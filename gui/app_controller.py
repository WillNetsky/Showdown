# gui/app_controller.py
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox  # Keep messagebox for app-level errors
import threading
import os
import glob
import time
import json
import re

# Matplotlib not directly used here anymore for GA plot, but other plots might exist
# from matplotlib.figure import Figure
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Imports for backend logic
from team_management import (load_players_from_json, create_random_team,
                             save_team_to_json, load_team_from_json, get_next_team_number)
from game_logic import play_game
from entities import Team, Batter, Pitcher  # Keep for type hints and direct use if any
from tournament import (
    preseason as tournament_preseason,
    play_season as tournament_play_season,
    postseason as tournament_postseason_culling,
    PLAYER_DATA_FILE, TEAMS_DIR
)
from stats import Stats, TeamStats
from optimizer_ga import GeneticTeamOptimizer, GACandidate  # Keep for running GA

# Import the new tab class and dialogs
from .ga_optimizer_tab import GAOptimizerTab
from .dialogs import TeamSelectionDialog  # Dialogs now imported

try:
    from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS
except ImportError:
    MIN_TEAM_POINTS = 4500
    MAX_TEAM_POINTS = 5000


class BaseballApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Baseball Simulator GUI")
        self.root.geometry("1400x900")

        self.all_teams = []
        self.season_number = 0
        self.num_teams_var = tk.IntVar(value=20)  # Tournament size
        self.all_players_data = None
        self.app_state = "IDLE"
        self.selected_team_for_roster_var = tk.StringVar()

        # GA related state managed by BaseballApp (controller)
        self.ga_optimizer_thread = None
        self.stop_ga_event = threading.Event()
        # This variable is used by GAOptimizerTab to know the desired number of benchmarks
        self.ga_num_benchmark_teams_var = tk.IntVar(value=5)

        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.left_pane_frame = ttk.Frame(self.main_pane, width=350)
        self.main_pane.add(self.left_pane_frame, weight=1)

        controls_frame = ttk.LabelFrame(self.left_pane_frame, text="Tournament Controls")
        controls_frame.pack(padx=10, pady=(0, 10), fill="x", side=tk.TOP)
        # ... (Tournament control buttons setup - no changes here) ...
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

        log_frame = ttk.LabelFrame(self.left_pane_frame, text="Simulation Log")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side=tk.BOTTOM)
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, relief=tk.SOLID,
                                                         borderwidth=1)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text_widget.config(state=tk.DISABLED)

        self.right_pane_notebook = ttk.Notebook(self.main_pane)
        self.main_pane.add(self.right_pane_notebook, weight=4)

        # --- Standings Tab ---
        # This could also be moved to its own class gui.standings_tab.StandingsTab(self.right_pane_notebook, self)
        self.standings_tab_frame = ttk.Frame(self.right_pane_notebook)  # Placeholder if not refactored yet
        self.right_pane_notebook.add(self.standings_tab_frame, text='Standings')
        cols_standings = ("Team", "W", "L", "Win%", "ELO", "R", "RA", "Run Diff")
        self.standings_treeview = ttk.Treeview(self.standings_tab_frame, columns=cols_standings, show='headings')
        for col in cols_standings:
            self.standings_treeview.heading(col, text=col,
                                            command=lambda _c=col: self._treeview_sort_column(self.standings_treeview,
                                                                                              _c, False))
            self.standings_treeview.column(col, width=85, anchor=tk.CENTER, stretch=tk.YES)
        self.standings_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Player Statistics (Season) Tab ---
        # This could also be moved to its own class gui.player_stats_tab.PlayerStatsTab(self.right_pane_notebook, self, 'season')
        self.player_stats_tab_frame = ttk.Frame(self.right_pane_notebook)  # Placeholder
        self.right_pane_notebook.add(self.player_stats_tab_frame, text='Player Statistics (Season)')
        # ... (Full setup of player_stats_tab_frame treeviews as before)
        player_stats_pane = ttk.PanedWindow(self.player_stats_tab_frame, orient=tk.VERTICAL)
        player_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        league_batting_frame = ttk.LabelFrame(player_stats_pane, text="League Batting Stats (Season)")
        player_stats_pane.add(league_batting_frame, weight=1)
        self.cols_league_batting = ("Name", "Year", "Set", "Team", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI",
                                    "BB", "SO", "AVG", "OBP", "SLG", "OPS", "BatRuns")
        self.league_batting_stats_treeview = ttk.Treeview(league_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)
        for col in self.cols_league_batting:
            w = 110 if col == "Name" else (45 if col == "Year" else (65 if col == "Set" else (70 if col == "Team" else (
                35 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    55 if col != "BatRuns" else 60)))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.league_batting_stats_treeview.heading(col, text=col, command=lambda _c=col: self._treeview_sort_column(
                self.league_batting_stats_treeview, _c, False))
            self.league_batting_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.league_batting_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)
        league_pitching_frame = ttk.LabelFrame(player_stats_pane, text="League Pitching Stats (Season)")
        player_stats_pane.add(league_pitching_frame, weight=1)
        self.cols_league_pitching = ("Name", "Year", "Set", "Team", "Role", "IP", "ERA", "WHIP", "BF", "K", "BB", "H",
                                     "R", "ER", "HR")
        self.league_pitching_stats_treeview = ttk.Treeview(league_pitching_frame, columns=self.cols_league_pitching,
                                                           show='headings', height=10)
        for col in self.cols_league_pitching:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (
                80 if col == "Team" else (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.league_pitching_stats_treeview.heading(col, text=col,
                                                        command=lambda _c=col: self._treeview_sort_column(
                                                            self.league_pitching_stats_treeview, _c, False))
            self.league_pitching_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.league_pitching_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Player Statistics (Career) Tab ---
        # This could also be moved to its own class gui.player_stats_tab.PlayerStatsTab(self.right_pane_notebook, self, 'career')
        self.career_stats_tab_frame = ttk.Frame(self.right_pane_notebook)  # Placeholder
        self.right_pane_notebook.add(self.career_stats_tab_frame, text='Player Statistics (Career)')
        # ... (Full setup of career_stats_tab_frame treeviews as before, using self.cols_league_batting and self.cols_league_pitching)
        career_stats_pane = ttk.PanedWindow(self.career_stats_tab_frame, orient=tk.VERTICAL)
        career_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        career_batting_frame = ttk.LabelFrame(career_stats_pane, text="League Batting Stats (Career)")
        career_stats_pane.add(career_batting_frame, weight=1)
        self.career_batting_stats_treeview = ttk.Treeview(career_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)
        for col in self.cols_league_batting:
            w = 110 if col == "Name" else (45 if col == "Year" else (65 if col == "Set" else (70 if col == "Team" else (
                35 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    55 if col != "BatRuns" else 60)))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.career_batting_stats_treeview.heading(col, text=col, command=lambda _c=col: self._treeview_sort_column(
                self.career_batting_stats_treeview, _c, False))
            self.career_batting_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.career_batting_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)
        career_pitching_frame = ttk.LabelFrame(career_stats_pane, text="League Pitching Stats (Career)")
        career_stats_pane.add(career_pitching_frame, weight=1)
        self.career_pitching_stats_treeview = ttk.Treeview(career_pitching_frame, columns=self.cols_league_pitching,
                                                           show='headings', height=10)
        for col in self.cols_league_pitching:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (
                80 if col == "Team" else (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.career_pitching_stats_treeview.heading(col, text=col,
                                                        command=lambda _c=col: self._treeview_sort_column(
                                                            self.career_pitching_stats_treeview, _c, False))
            self.career_pitching_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.career_pitching_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Team Rosters & Stats Tab ---
        # This could also be moved to its own class gui.team_roster_tab.TeamRosterTab(self.right_pane_notebook, self)
        self.roster_tab_frame = ttk.Frame(self.right_pane_notebook)  # Placeholder
        self.right_pane_notebook.add(self.roster_tab_frame, text='Team Rosters & Stats')
        # ... (Full setup of roster_tab_frame combobox and treeviews as before, using self.cols_roster_batting for batting)
        roster_selector_frame = ttk.Frame(self.roster_tab_frame)
        roster_selector_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(roster_selector_frame, text="Select Team:").pack(side=tk.LEFT, padx=(0, 5))
        self.roster_team_combobox = ttk.Combobox(roster_selector_frame, textvariable=self.selected_team_for_roster_var,
                                                 state="readonly", width=40)
        self.roster_team_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.roster_team_combobox.bind("<<ComboboxSelected>>",
                                       self._on_roster_team_selected)  # This method stays in BaseballApp
        roster_stats_pane = ttk.PanedWindow(self.roster_tab_frame, orient=tk.VERTICAL)
        roster_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        roster_batting_frame = ttk.LabelFrame(roster_stats_pane, text="Batting Stats (Season)")
        roster_stats_pane.add(roster_batting_frame, weight=1)
        self.cols_roster_batting = ("Name", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG",
                                    "OBP", "SLG", "OPS", "BatRuns")
        self.roster_batting_treeview = ttk.Treeview(roster_batting_frame, columns=self.cols_roster_batting,
                                                    show='headings', height=8)
        for col in self.cols_roster_batting:
            width = 110 if col == "Name" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    60 if col != "BatRuns" else 65))
            anchor = tk.W if col == "Name" else tk.CENTER
            self.roster_batting_treeview.heading(col, text=col, command=lambda _c=col: self._treeview_sort_column(
                self.roster_batting_treeview, _c, False))
            self.roster_batting_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        self.roster_batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)
        roster_pitching_frame = ttk.LabelFrame(roster_stats_pane, text="Pitching Stats (Season)")
        roster_stats_pane.add(roster_pitching_frame, weight=1)
        self.cols_roster_pitching = ("Name", "Role", "IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR")
        self.roster_pitching_treeview = ttk.Treeview(roster_pitching_frame, columns=self.cols_roster_pitching,
                                                     show='headings', height=6)
        for col in self.cols_roster_pitching:
            width = 120 if col == "Name" else (50 if col == "IP" else 45)
            anchor = tk.W if col == "Name" else tk.CENTER
            self.roster_pitching_treeview.heading(col, text=col, command=lambda _c=col: self._treeview_sort_column(
                self.roster_pitching_treeview, _c, False))
            self.roster_pitching_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        self.roster_pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- GA Optimizer Tab ---
        # Instantiate the new GAOptimizerTab class
        self.ga_optimizer_tab = GAOptimizerTab(self.right_pane_notebook, self)  # Pass self (BaseballApp) as controller
        self.right_pane_notebook.add(self.ga_optimizer_tab, text='GA Team Optimizer')

        # --- Single Game Tab (Placeholder) ---
        self.single_game_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.single_game_tab_frame, text='Play Single Game')
        ttk.Label(self.single_game_tab_frame, text="Detailed single game playout (Phase 2).").pack(padx=20, pady=20)

        self._set_app_state("LOADING_PLAYERS")
        self._load_all_player_data_async()
        self.update_button_states()

    # Methods that were specific to _setup_ga_optimizer_tab are now in GAOptimizerTab class
    # such as _select_ga_benchmark_teams, _update_selected_benchmarks_label,
    # _draw_ga_fitness_plot, _display_best_ga_team.
    # BaseballApp will now call methods on its self.ga_optimizer_tab instance.

    def _set_app_state(self, new_state):  # Stays in BaseballApp
        self.app_state = new_state
        self.update_button_states()

    def _treeview_sort_column(self, tv, col, reverse):  # Stays in BaseballApp (general utility)
        # ... (Implementation as before, ensure BatRuns is in numeric_cols for relevant treeviews) ...
        try:
            data_list = []
            for k in tv.get_children(''):
                value = tv.set(k, col)
                try:
                    numeric_cols = []
                    # Check which treeview it is to apply correct numeric columns
                    if tv == self.standings_treeview:
                        numeric_cols = ["W", "L", "Win%", "ELO", "R", "RA", "Run Diff"]
                    elif tv in [self.roster_batting_treeview, self.league_batting_stats_treeview,
                                self.career_batting_stats_treeview]:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif hasattr(self,
                                 'ga_optimizer_tab') and tv == self.ga_optimizer_tab.best_team_batting_treeview:  # Accessing from GA tab
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]
                    elif tv in [self.roster_pitching_treeview, self.league_pitching_stats_treeview,
                                self.career_pitching_stats_treeview]:
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
                        elif col in ["AVG", "OBP", "SLG", "OPS"] and cleaned_value.startswith("."):
                            numeric_value = float(cleaned_value) if cleaned_value != ".---" else -1.0
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

    def _load_all_player_data_async(self):  # Stays
        self.log_message("Initiating player data load...")
        thread = threading.Thread(target=self._load_all_player_data_logic, daemon=True);
        thread.start()

    def _load_all_player_data_logic(self):  # Stays
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

    def log_message(self, message, internal=False):  # Stays (central logging)
        if not internal or "[GA]" in message or "ERROR" in message or "Warning" in message:
            self.root.after(0, lambda: self._log_to_widget(message))

    def _log_to_widget(self, message):  # Stays
        timestamp = time.strftime("%H:%M:%S")
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text_widget.see(tk.END)
        self.log_text_widget.config(state=tk.DISABLED)

    def update_button_states(self):  # Stays (controls app-wide button states)
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
            if ga_tab_exists:
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

    def prompt_clear_tournament_data(self):  # Stays
        if self.app_state not in ["IDLE", "SEASON_CONCLUDED"] or (
                self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive()):
            messagebox.showwarning("Operation in Progress", "Cannot clear data now.", parent=self.root);
            return
        if messagebox.askyesno("Confirm Clear", "Clear all tournament, GA data, and selected benchmarks?",
                               parent=self.root):
            self._clear_tournament_data_confirmed()

    def _clear_tournament_data_confirmed(self):  # Stays, calls GA tab reset
        self.log_message("Clearing all tournament and GA data...")
        self.all_teams = [];
        self.season_number = 0
        for tv in [self.standings_treeview, self.league_batting_stats_treeview, self.league_pitching_stats_treeview,
                   self.career_batting_stats_treeview, self.career_pitching_stats_treeview,
                   self.roster_batting_treeview, self.roster_pitching_treeview]:
            for i in tv.get_children(): tv.delete(i)

        if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
            self.ga_optimizer_tab.reset_ui()  # Tell GA tab to reset its UI

        self.log_text_widget.config(state=tk.NORMAL);
        self.log_text_widget.delete('1.0', tk.END);
        self.log_text_widget.config(state=tk.DISABLED)
        self.log_message("Data cleared. Ready for new run.")
        self._update_roster_tab_team_selector()  # This method needs to exist
        self._set_app_state("IDLE")

    # --- Tournament Methods (initialize_tournament_threaded, _initialize_tournament_logic, etc. stay in BaseballApp) ---
    def initialize_tournament_threaded(self):  # Stays
        if not self.all_players_data: messagebox.showerror("Error", "Player data not loaded."); return
        self._set_app_state("INITIALIZING_TOURNAMENT")
        self.log_message("Opening team selection for tournament...")
        # Now use the imported TeamSelectionDialog
        dialog = TeamSelectionDialog(self.root, self.num_teams_var.get(), dialog_title="Select Teams for Tournament")
        if dialog.selected_team_filepaths is None:
            self.log_message("Tournament team selection cancelled.");
            self._set_app_state("IDLE");
            return
        self.log_message(f"Selected {len(dialog.selected_team_filepaths)} teams for tournament. Initializing...")
        thread = threading.Thread(target=self._initialize_tournament_logic, args=(dialog.selected_team_filepaths,),
                                  daemon=True);
        thread.start()

    def _initialize_tournament_logic(self, selected_filepaths):  # Stays
        # ... (Implementation as before)
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
            self.log_message(f"Loaded {len(temp_teams)} user-selected teams.")
            to_generate = num_to_init - len(temp_teams)
            if to_generate > 0:
                self.log_message(f"Generating {to_generate} random teams.")
                if not self.all_players_data: self.log_message("ERROR: Player data missing!"); self.root.after(0,
                                                                                                               lambda: self._set_app_state(
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
                        self.log_message(f"Generated & saved {new_team.name}.")
                    else:
                        self.log_message(f"ERROR: Failed to gen {name}."); break
            self.all_teams = temp_teams;
            self.season_number = 0
            if self.all_teams:
                self.log_message(f"Running initial preseason for {len(self.all_teams)} teams...")
                tournament_preseason(self.all_teams, self.log_message);
                self.season_number = 1
                self.log_message(f"Initial preseason done.")
            self.log_message(f"Tournament initialized: {len(self.all_teams)} teams. Ready for S{self.season_number}.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._update_league_player_stats_display('season_stats', log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Init error: {e}");
            self.root.after(0, lambda: messagebox.showerror("Init Error", str(e)));
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_season_threaded(self):  # Stays
        # ... (Implementation as before)
        if not self.all_teams: messagebox.showwarning("No Teams", "Initialize first."); return
        self._set_app_state("SEASON_IN_PROGRESS")
        self.log_message(f"Starting Season {self.season_number}...")
        thread = threading.Thread(target=self._run_season_logic, daemon=True);
        thread.start()

    def _run_season_logic(self):  # Stays
        # ... (Implementation as before)
        try:
            if self.season_number > 0:
                self.log_message(f"--- S{self.season_number}: Pre-season stat reset ---")
                tournament_preseason(self.all_teams, self.log_message)
            self.log_message(f"--- S{self.season_number}: Regular Season Playing ---")
            tournament_play_season(self.all_teams, self.log_message)
            self.log_message("Season play complete. Saving data...")
            for team in self.all_teams:
                f_path = team.json_filepath if hasattr(team, 'json_filepath') and team.json_filepath else None
                if not f_path or not os.path.exists(os.path.dirname(f_path)):
                    num_match = re.search(r'Team[_ ](\d+)', team.name)
                    num = get_next_team_number(TEAMS_DIR) if not num_match else num_match.group(1)
                    s_name = re.sub(r'[^\w.-]', '_', team.name or f"Team{num}")
                    f_path = os.path.join(TEAMS_DIR, f"Team_{num}_{s_name}_{team.total_points}.json")
                save_team_to_json(team, f_path);
                team.json_filepath = f_path
            self.log_message("Team data saved.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, lambda: self._update_league_player_stats_display('season_stats', log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))
        except Exception as e:
            self.log_message(f"Season {self.season_number} error: {e}");
            self.root.after(0, lambda: messagebox.showerror(f"S{self.season_number} Error", str(e)));
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_postseason_and_prepare_threaded(self):  # Stays
        # ... (Implementation as before)
        if not self.all_teams or self.app_state != "SEASON_CONCLUDED": messagebox.showwarning("Invalid State",
                                                                                              "Run season first."); return
        self._set_app_state("POSTSEASON_IN_PROGRESS")
        self.log_message(f"--- S{self.season_number} Post-season & Prep ---")
        thread = threading.Thread(target=self._run_postseason_and_prepare_logic, daemon=True);
        thread.start()

    def _run_postseason_and_prepare_logic(self):  # Stays
        # ... (Implementation as before)
        try:
            survivors = [t for t in self.all_teams if t.team_stats.wins >= t.team_stats.losses]
            self.log_message(f"{len(self.all_teams) - len(survivors)} teams culled.")
            tournament_postseason_culling(survivors, self.log_message)
            self.all_teams = survivors
            to_regen = self.num_teams_var.get() - len(self.all_teams)
            if to_regen > 0:
                self.log_message(f"Regenerating {to_regen} teams...")
                if not self.all_players_data:
                    self.log_message("ERROR: Player data missing!");
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
                            self.log_message(f"Regenerated & saved {new_team.name}.")
                        else:
                            self.log_message(f"ERROR: Failed to regen {name}."); break
            self.season_number += 1
            self.log_message(f"Postseason done. Ready for S{self.season_number} with {len(self.all_teams)} teams.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._update_league_player_stats_display('season_stats', log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Postseason error: {e}");
            self.root.after(0, lambda: messagebox.showerror("Postseason Error", str(e)));
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))

    # --- GUI Update Methods for general tabs (Standings, Player Stats, Rosters) ---
    # These were re-added in a previous step
    def update_standings_display(self, teams_to_display):  # Stays
        # ... (Implementation as provided previously)
        for i in self.standings_treeview.get_children(): self.standings_treeview.delete(i)
        if not teams_to_display: return
        valid_teams_to_display = [t for t in teams_to_display if hasattr(t, 'team_stats') and t.team_stats is not None]
        sorted_teams = sorted(valid_teams_to_display, key=lambda t: (t.team_stats.wins, t.team_stats.elo_rating),
                              reverse=True)
        for team in sorted_teams:
            stats = team.team_stats
            win_pct = f".{int(stats.calculate_win_pct() * 1000):03d}" if stats.games_played > 0 else ".000"
            elo = f"{stats.elo_rating:.0f}"
            self.standings_treeview.insert("", tk.END, values=(team.name, stats.wins, stats.losses, win_pct, elo,
                                                               stats.team_runs_scored, stats.team_runs_allowed,
                                                               stats.run_differential))

    def _update_league_player_stats_display(self, stats_source_attr='season_stats', batting_treeview=None,
                                            pitching_treeview=None, log_prefix="Season"):  # Stays
        # ... (Implementation as provided previously, including BatRuns)
        if batting_treeview is None: batting_treeview = self.league_batting_stats_treeview
        if pitching_treeview is None: pitching_treeview = self.league_pitching_stats_treeview
        for i in batting_treeview.get_children(): batting_treeview.delete(i)
        for i in pitching_treeview.get_children(): pitching_treeview.delete(i)
        if not self.all_teams: return
        player_stats_map = {}
        for team_obj in self.all_teams:
            for player in team_obj.batters + team_obj.bench + team_obj.all_pitchers:
                player_key = (player.name, player.year, player.set)
                if player_key not in player_stats_map: player_stats_map[player_key] = {'player_obj': player,
                                                                                       'teams': set()}
                player_stats_map[player_key]['teams'].add(team_obj.name)
        batting_entries, pitching_entries = [], []
        for data in player_stats_map.values():
            player = data['player_obj'];
            team_name_disp = player.team_name or (list(data['teams'])[0] if data['teams'] else "N/A")
            p_stats = getattr(player, stats_source_attr, Stats())
            if isinstance(player, Batter):
                p_stats.update_hits();
                bat_runs = p_stats.calculate_batting_runs()
                batting_entries.append((player.name, player.year, player.set, team_name_disp, player.position,
                                        p_stats.plate_appearances, p_stats.at_bats, p_stats.runs_scored, p_stats.hits,
                                        p_stats.doubles, p_stats.triples, p_stats.home_runs, p_stats.rbi,
                                        p_stats.walks, p_stats.strikeouts, p_stats.calculate_avg(),
                                        p_stats.calculate_obp(), p_stats.calculate_slg(), p_stats.calculate_ops(),
                                        f"{bat_runs:.2f}"))
            elif isinstance(player, Pitcher):
                era, whip = p_stats.calculate_era(), p_stats.calculate_whip()
                pitching_entries.append(
                    (player.name, player.year, player.set, team_name_disp, player.team_role or player.position,
                     p_stats.get_formatted_ip(), f"{era:.2f}" if era != float('inf') else "INF",
                     f"{whip:.2f}" if whip != float('inf') else "INF", p_stats.batters_faced,
                     p_stats.strikeouts_thrown, p_stats.walks_allowed, p_stats.hits_allowed,
                     p_stats.runs_allowed, p_stats.earned_runs_allowed, p_stats.home_runs_allowed))
        for entry in batting_entries: batting_treeview.insert("", tk.END, values=entry)
        for entry in pitching_entries: pitching_treeview.insert("", tk.END, values=entry)

    def _update_career_player_stats_display(self):  # Stays
        # ... (Implementation as provided previously)
        self._update_league_player_stats_display(stats_source_attr='career_stats',
                                                 batting_treeview=self.career_batting_stats_treeview,
                                                 pitching_treeview=self.career_pitching_stats_treeview,
                                                 log_prefix="Career")

    def _update_roster_tab_team_selector(self):  # Stays
        # ... (Implementation as provided previously)
        team_names = [team.name for team in self.all_teams] if self.all_teams else []
        current_selection = self.selected_team_for_roster_var.get()
        self.roster_team_combobox['values'] = team_names
        if team_names:
            if current_selection in team_names:
                self.roster_team_combobox.set(current_selection)
            else:
                self.roster_team_combobox.set(team_names[0])
            self._on_roster_team_selected(None)
        else:
            self.roster_team_combobox.set(''); self._clear_roster_stats_display()

    def _on_roster_team_selected(self, event):  # Stays
        # ... (Implementation as provided previously, including BatRuns in display)
        selected_name = self.selected_team_for_roster_var.get()
        if not selected_name: self._clear_roster_stats_display(); return
        team_obj = next((t for t in self.all_teams if t.name == selected_name), None)
        if team_obj:
            self._display_selected_team_stats(team_obj)
        else:
            self.log_message(f"Team not found: {selected_name}"); self._clear_roster_stats_display()

    def _clear_roster_stats_display(self):  # Stays
        # ... (Implementation as provided previously)
        for i in self.roster_batting_treeview.get_children(): self.roster_batting_treeview.delete(i)
        for i in self.roster_pitching_treeview.get_children(): self.roster_pitching_treeview.delete(i)

    def _display_selected_team_stats(self, team_obj):  # Stays
        # ... (Implementation as provided previously, including BatRuns)
        self._clear_roster_stats_display()
        for player in team_obj.batters + team_obj.bench:
            s = player.season_stats if hasattr(player, 'season_stats') else Stats()
            s.update_hits();
            bat_runs = s.calculate_batting_runs()
            self.roster_batting_treeview.insert("", tk.END, values=(player.name, player.position,
                                                                    s.plate_appearances, s.at_bats, s.runs_scored,
                                                                    s.hits, s.doubles, s.triples, s.home_runs,
                                                                    s.rbi, s.walks, s.strikeouts, s.calculate_avg(),
                                                                    s.calculate_obp(), s.calculate_slg(),
                                                                    s.calculate_ops(), f"{bat_runs:.2f}"))
        for player in team_obj.all_pitchers:
            s = player.season_stats if hasattr(player, 'season_stats') else Stats()
            era, whip = s.calculate_era(), s.calculate_whip()
            self.roster_pitching_treeview.insert("", tk.END, values=(player.name, player.team_role or player.position,
                                                                     s.get_formatted_ip(),
                                                                     f"{era:.2f}" if era != float('inf') else "INF",
                                                                     f"{whip:.2f}" if whip != float('inf') else "INF",
                                                                     s.batters_faced, s.strikeouts_thrown,
                                                                     s.walks_allowed, s.hits_allowed, s.runs_allowed,
                                                                     s.earned_runs_allowed, s.home_runs_allowed))

    # --- GA Optimizer Process Management Methods (Controller Logic) ---
    def start_ga_optimizer_process(self, ga_params_from_tab, selected_benchmark_files):
        """
        Called by GAOptimizerTab to initiate the GA backend process.
        """
        self.log_message("GA process initiated by GA Tab...")
        self._set_app_state("GA_RUNNING")
        self.stop_ga_event.clear()

        # The GAOptimizerTab instance (self.ga_optimizer_tab) will handle clearing its own plot/UI
        # by BaseballApp calling a reset method on it, or it handles it internally on start.
        self.ga_optimizer_tab.reset_ui()  # Tell the tab to clear its specific displays

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
            min_team_points=MIN_TEAM_POINTS,  # Global constants
            max_team_points=MAX_TEAM_POINTS,  # Global constants
            log_callback=self.log_message,  # App's logger
            update_progress_callback=self._forward_ga_progress_to_tab,  # New forwarder
            stop_event=self.stop_ga_event
        )
        self.ga_optimizer_thread = threading.Thread(target=self._run_ga_logic_thread, daemon=True)
        self.ga_optimizer_thread.start()

    def _forward_ga_progress_to_tab(self, percentage, message, generation_num=None, best_fitness=None,
                                    avg_fitness=None):
        """Forwards progress from GA backend to the GAOptimizerTab instance for UI updates."""
        if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
            # Schedule the call on the GAOptimizerTab instance through the main Tkinter loop
            self.root.after(0, lambda: self.ga_optimizer_tab.update_progress_display(percentage, message))
            if generation_num is not None:  # Also forward plot data
                self.root.after(0, lambda: self.ga_optimizer_tab.update_plot_data(generation_num, best_fitness,
                                                                                  avg_fitness))

    def _run_ga_logic_thread(self):  # Renamed from _run_ga_logic to avoid confusion if old one existed
        """The target function for the GA optimizer thread."""
        best_candidate = None
        try:
            best_candidate = self.ga_optimizer.run()  # This blocks until GA is done or stopped

            if self.stop_ga_event.is_set():
                self.log_message("GA run was stopped by user (acknowledged in app_controller).")
            elif best_candidate and best_candidate.team:
                # Forward the best candidate to the GA tab for display
                self.root.after(0, lambda: self.ga_optimizer_tab.display_best_ga_team(best_candidate))

                # Saving the best team is a responsibility of the app controller
                team_name_part = re.sub(r'[^\w\.-]', '_', best_candidate.team.name)
                filename = os.path.join(TEAMS_DIR,
                                        f"GA_Best_{team_name_part}_Fit{best_candidate.fitness:.0f}_Pts{best_candidate.team.total_points}.json")
                save_team_to_json(best_candidate.team, filename)
                self.log_message(f"Best GA team ('{best_candidate.team.name}') saved as {os.path.basename(filename)}")
            else:
                self.log_message("GA finished: No valid best team found or stopped before completion.")

        except Exception as e:
            self.log_message(f"Error during GA execution thread: {e}")
            self.root.after(0, lambda: messagebox.showerror("GA Runtime Error",
                                                            f"An error occurred during GA processing: {e}",
                                                            parent=self.root))
        finally:
            self.ga_optimizer_thread = None  # Clear the thread attribute

            final_status_msg = "Status: GA Finished"
            if self.stop_ga_event.is_set():
                final_status_msg = "Status: GA Stopped by user"
            elif best_candidate is None and not self.stop_ga_event.is_set():  # No candidate and not stopped implies error or no valid result
                final_status_msg = "Status: GA Error or No Result"

            if hasattr(self, 'ga_optimizer_tab') and self.ga_optimizer_tab:
                # Ensure final plot/progress update on the tab
                self.root.after(0, lambda: self.ga_optimizer_tab.update_progress_display(100,
                                                                                         final_status_msg.split(": ")[
                                                                                             1]))
                if best_candidate is None and not self.stop_ga_event.is_set() and hasattr(self.ga_optimizer_tab,
                                                                                          'fitness_generations') and not self.ga_optimizer_tab.fitness_generations:  # if no plot data at all
                    self.root.after(0, self.ga_optimizer_tab.draw_fitness_plot)  # Draw empty plot with message

            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def stop_ga_search(self):  # Stays in BaseballApp to control the thread/event
        if self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive():
            self.log_message("Attempting to stop GA search (controller)...")
            self.stop_ga_event.set()
            # Button state will be updated by _set_app_state via _run_ga_logic_thread's finally block
        else:
            self.log_message("GA search is not currently running (controller).")