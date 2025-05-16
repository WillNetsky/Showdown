# gui/app_controller.py
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import glob
import time
import json
import re

# Imports for backend logic
from team_management import (load_players_from_json, create_random_team,
                             save_team_to_json, load_team_from_json, get_next_team_number)
from game_logic import play_game
from entities import Team, Batter, Pitcher
from tournament import (
    preseason as tournament_preseason,
    play_season as tournament_play_season,
    postseason as tournament_postseason_culling,
    PLAYER_DATA_FILE, TEAMS_DIR
)
from stats import Stats, TeamStats
from optimizer_ga import GeneticTeamOptimizer, GACandidate

# Import the GUI components from the 'gui' package
from .dialogs import TeamSelectionDialog
from .ga_optimizer_tab import GAOptimizerTab
from .player_league_stats_tab import PlayerLeagueStatsTab
from .standings_tab import StandingsTab
from .team_roster_tab import TeamRosterTab
from .control_pane import ControlPane  # Assuming ControlPane was also refactored

try:
    import sys

    # Ensure parent directory is in path if running app_controller directly
    # This might not be needed if main.py handles path setup or project is structured as a package
    if os.path.join(os.path.dirname(__file__), '..') not in sys.path:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS
except ImportError:
    MIN_TEAM_POINTS = 4500
    MAX_TEAM_POINTS = 5000


class BaseballApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Baseball Simulator GUI")
        self.root.geometry("1400x900")

        # Core application data
        self.all_teams = []
        self.season_number = 0
        self.all_players_data = None
        self.app_state = "IDLE"

        # Tkinter variables that might be shared or controlled at app level
        self.num_teams_var = tk.IntVar(value=20)  # Used by ControlPane and tournament logic

        # GA related state managed by BaseballApp (controller part)
        self.ga_optimizer_thread = None
        self.stop_ga_event = threading.Event()
        self.ga_num_benchmark_teams_var = tk.IntVar(value=5)  # Used by GAOptimizerTab

        # --- Main Layout ---
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Pane (will be populated by ControlPane)
        self.left_pane_frame = ttk.Frame(self.main_pane, width=350)
        self.main_pane.add(self.left_pane_frame, weight=0)

        # --- Instantiate ControlPane (Manages Left Pane UI) ---
        self.control_pane = ControlPane(self.left_pane_frame, self)

        # --- Right Pane: Notebook for Tabs ---
        self.right_pane_notebook = ttk.Notebook(self.main_pane)
        self.main_pane.add(self.right_pane_notebook, weight=1)

        # --- Instantiate and Add Tabs ---
        self.standings_tab = StandingsTab(self.right_pane_notebook, self)
        self.right_pane_notebook.add(self.standings_tab, text='Standings')

        self.player_stats_season_tab = PlayerLeagueStatsTab(self.right_pane_notebook, self,
                                                            stats_source_attr='season_stats',
                                                            tab_title_prefix="Season")
        self.right_pane_notebook.add(self.player_stats_season_tab, text='Player Statistics (Season)')

        self.player_stats_career_tab = PlayerLeagueStatsTab(self.right_pane_notebook, self,
                                                            stats_source_attr='career_stats',
                                                            tab_title_prefix="Career")
        self.right_pane_notebook.add(self.player_stats_career_tab, text='Player Statistics (Career)')

        self.team_roster_tab = TeamRosterTab(self.right_pane_notebook, self)
        self.right_pane_notebook.add(self.team_roster_tab, text='Team Rosters & Stats')

        self.ga_optimizer_tab = GAOptimizerTab(self.right_pane_notebook, self)
        self.right_pane_notebook.add(self.ga_optimizer_tab, text='GA Team Optimizer')

        self.single_game_tab_frame = ttk.Frame(self.right_pane_notebook)  # Placeholder
        self.right_pane_notebook.add(self.single_game_tab_frame, text='Play Single Game')
        ttk.Label(self.single_game_tab_frame, text="Detailed single game playout (Future).").pack(padx=20, pady=20)

        # Initial state
        self._set_app_state("LOADING_PLAYERS")
        self._load_all_player_data_async()
        self.update_button_states()

    def _set_app_state(self, new_state):
        self.app_state = new_state
        self.update_button_states()

    def _treeview_sort_column(self, tv, col, reverse):
        # This general utility remains in the app controller
        # It needs to correctly identify the treeview being sorted to apply numeric rules
        try:
            data_list = []
            for k in tv.get_children(''):
                value = tv.set(k, col)
                try:
                    numeric_cols = []
                    # Determine numeric columns based on the treeview instance
                    # This logic checks against treeview instances now owned by tab objects
                    if hasattr(self, 'standings_tab') and tv == self.standings_tab.standings_treeview:
                        numeric_cols = ["W", "L", "Win%", "ELO", "R", "RA", "Run Diff"]
                    elif hasattr(self,
                                 'player_stats_season_tab') and tv == self.player_stats_season_tab.batting_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif hasattr(self,
                                 'player_stats_career_tab') and tv == self.player_stats_career_tab.batting_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif hasattr(self, 'team_roster_tab') and tv == self.team_roster_tab.batting_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif hasattr(self, 'ga_optimizer_tab') and tv == self.ga_optimizer_tab.best_team_batting_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif hasattr(self,
                                 'player_stats_season_tab') and tv == self.player_stats_season_tab.pitching_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]
                    elif hasattr(self,
                                 'player_stats_career_tab') and tv == self.player_stats_career_tab.pitching_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]
                    elif hasattr(self, 'team_roster_tab') and tv == self.team_roster_tab.pitching_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]
                    elif hasattr(self, 'ga_optimizer_tab') and tv == self.ga_optimizer_tab.best_team_pitching_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]

                    is_numeric_col = col in numeric_cols
                    if is_numeric_col:
                        cleaned_value = str(value).replace('%', '').replace('+', '')
                        if col == "IP" and '.' in cleaned_value:
                            parts = cleaned_value.split('.')
                            numeric_value = float(parts[0]) + (float(parts[1]) / 3.0) if len(parts) == 2 and parts[
                                1].isdigit() else float(parts[0])
                        elif col in ["AVG", "OBP", "SLG", "OPS", "Win%"] and cleaned_value.startswith("."):
                            numeric_value = float(
                                cleaned_value) if cleaned_value != ".---" and cleaned_value != ".-" else -1.0
                        elif cleaned_value.lower() == "inf":
                            numeric_value = float('inf')
                        elif cleaned_value.lower() == "-inf":
                            numeric_value = float('-inf')
                        elif cleaned_value.lower() == "nan":
                            numeric_value = float('inf') if col == "ERA" else -1.0
                        elif col == "Year":
                            numeric_value = int(cleaned_value) if cleaned_value.isdigit() else 0
                        else:
                            numeric_value = float(cleaned_value)
                        data_list.append((numeric_value, k))
                    else:
                        data_list.append((str(value).lower(), k))
                except ValueError:
                    data_list.append((str(value).lower(), k))

            if col == "ERA":
                data_list.sort(key=lambda t: t[0], reverse=not reverse)
            else:
                data_list.sort(key=lambda t: t[0], reverse=reverse)

            for index, (val, k) in enumerate(data_list): tv.move(k, '', index)
            tv.heading(col, command=lambda _c=col: self._treeview_sort_column(tv, _c, not reverse))
        except tk.TclError as e:
            self.log_message(f"Sort TclError ({col}): {e}", internal=True)
        except Exception as e:
            self.log_message(f"Sort Error ({col}): {e}")

    def _load_all_player_data_async(self):
        self.log_message("Initiating player data load...")
        thread = threading.Thread(target=self._load_all_player_data_logic, daemon=True);
        thread.start()

    def _load_all_player_data_logic(self):
        try:
            self.all_players_data = load_players_from_json(PLAYER_DATA_FILE)
            if self.all_players_data:
                self.log_message(f"Loaded {len(self.all_players_data)} players from {PLAYER_DATA_FILE}.")
            else:
                self.log_message(f"ERROR: No player data loaded from {PLAYER_DATA_FILE}.")
                messagebox.showerror("Player Data Error", f"Could not load player data from {PLAYER_DATA_FILE}.")
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Exception during player data load: {e}")
            self.root.after(0, lambda: messagebox.showerror("Player Data Exception", str(e)))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def log_message(self, message, internal=False):
        """Main application logging method. Forwards to ControlPane's log widget."""
        if not internal or "[GA]" in message or "ERROR" in message or "Warning" in message:
            if hasattr(self, 'control_pane') and self.control_pane:
                self.root.after(0, lambda: self.control_pane.log_to_widget(message))
            else:
                print(f"LOG (app_controller fallback): {message}")

    def update_button_states(self):
        current_state = self.app_state
        is_ga_running = self.ga_optimizer_thread is not None and self.ga_optimizer_thread.is_alive()
        players_loaded = self.all_players_data is not None
        teams_exist = bool(self.all_teams)

        # Update ControlPane buttons
        if hasattr(self, 'control_pane') and self.control_pane:
            self.control_pane.update_control_buttons_state(current_state, players_loaded, teams_exist, is_ga_running)

        # Update GAOptimizerTab buttons
        if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
            if is_ga_running or current_state == "GA_RUNNING":
                self.ga_optimizer_tab.start_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.NORMAL)
                self.ga_optimizer_tab.select_benchmarks_button.config(state=tk.DISABLED)
            elif current_state in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT",
                                   "SEASON_IN_PROGRESS", "POSTSEASON_IN_PROGRESS"]:
                self.ga_optimizer_tab.start_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.select_benchmarks_button.config(state=tk.DISABLED)
            else:  # IDLE or SEASON_CONCLUDED
                self.ga_optimizer_tab.start_ga_button.config(state=tk.NORMAL if players_loaded else tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.select_benchmarks_button.config(
                    state=tk.NORMAL if players_loaded else tk.DISABLED)

    def prompt_clear_tournament_data(self):
        if self.app_state not in ["IDLE", "SEASON_CONCLUDED"] or (
                self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive()):
            messagebox.showwarning("Operation in Progress", "Cannot clear data now.", parent=self.root);
            return
        if messagebox.askyesno("Confirm Clear", "Clear all tournament, GA data, and custom benchmarks?",
                               parent=self.root):
            self._clear_tournament_data_confirmed()

    def _clear_tournament_data_confirmed(self):
        self.log_message("Clearing all application data...")
        self.all_teams = [];
        self.season_number = 0

        if hasattr(self, 'standings_tab'): self.standings_tab.clear_display()
        if hasattr(self, 'player_stats_season_tab'): self.player_stats_season_tab.clear_display()
        if hasattr(self, 'player_stats_career_tab'): self.player_stats_career_tab.clear_display()
        if hasattr(self, 'team_roster_tab'): self.team_roster_tab.clear_display()
        if hasattr(self, 'ga_optimizer_tab'): self.ga_optimizer_tab.reset_ui()

        if hasattr(self, 'control_pane') and hasattr(self.control_pane, 'log_text_widget'):
            self.control_pane.log_text_widget.config(state=tk.NORMAL)
            self.control_pane.log_text_widget.delete('1.0', tk.END)
            # self.control_pane.log_text_widget.config(state=tk.DISABLED) # Log_message will disable it

        self.log_message("Data cleared. Ready for new run.")
        if hasattr(self, 'team_roster_tab'): self.team_roster_tab.update_team_selector()
        self._set_app_state("IDLE")

    # --- Tournament Flow Methods ---
    def initialize_tournament_threaded(self):
        if not self.all_players_data: messagebox.showerror("Error", "Player data not loaded."); return
        self._set_app_state("INITIALIZING_TOURNAMENT")
        self.log_message("Opening team selection for tournament...")
        dialog = TeamSelectionDialog(self.root, self.num_teams_var.get(), dialog_title="Select Teams for Tournament")
        if dialog.selected_team_filepaths is None:
            self.log_message("Tournament team selection cancelled.");
            self._set_app_state("IDLE");
            return
        self.log_message(f"Selected {len(dialog.selected_team_filepaths)} teams for tournament. Initializing...")
        thread = threading.Thread(target=self._initialize_tournament_logic, args=(dialog.selected_team_filepaths,),
                                  daemon=True);
        thread.start()

    def _initialize_tournament_logic(self, selected_filepaths):
        try:
            num_to_init = self.num_teams_var.get();
            temp_teams = []
            loaded_paths = set()
            for fp in selected_filepaths:
                if fp in loaded_paths: continue
                team = load_team_from_json(fp)
                if team:
                    team.json_filepath = fp; temp_teams.append(team); loaded_paths.add(fp)
                else:
                    self.log_message(f"Warn: Failed to load team from {fp}")
            self.log_message(f"Loaded {len(temp_teams)} user-selected teams for tournament.")
            to_generate = num_to_init - len(temp_teams)
            if to_generate > 0:
                self.log_message(f"Generating {to_generate} random teams for tournament.")
                if not self.all_players_data: self.log_message(
                    "ERROR: Player data missing for generation!"); self.root.after(0, lambda: self._set_app_state(
                    "IDLE")); return
                for _ in range(to_generate):
                    num = get_next_team_number(TEAMS_DIR);
                    name = f"RandTourneyTm {num}"
                    new_team = create_random_team(self.all_players_data, name, MIN_TEAM_POINTS, MAX_TEAM_POINTS)
                    if new_team:
                        temp_teams.append(new_team);
                        s_name = re.sub(r'[^\w.-]', '_', new_team.name)
                        f_path = os.path.join(TEAMS_DIR, f"Team_{num}_{s_name}_{new_team.total_points}.json")
                        save_team_to_json(new_team, f_path);
                        new_team.json_filepath = f_path
                        self.log_message(f"Generated and saved tournament team: {new_team.name}.")
                    else:
                        self.log_message(f"ERROR: Failed to generate random team: {name}."); break
            self.all_teams = temp_teams;
            self.season_number = 0
            if self.all_teams:
                self.log_message(f"Running initial preseason for {len(self.all_teams)} tournament teams...")
                tournament_preseason(self.all_teams, self.log_message);
                self.season_number = 1
                self.log_message(f"Initial preseason complete.")
            self.log_message(
                f"Tournament initialized: {len(self.all_teams)} teams. Ready for Season {self.season_number}.")

            if hasattr(self, 'standings_tab'): self.root.after(0, lambda: self.standings_tab.update_display(
                self.all_teams))
            if hasattr(self, 'player_stats_season_tab'): self.root.after(0, self.player_stats_season_tab.update_display)
            if hasattr(self, 'player_stats_career_tab'): self.root.after(0, self.player_stats_career_tab.update_display)
            if hasattr(self, 'team_roster_tab'): self.root.after(0, self.team_roster_tab.update_team_selector)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Initialization error: {e}");
            self.root.after(0, lambda: messagebox.showerror("Initialization Error", str(e)));
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_season_threaded(self):
        if not self.all_teams: messagebox.showwarning("No Teams", "Initialize teams first."); return
        self._set_app_state("SEASON_IN_PROGRESS")
        self.log_message(f"Starting Season {self.season_number} simulation...")
        thread = threading.Thread(target=self._run_season_logic, daemon=True);
        thread.start()

    def _run_season_logic(self):
        try:
            if self.season_number > 0:
                self.log_message(f"--- Season {self.season_number}: Pre-season stat reset ---")
                tournament_preseason(self.all_teams, self.log_message)
            self.log_message(f"--- Season {self.season_number}: Regular Season Playing ---")
            tournament_play_season(self.all_teams, self.log_message)
            self.log_message("Regular season play complete. Saving team data...")
            for team in self.all_teams:
                f_path = team.json_filepath if hasattr(team, 'json_filepath') and team.json_filepath and os.path.exists(
                    os.path.dirname(team.json_filepath)) else None
                if not f_path:
                    num_match = re.search(r'Team[_ ](\d+)', team.name)
                    next_num = get_next_team_number(TEAMS_DIR) if not num_match else num_match.group(1)
                    s_name = re.sub(r'[^\w.-]', '_', team.name if team.name else f"Team{next_num}")
                    f_path = os.path.join(TEAMS_DIR, f"Team_{next_num}_{s_name}_{team.total_points}.json")
                save_team_to_json(team, f_path);
                team.json_filepath = f_path
            self.log_message("All team data saved after season.")

            if hasattr(self, 'standings_tab'): self.root.after(0, lambda: self.standings_tab.update_display(
                self.all_teams))
            if hasattr(self, 'player_stats_season_tab'): self.root.after(0, self.player_stats_season_tab.update_display)
            if hasattr(self, 'player_stats_career_tab'): self.root.after(0, self.player_stats_career_tab.update_display)
            if hasattr(self, 'team_roster_tab'): self.root.after(0, self.team_roster_tab.update_team_selector)
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))
        except Exception as e:
            self.log_message(f"Error during season {self.season_number} run: {e}")
            self.root.after(0, lambda: messagebox.showerror(f"Season {self.season_number} Error", str(e)))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_postseason_and_prepare_threaded(self):
        if not self.all_teams or self.app_state != "SEASON_CONCLUDED": messagebox.showwarning("Invalid State",
                                                                                              "Run a season to conclusion first."); return
        self._set_app_state("POSTSEASON_IN_PROGRESS")
        self.log_message(f"--- Season {self.season_number} Completed: Post-season Culling & Regeneration ---")
        thread = threading.Thread(target=self._run_postseason_and_prepare_logic, daemon=True);
        thread.start()

    def _run_postseason_and_prepare_logic(self):
        try:
            survivors = [t for t in self.all_teams if t.team_stats.wins >= t.team_stats.losses]
            self.log_message(f"{len(self.all_teams) - len(survivors)} teams culled based on W/L record.")
            tournament_postseason_culling(survivors, self.log_message)
            self.all_teams = survivors
            to_regen = self.num_teams_var.get() - len(self.all_teams)
            if to_regen > 0:
                self.log_message(f"Regenerating {to_regen} teams...")
                if not self.all_players_data:
                    self.log_message("ERROR: Player data missing for regeneration!");
                else:
                    for _ in range(to_regen):
                        num = get_next_team_number(TEAMS_DIR);
                        name = f"RegenTm {num}"
                        new_team = create_random_team(self.all_players_data, name, MIN_TEAM_POINTS, MAX_TEAM_POINTS)
                        if new_team:
                            self.all_teams.append(new_team);
                            s_name = re.sub(r'[^\w.-]', '_', new_team.name)
                            f_path = os.path.join(TEAMS_DIR, f"Team_{num}_{s_name}_{new_team.total_points}.json")
                            save_team_to_json(new_team, f_path);
                            new_team.json_filepath = f_path
                            self.log_message(f"Regenerated and saved {new_team.name}.")
                        else:
                            self.log_message(f"ERROR: Failed to regenerate team: {name}."); break
            self.season_number += 1
            self.log_message(
                f"Postseason complete. Ready for Season {self.season_number} with {len(self.all_teams)} teams.")

            if hasattr(self, 'standings_tab'): self.root.after(0, lambda: self.standings_tab.update_display(
                self.all_teams))
            if hasattr(self, 'player_stats_season_tab'): self.root.after(0, self.player_stats_season_tab.update_display)
            if hasattr(self, 'player_stats_career_tab'): self.root.after(0, self.player_stats_career_tab.update_display)
            if hasattr(self, 'team_roster_tab'): self.root.after(0, self.team_roster_tab.update_team_selector)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Error during postseason preparation: {e}");
            self.root.after(0, lambda: messagebox.showerror("Postseason Error", str(e)));
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))

    # --- GA Optimizer Process Management Methods ---
    def start_ga_optimizer_process(self, ga_params_from_tab, selected_benchmark_files):
        self.log_message("GA process initiated by controller...")
        self._set_app_state("GA_RUNNING")
        self.stop_ga_event.clear()
        if hasattr(self, 'ga_optimizer_tab'): self.ga_optimizer_tab.reset_ui()

        self.ga_optimizer = GeneticTeamOptimizer(
            all_players_list=self.all_players_data,
            population_size=ga_params_from_tab["population_size"],
            num_generations=ga_params_from_tab["num_generations"],
            mutation_rate=ga_params_from_tab["mutation_rate"],
            num_mutation_swaps=ga_params_from_tab["num_mutation_swaps"],
            elitism_count=ga_params_from_tab["elitism_count"],
            num_benchmark_teams=ga_params_from_tab["num_benchmark_teams"],
            games_vs_each_benchmark=ga_params_from_tab["games_vs_each_benchmark"],
            immigration_rate=ga_params_from_tab["immigration_rate"],
            benchmark_archetype_files=selected_benchmark_files,
            min_team_points=MIN_TEAM_POINTS, max_team_points=MAX_TEAM_POINTS,
            log_callback=self.log_message,
            update_progress_callback=self._forward_ga_progress_to_tab,
            stop_event=self.stop_ga_event
        )
        self.ga_optimizer_thread = threading.Thread(target=self._run_ga_logic_thread, daemon=True)
        self.ga_optimizer_thread.start()

    def _forward_ga_progress_to_tab(self, percentage, message, generation_num=None, best_fitness=None,
                                    avg_fitness=None):
        if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
            self.root.after(0, lambda: self.ga_optimizer_tab.update_progress_display(percentage, message))
            if generation_num is not None and best_fitness is not None and avg_fitness is not None:
                self.root.after(0, lambda: self.ga_optimizer_tab.update_plot_data(generation_num, best_fitness,
                                                                                  avg_fitness))

    def _run_ga_logic_thread(self):
        best_candidate = None
        try:
            best_candidate = self.ga_optimizer.run()
            if self.stop_ga_event.is_set():
                self.log_message("GA run was stopped by user (controller ack).")
            elif best_candidate and best_candidate.team:
                if hasattr(self, 'ga_optimizer_tab'): self.root.after(0,
                                                                      lambda: self.ga_optimizer_tab.display_best_ga_team(
                                                                          best_candidate))
                team_name_part = re.sub(r'[^\w.-]', '_', best_candidate.team.name)
                filename = os.path.join(TEAMS_DIR,
                                        f"GA_Best_{team_name_part}_Fit{best_candidate.fitness:.0f}_Pts{best_candidate.team.total_points}.json")
                save_team_to_json(best_candidate.team, filename)
                self.log_message(f"Best GA team ('{best_candidate.team.name}') saved as {os.path.basename(filename)}")
            else:
                self.log_message("GA finished: No valid best team or was stopped before finding one.")
        except Exception as e:
            self.log_message(f"Error during GA execution thread: {e}")
            self.root.after(0, lambda: messagebox.showerror("GA Runtime Error", f"An error occurred: {e}",
                                                            parent=self.root))
        finally:
            self.ga_optimizer_thread = None
            final_status_msg = "Status: GA Finished"
            if self.stop_ga_event.is_set():
                final_status_msg = "Status: GA Stopped by user"
            elif best_candidate is None and not self.stop_ga_event.is_set():
                final_status_msg = "Status: GA Error or No Result"
            if hasattr(self, 'ga_optimizer_tab'):
                self.root.after(0, lambda: self.ga_optimizer_tab.update_progress_display(100,
                                                                                         final_status_msg.split(": ")[
                                                                                             1]))
                if hasattr(self.ga_optimizer_tab,
                           'fitness_generations') and not self.ga_optimizer_tab.fitness_generations and not self.stop_ga_event.is_set():
                    self.root.after(0, self.ga_optimizer_tab.draw_fitness_plot)
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def stop_ga_search(self):
        if self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive():
            self.log_message("Stopping GA search (controller)...")
            self.stop_ga_event.set()
        else:
            self.log_message("GA search not currently running (controller).")

# Note: No if __name__ == "__main__": block here, as this file is a module.
# main.py is now the entry point.