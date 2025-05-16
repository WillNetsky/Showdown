# gui/app_controller.py
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import time
import re

# Imports for backend logic
from team_management import (load_players_from_json, create_random_team,
                             save_team_to_json, load_team_from_json, get_next_team_number)

from tournament import (
    preseason as tournament_preseason,
    play_season as tournament_play_season,
    postseason as tournament_postseason_culling,
    PLAYER_DATA_FILE, TEAMS_DIR
)

from optimizer_ga import GeneticTeamOptimizer

# Import the GUI components from the 'gui' package
from .dialogs import TeamSelectionDialog
from .ga_optimizer_tab import GAOptimizerTab
from .player_league_stats_tab import PlayerLeagueStatsTab
from .standings_tab import StandingsTab
from .team_roster_tab import TeamRosterTab

try:
    import sys

    if os.path.join(os.path.dirname(__file__), '..') not in sys.path:  # Ensure project root is in path
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

        # Tkinter variables for widgets still managed directly by BaseballApp (e.g., tournament controls)
        self.num_teams_var = tk.IntVar(value=20)

        # GA related state managed by BaseballApp (controller part)
        self.ga_optimizer_thread = None
        self.stop_ga_event = threading.Event()
        self.ga_num_benchmark_teams_var = tk.IntVar(value=5)  # Shared with GAOptimizerTab

        # --- Main Layout ---
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_pane_frame = ttk.Frame(self.main_pane, width=350)
        self.main_pane.add(self.left_pane_frame, weight=0)

        # --- Left Pane: Tournament Controls ---
        controls_frame = ttk.LabelFrame(self.left_pane_frame, text="Tournament Controls")
        controls_frame.pack(padx=10, pady=(0, 10), fill="x", side=tk.TOP)
        ttk.Label(controls_frame, text="Number of Teams:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(controls_frame, textvariable=self.num_teams_var, width=5).grid(row=0, column=1, padx=5, pady=5,
                                                                                 sticky="w")
        self.init_button = ttk.Button(controls_frame, text="Initialize/Load Teams",
                                      command=self.initialize_tournament_threaded)
        self.init_button.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 2), sticky="ew")
        self.run_season_button = ttk.Button(controls_frame, text="Run Season", command=self.run_season_threaded)
        self.run_season_button.grid(row=2, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        self.run_postseason_button = ttk.Button(controls_frame, text="Run Postseason & Prepare Next",
                                                command=self.run_postseason_and_prepare_threaded)
        self.run_postseason_button.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        self.clear_tournament_button = ttk.Button(controls_frame, text="Clear Tournament Data",
                                                  command=self.prompt_clear_tournament_data)
        self.clear_tournament_button.grid(row=4, column=0, columnspan=2, padx=5, pady=(10, 2), sticky="ew")

        # --- Left Pane: Simulation Log ---
        log_frame = ttk.LabelFrame(self.left_pane_frame, text="Simulation Log")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side=tk.BOTTOM)
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, relief=tk.SOLID,
                                                         borderwidth=1)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text_widget.config(state=tk.DISABLED)

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
        # This method is now more generic as it's called by various tabs
        try:
            data_list = []
            for k in tv.get_children(''):
                value = tv.set(k, col)
                try:
                    numeric_cols = []
                    # Determine numeric columns based on the treeview instance or its known columns
                    # This part needs to be robust if columns are defined within tabs
                    # For now, we assume the column names passed are sufficient to identify numeric types
                    # Or, each tab's sort command could pass its specific numeric_cols list.
                    # A more generic approach: try to convert, fallback to string.
                    # Simplified example:
                    if col in ["W", "L", "ELO", "R", "RA", "Run Diff", "PA", "AB", "H", "2B", "3B", "HR", "RBI", "BB",
                               "SO", "BatRuns", "Year", "IP", "BF", "K", "ER"]:  # Common numeric stats
                        numeric_cols.append(col)
                    if col in ["Win%", "AVG", "OBP", "SLG", "OPS", "ERA", "WHIP"]:  # Rate stats
                        numeric_cols.append(col)

                    is_numeric_col = col in numeric_cols
                    if is_numeric_col:
                        cleaned_value = str(value).replace('%', '').replace('+', '')
                        if col == "IP" and '.' in cleaned_value:
                            parts = cleaned_value.split('.')
                            numeric_value = float(parts[0]) + (float(parts[1]) / 3.0) if len(parts) == 2 and parts[
                                1].isdigit() else float(parts[0])
                        elif col in ["AVG", "OBP", "SLG", "OPS", "Win%"] and cleaned_value.startswith("."):
                            numeric_value = float(
                                cleaned_value) if cleaned_value != ".---" and cleaned_value != ".-" else -1.0  # Handle placeholders
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
                    else:  # Text column
                        data_list.append((str(value).lower(), k))
                except ValueError:  # Fallback for conversion errors
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
        if not internal or "[GA]" in message or "ERROR" in message or "Warning" in message:
            self.root.after(0, lambda: self._log_to_widget(message))

    def _log_to_widget(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text_widget.see(tk.END)
        self.log_text_widget.config(state=tk.DISABLED)

    def update_button_states(self):
        current_state = self.app_state
        is_ga_running = self.ga_optimizer_thread is not None and self.ga_optimizer_thread.is_alive()
        can_clear = self.all_players_data and not is_ga_running and current_state not in ["LOADING_PLAYERS",
                                                                                          "INITIALIZING_TOURNAMENT",
                                                                                          "SEASON_IN_PROGRESS",
                                                                                          "POSTSEASON_IN_PROGRESS",
                                                                                          "GA_RUNNING"]
        self.clear_tournament_button.config(state=tk.NORMAL if can_clear else tk.DISABLED)

        ga_tab_exists = hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab is not None

        if is_ga_running or current_state == "GA_RUNNING":
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button]: btn.config(
                state=tk.DISABLED)
            if ga_tab_exists:  # Control buttons within GAOptimizerTab
                self.ga_optimizer_tab.start_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.NORMAL)
                self.ga_optimizer_tab.select_benchmarks_button.config(state=tk.DISABLED)
        elif current_state in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT", "SEASON_IN_PROGRESS",
                               "POSTSEASON_IN_PROGRESS"]:
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button]: btn.config(
                state=tk.DISABLED)
            if ga_tab_exists:
                self.ga_optimizer_tab.start_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.select_benchmarks_button.config(state=tk.DISABLED)
        elif current_state == "IDLE":
            self.init_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
            self.run_season_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)
            self.run_postseason_button.config(state=tk.DISABLED)
            if ga_tab_exists:
                self.ga_optimizer_tab.start_ga_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.select_benchmarks_button.config(
                    state=tk.NORMAL if self.all_players_data else tk.DISABLED)
        elif current_state == "SEASON_CONCLUDED":
            self.init_button.config(state=tk.DISABLED)
            self.run_season_button.config(state=tk.DISABLED)
            self.run_postseason_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)
            if ga_tab_exists:
                self.ga_optimizer_tab.start_ga_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
                self.ga_optimizer_tab.stop_ga_button.config(state=tk.DISABLED)
                self.ga_optimizer_tab.select_benchmarks_button.config(
                    state=tk.NORMAL if self.all_players_data else tk.DISABLED)

    def prompt_clear_tournament_data(self):
        if self.app_state not in ["IDLE", "SEASON_CONCLUDED"] or (
                self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive()):
            messagebox.showwarning("Operation in Progress", "Cannot clear data now.", parent=self.root);
            return
        if messagebox.askyesno("Confirm Clear", "Clear all tournament, GA data, and selected benchmarks?",
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

        self.log_text_widget.config(state=tk.NORMAL);
        self.log_text_widget.delete('1.0', tk.END);
        self.log_text_widget.config(state=tk.DISABLED)
        self.log_message("Data cleared. Ready for new run.")
        if hasattr(self, 'team_roster_tab'): self.team_roster_tab.update_team_selector()  # Update combobox
        self._set_app_state("IDLE")

    def initialize_tournament_threaded(self):
        if not self.all_players_data: messagebox.showerror("Error", "Player data not loaded."); return
        self._set_app_state("INITIALIZING_TOURNAMENT")
        self.log_message("Opening team selection for tournament...")
        dialog = TeamSelectionDialog(self.root, self.num_teams_var.get(), dialog_title="Select Teams for Tournament")
        if dialog.selected_team_filepaths is None:  # User cancelled
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
            # Update all relevant displays
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
            if self.season_number > 0:  # Preseason reset for S1 is done in init. For S2+ do it here.
                self.log_message(f"--- Season {self.season_number}: Pre-season stat reset ---")
                tournament_preseason(self.all_teams, self.log_message)  # Resets season_stats
            self.log_message(f"--- Season {self.season_number}: Regular Season Playing ---")
            tournament_play_season(self.all_teams, self.log_message)
            self.log_message("Regular season play complete. Saving team data...")
            for team in self.all_teams:
                f_path = team.json_filepath if hasattr(team, 'json_filepath') and team.json_filepath else None
                if not f_path or not os.path.exists(os.path.dirname(f_path)):  # If no stored path or dir invalid
                    num_match = re.search(r'Team[_ ](\d+)', team.name)  # Try to find existing number
                    next_num = get_next_team_number(TEAMS_DIR) if not num_match else num_match.group(1)
                    s_name = re.sub(r'[^\w.-]', '_', team.name if team.name else f"Team{next_num}")
                    f_path = os.path.join(TEAMS_DIR, f"Team_{next_num}_{s_name}_{team.total_points}.json")
                save_team_to_json(team, f_path);
                team.json_filepath = f_path  # Update stored path
            self.log_message("All team data saved after season.")
            # Update all relevant displays
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
            survivors = [t for t in self.all_teams if t.team_stats.wins >= t.team_stats.losses]  # Example culling
            self.log_message(f"{len(self.all_teams) - len(survivors)} teams culled based on W/L record.")
            tournament_postseason_culling(survivors, self.log_message)  # Resets season_stats of survivors
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
            # Update all relevant displays
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
        """Called by GAOptimizerTab to initiate the GA backend process."""
        self.log_message("GA process initiated by GA Tab...")
        self._set_app_state("GA_RUNNING")
        self.stop_ga_event.clear()
        if hasattr(self, 'ga_optimizer_tab'): self.ga_optimizer_tab.reset_ui()  # Tell tab to clear its displays

        self.ga_optimizer = GeneticTeamOptimizer(
            all_players_list=self.all_players_data,
            population_size=ga_params_from_tab["population_size"],
            num_generations=ga_params_from_tab["num_generations"],
            mutation_rate=ga_params_from_tab["mutation_rate"],
            num_mutation_swaps=ga_params_from_tab["num_mutation_swaps"],
            elitism_count=ga_params_from_tab["elitism_count"],
            num_benchmark_teams=ga_params_from_tab["num_benchmark_teams"],  # This is total desired by user
            games_vs_each_benchmark=ga_params_from_tab["games_vs_each_benchmark"],
            immigration_rate=ga_params_from_tab["immigration_rate"],
            benchmark_archetype_files=selected_benchmark_files,  # List of filepaths selected by user
            min_team_points=MIN_TEAM_POINTS,
            max_team_points=MAX_TEAM_POINTS,
            log_callback=self.log_message,
            update_progress_callback=self._forward_ga_progress_to_tab,
            stop_event=self.stop_ga_event
        )
        self.ga_optimizer_thread = threading.Thread(target=self._run_ga_logic_thread, daemon=True)
        self.ga_optimizer_thread.start()

    def _forward_ga_progress_to_tab(self, percentage, message, generation_num=None, best_fitness=None,
                                    avg_fitness=None):
        """Forwards progress from GA backend to the GAOptimizerTab instance for UI updates."""
        if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
            self.root.after(0, lambda: self.ga_optimizer_tab.update_progress_display(percentage, message))
            if generation_num is not None and best_fitness is not None and avg_fitness is not None:
                self.root.after(0, lambda: self.ga_optimizer_tab.update_plot_data(generation_num, best_fitness,
                                                                                  avg_fitness))

    def _run_ga_logic_thread(self):
        """The target function for the GA optimizer thread."""
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
                # Ensure plot gets a final draw if it was running
                if hasattr(self.ga_optimizer_tab,
                           'fitness_generations') and not self.ga_optimizer_tab.fitness_generations and not self.stop_ga_event.is_set():
                    self.root.after(0, self.ga_optimizer_tab.draw_fitness_plot)  # Draw empty with message if no data
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def stop_ga_search(self):
        if self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive():
            self.log_message("Stopping GA search (controller)...")
            self.stop_ga_event.set()
        else:
            self.log_message("GA search not currently running (controller).")