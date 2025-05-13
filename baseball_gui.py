# baseball_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import glob  # For finding team files
import time  # For timestamping logs

# Import your existing project modules
from team_management import (load_players_from_json, create_random_team,
                             save_team_to_json, load_team_from_json, get_next_team_number)
from game_logic import play_game  # Used by tournament functions
from entities import Team, Batter, Pitcher  # Ensure Team, Batter, Pitcher are imported
from tournament import (
    preseason as tournament_preseason,
    play_season as tournament_play_season,
    postseason as tournament_postseason_culling,
    get_formatted_season_leaders,
    PLAYER_DATA_FILE, TEAMS_DIR
)
from stats import Stats  # Import Stats for type checking or default creation

try:
    from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS
except ImportError:
    MIN_TEAM_POINTS = 4500  # Default fallback
    MAX_TEAM_POINTS = 5000  # Default fallback


class BaseballApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Baseball Simulator GUI")
        self.root.geometry("1350x850")  # Adjusted size for new columns

        self.all_teams = []
        self.season_number = 0
        self.num_teams_var = tk.IntVar(value=20)
        self.all_players_data = None
        self.app_state = "IDLE"
        self.selected_team_for_roster_var = tk.StringVar()

        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_pane_frame = ttk.Frame(self.main_pane, width=350)
        self.main_pane.add(self.left_pane_frame, weight=1)

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

        log_frame = ttk.LabelFrame(self.left_pane_frame, text="Simulation Log")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side=tk.BOTTOM)
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, relief=tk.SOLID,
                                                         borderwidth=1)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text_widget.config(state=tk.DISABLED)

        self.right_pane_notebook = ttk.Notebook(self.main_pane)
        self.main_pane.add(self.right_pane_notebook, weight=4)

        # Standings Tab
        self.standings_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.standings_tab_frame, text='Standings')
        cols_standings = ("Team", "W", "L", "Win%", "ELO", "R", "RA", "Run Diff")
        self.standings_treeview = ttk.Treeview(self.standings_tab_frame, columns=cols_standings, show='headings')
        for col in cols_standings:
            self.standings_treeview.heading(col, text=col,
                                            command=lambda _col=col: self._treeview_sort_column(self.standings_treeview,
                                                                                                _col, False))
            self.standings_treeview.column(col, width=85, anchor=tk.CENTER, stretch=tk.YES)
        self.standings_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # Player Statistics (Season) Tab
        self.player_stats_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.player_stats_tab_frame, text='Player Statistics (Season)')
        player_stats_pane = ttk.PanedWindow(self.player_stats_tab_frame, orient=tk.VERTICAL)
        player_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        league_batting_frame = ttk.LabelFrame(player_stats_pane, text="League Batting Stats (Season)")
        player_stats_pane.add(league_batting_frame, weight=1)
        # MODIFIED: Added "Year", "Set"
        self.cols_league_batting = ("Name", "Year", "Set", "Team", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI",
                                    "BB", "SO", "AVG", "OBP", "SLG", "OPS")
        self.league_batting_stats_treeview = ttk.Treeview(league_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)
        for col in self.cols_league_batting:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (80 if col == "Team" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.league_batting_stats_treeview.heading(col, text=col,
                                                       command=lambda _col=col: self._treeview_sort_column(
                                                           self.league_batting_stats_treeview, _col, False))
            self.league_batting_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.league_batting_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        league_pitching_frame = ttk.LabelFrame(player_stats_pane, text="League Pitching Stats (Season)")
        player_stats_pane.add(league_pitching_frame, weight=1)
        # MODIFIED: Added "Year", "Set"
        self.cols_league_pitching = ("Name", "Year", "Set", "Team", "Role", "IP", "ERA", "WHIP", "BF", "K", "BB", "H",
                                     "R", "ER", "HR")
        self.league_pitching_stats_treeview = ttk.Treeview(league_pitching_frame, columns=self.cols_league_pitching,
                                                           show='headings', height=10)
        for col in self.cols_league_pitching:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (
                80 if col == "Team" else (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.league_pitching_stats_treeview.heading(col, text=col,
                                                        command=lambda _col=col: self._treeview_sort_column(
                                                            self.league_pitching_stats_treeview, _col, False))
            self.league_pitching_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.league_pitching_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # Career Player Statistics Tab
        self.career_stats_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.career_stats_tab_frame, text='Player Statistics (Career)')
        career_stats_pane = ttk.PanedWindow(self.career_stats_tab_frame, orient=tk.VERTICAL)
        career_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        career_batting_frame = ttk.LabelFrame(career_stats_pane, text="League Batting Stats (Career)")
        career_stats_pane.add(career_batting_frame, weight=1)
        # Uses self.cols_league_batting which now includes Year/Set
        self.career_batting_stats_treeview = ttk.Treeview(career_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)
        for col in self.cols_league_batting:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (80 if col == "Team" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.career_batting_stats_treeview.heading(col, text=col,
                                                       command=lambda _col=col: self._treeview_sort_column(
                                                           self.career_batting_stats_treeview, _col, False))
            self.career_batting_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.career_batting_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        career_pitching_frame = ttk.LabelFrame(career_stats_pane, text="League Pitching Stats (Career)")
        career_stats_pane.add(career_pitching_frame, weight=1)
        # Uses self.cols_league_pitching which now includes Year/Set
        self.career_pitching_stats_treeview = ttk.Treeview(career_pitching_frame, columns=self.cols_league_pitching,
                                                           show='headings', height=10)
        for col in self.cols_league_pitching:
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (
                80 if col == "Team" else (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.career_pitching_stats_treeview.heading(col, text=col,
                                                        command=lambda _col=col: self._treeview_sort_column(
                                                            self.career_pitching_stats_treeview, _col, False))
            self.career_pitching_stats_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)
        self.career_pitching_stats_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        self.roster_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.roster_tab_frame, text='Team Rosters & Stats')
        roster_selector_frame = ttk.Frame(self.roster_tab_frame)
        roster_selector_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(roster_selector_frame, text="Select Team:").pack(side=tk.LEFT, padx=(0, 5))
        self.roster_team_combobox = ttk.Combobox(roster_selector_frame, textvariable=self.selected_team_for_roster_var,
                                                 state="readonly", width=40)
        self.roster_team_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.roster_team_combobox.bind("<<ComboboxSelected>>", self._on_roster_team_selected)
        roster_stats_pane = ttk.PanedWindow(self.roster_tab_frame, orient=tk.VERTICAL)
        roster_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        roster_batting_frame = ttk.LabelFrame(roster_stats_pane, text="Batting Stats (Season)")
        roster_stats_pane.add(roster_batting_frame, weight=1)
        self.cols_roster_batting = ("Name", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG",
                                    "OBP", "SLG", "OPS")
        self.roster_batting_treeview = ttk.Treeview(roster_batting_frame, columns=self.cols_roster_batting,
                                                    show='headings', height=8)
        for col in self.cols_roster_batting:
            width = 120 if col == "Name" else (
                45 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else 65)
            anchor = tk.W if col == "Name" else tk.CENTER
            self.roster_batting_treeview.heading(col, text=col, command=lambda _col=col: self._treeview_sort_column(
                self.roster_batting_treeview, _col, False))
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
            self.roster_pitching_treeview.heading(col, text=col, command=lambda _col=col: self._treeview_sort_column(
                self.roster_pitching_treeview, _col, False))
            self.roster_pitching_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        self.roster_pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        self.single_game_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.single_game_tab_frame, text='Play Single Game (Phase 2)')
        ttk.Label(self.single_game_tab_frame,
                  text="Detailed single game playout with Canvas will be implemented here.").pack(padx=20, pady=20)

        self._set_app_state("LOADING_PLAYERS")
        self._load_all_player_data_async()

    def _set_app_state(self, new_state):
        self.app_state = new_state
        self.update_button_states()

    def _treeview_sort_column(self, tv, col, reverse):
        try:
            data_list = []
            for k in tv.get_children(''):
                value = tv.set(k, col)
                try:
                    numeric_cols = []
                    # Define which columns are numeric for each specific treeview
                    if tv == self.standings_treeview:
                        numeric_cols = ["W", "L", "Win%", "ELO", "R", "RA", "Run Diff"]
                    elif tv == self.roster_batting_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "Year"]
                    elif tv == self.roster_pitching_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]
                    elif tv == self.league_batting_stats_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "Year"]
                    elif tv == self.career_batting_stats_treeview:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "Year"]
                    elif tv == self.league_pitching_stats_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]
                    elif tv == self.career_pitching_stats_treeview:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]

                    is_numeric_col = col in numeric_cols

                    if is_numeric_col:
                        cleaned_value = value.replace('%', '').replace('+', '')
                        if col == "IP" and '.' in cleaned_value:
                            parts = cleaned_value.split('.')
                            numeric_value = float(parts[0]) + (float(parts[1]) / 3.0) if len(parts) == 2 and parts[
                                1].isdigit() else float(parts[0])
                        elif col in ["AVG", "OBP", "SLG", "OPS"] and value.startswith("."):
                            numeric_value = float(value) if value != ".---" else -1.0
                        elif value.lower() == "inf":
                            numeric_value = float('inf')
                        elif value.lower() == "-inf":
                            numeric_value = float('-inf')
                        elif value.lower() == "nan":
                            numeric_value = float('inf') if col == "ERA" else -1.0
                        elif col == "Year":  # Treat Year as integer for sorting
                            numeric_value = int(cleaned_value) if cleaned_value.isdigit() else 0
                        else:
                            numeric_value = float(cleaned_value)
                        data_list.append((numeric_value, k))
                    else:
                        data_list.append((value.lower(), k))
                except ValueError:
                    data_list.append((value.lower(), k))

            if col == "ERA":
                data_list.sort(key=lambda t: t[0], reverse=not reverse)
            else:
                data_list.sort(key=lambda t: t[0], reverse=reverse)

            for index, (val, k) in enumerate(data_list):
                tv.move(k, '', index)

            tv.heading(col, command=lambda _col=col: self._treeview_sort_column(tv, _col, not reverse))
        except tk.TclError as e:
            self.log_message(f"Warning: TclError while sorting column {col}: {e}.")
        except Exception as e:
            self.log_message(f"Error sorting column {col}: {e}")

    def _load_all_player_data_async(self):
        self.log_message("Initiating player data load...")
        thread = threading.Thread(target=self._load_all_player_data_logic, daemon=True)
        thread.start()

    def _load_all_player_data_logic(self):
        try:
            self.all_players_data = load_players_from_json(PLAYER_DATA_FILE)
            if self.all_players_data:
                self.log_message(f"Successfully loaded {len(self.all_players_data)} players from {PLAYER_DATA_FILE}.")
                self.root.after(0, lambda: self._set_app_state("IDLE"))
            else:
                self.log_message(
                    f"ERROR: No player data loaded from {PLAYER_DATA_FILE}. Team generation will likely fail.")
                self.root.after(0, lambda: messagebox.showerror("Player Data Error",
                                                                f"Could not load player data from {PLAYER_DATA_FILE}. Please check the file."))
                self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Exception during player data load: {e}")
            self.root.after(0, lambda: messagebox.showerror("Player Data Exception", str(e)))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def log_message(self, message, internal=False):
        if not internal:
            self.root.after(0, lambda: self._log_to_widget(message))

    def _log_to_widget(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text_widget.see(tk.END)
        self.log_text_widget.config(state=tk.DISABLED)

    def update_button_states(self):
        current_state = self.app_state
        if current_state in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT", "SEASON_IN_PROGRESS",
                             "POSTSEASON_IN_PROGRESS"]:
            self.init_button.config(state=tk.DISABLED)
            self.run_season_button.config(state=tk.DISABLED)
            self.run_postseason_button.config(state=tk.DISABLED)
        elif current_state == "IDLE":
            self.init_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
            self.run_season_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)
            self.run_postseason_button.config(state=tk.DISABLED)
        elif current_state == "SEASON_CONCLUDED":
            self.init_button.config(state=tk.DISABLED)
            self.run_season_button.config(state=tk.DISABLED)
            self.run_postseason_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)

    def initialize_tournament_threaded(self):
        if not self.all_players_data:
            messagebox.showerror("Error", "Player data is not loaded. Cannot initialize teams.")
            self.log_message("Initialization aborted: Player data missing.")
            return
        self._set_app_state("INITIALIZING_TOURNAMENT")
        self.log_message("Starting tournament initialization process...")
        thread = threading.Thread(target=self._initialize_tournament_logic, daemon=True)
        thread.start()

    def _initialize_tournament_logic(self):
        try:
            num_teams_to_init = self.num_teams_var.get()
            self.log_message(f"Initializing {num_teams_to_init} teams...")
            temp_teams = []
            if os.path.exists(TEAMS_DIR) and os.path.isdir(TEAMS_DIR):
                available_team_files = sorted(glob.glob(os.path.join(TEAMS_DIR, 'Team_*.json')))
                for team_file in available_team_files:
                    if len(temp_teams) >= num_teams_to_init: break
                    team = load_team_from_json(team_file)
                    if team: temp_teams.append(team)
                self.log_message(f"Loaded {len(temp_teams)} existing teams from '{TEAMS_DIR}'.")
            else:
                self.log_message(
                    f"Teams directory '{TEAMS_DIR}' not found or is not a directory. Skipping loading existing teams.")
            teams_to_generate = num_teams_to_init - len(temp_teams)
            if teams_to_generate > 0:
                self.log_message(f"Need to generate {teams_to_generate} new teams.")
                if not self.all_players_data:
                    self.log_message("ERROR: Cannot generate teams, all_players_data is not loaded.")
                    self.root.after(0, lambda: messagebox.showerror("Error",
                                                                    "Player data not available for team generation."))
                    self.root.after(0, lambda: self._set_app_state("IDLE"))
                    return
                for i in range(teams_to_generate):
                    next_file_num = get_next_team_number(TEAMS_DIR)
                    actual_team_name = f"Random Team {next_file_num}"
                    self.log_message(f"Generating new team: {actual_team_name} (file number {next_file_num})...")
                    new_team = create_random_team(self.all_players_data, actual_team_name, MIN_TEAM_POINTS,
                                                  MAX_TEAM_POINTS)
                    if new_team:
                        temp_teams.append(new_team)
                        team_save_filename = f"Team_{next_file_num}_{new_team.total_points}.json"
                        team_save_filepath = os.path.join(TEAMS_DIR, team_save_filename)
                        save_team_to_json(new_team, team_save_filepath)
                        self.log_message(f"Generated and saved {new_team.name} as {team_save_filename}.")
                    else:
                        self.log_message(f"ERROR: Failed to generate team: {actual_team_name}. Stopping generation.")
                        break
            self.all_teams = temp_teams
            self.season_number = 1
            self.log_message(
                f"Tournament initialized with {len(self.all_teams)} teams. Ready for Season {self.season_number}.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._update_league_player_stats_display(stats_source_attr='season_stats',
                                                                                log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Error during initialization: {e}")
            self.root.after(0, lambda: messagebox.showerror("Initialization Error", str(e)))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_season_threaded(self):
        if not self.all_teams:
            messagebox.showwarning("No Teams", "Please initialize teams first.")
            return
        self._set_app_state("SEASON_IN_PROGRESS")
        self.log_message(f"Starting Season {self.season_number} simulation...")
        thread = threading.Thread(target=self._run_season_logic, daemon=True)
        thread.start()

    def _run_season_logic(self):
        try:
            self.log_message(f"--- Season {self.season_number}: Pre-season ---")
            tournament_preseason(self.all_teams, log_callback=self.log_message)
            self.log_message("Pre-season complete.")
            self.log_message(f"--- Season {self.season_number}: Regular Season Playing ---")
            tournament_play_season(self.all_teams, log_callback=self.log_message)
            self.log_message("Regular season play complete.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, lambda: self._update_league_player_stats_display(stats_source_attr='season_stats',
                                                                                log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))
        except Exception as e:
            self.log_message(f"Error during season {self.season_number} run: {e}")
            self.root.after(0, lambda: messagebox.showerror(f"Season {self.season_number} Error", str(e)))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def run_postseason_and_prepare_threaded(self):
        if not self.all_teams or self.app_state != "SEASON_CONCLUDED":
            messagebox.showwarning("Invalid State", "Cannot run postseason. Ensure a season has concluded.")
            return
        self._set_app_state("POSTSEASON_IN_PROGRESS")
        self.log_message(f"--- Season {self.season_number}: Post-season Culling & Regeneration ---")
        thread = threading.Thread(target=self._run_postseason_and_prepare_logic, daemon=True)
        thread.start()

    def _run_postseason_and_prepare_logic(self):
        try:
            survivors = [team for team in self.all_teams if team.team_stats.wins >= team.team_stats.losses]
            num_eliminated = len(self.all_teams) - len(survivors)
            self.log_message(f"{num_eliminated} teams eliminated based on W/L record.")
            tournament_postseason_culling(survivors, log_callback=self.log_message)
            self.log_message("Survivor stats reset for next season.")
            self.all_teams = survivors
            num_teams_needed = self.num_teams_var.get()
            teams_to_regenerate = num_teams_needed - len(self.all_teams)
            if teams_to_regenerate > 0:
                self.log_message(f"Regenerating {teams_to_regenerate} teams...")
                if not self.all_players_data:
                    self.log_message("ERROR: Cannot regenerate teams, all_players_data is not loaded.")
                else:
                    for i in range(teams_to_regenerate):
                        next_file_num = get_next_team_number(TEAMS_DIR)
                        actual_team_name = f"Random Team {next_file_num}"
                        self.log_message(
                            f"Generating replacement team: {actual_team_name} (file num {next_file_num})...")
                        new_team = create_random_team(self.all_players_data, actual_team_name, MIN_TEAM_POINTS,
                                                      MAX_TEAM_POINTS)
                        if new_team:
                            self.all_teams.append(new_team)
                            team_save_filename = f"Team_{next_file_num}_{new_team.total_points}.json"
                            team_save_filepath = os.path.join(TEAMS_DIR, team_save_filename)
                            save_team_to_json(new_team, team_save_filepath)
                            self.log_message(f"Regenerated and saved {new_team.name} as {team_save_filename}.")
                        else:
                            self.log_message(
                                f"ERROR: Failed to regenerate team: {actual_team_name}. Stopping regeneration.")
                            break
            self.season_number += 1
            self.log_message(
                f"Postseason complete. Ready for Season {self.season_number} with {len(self.all_teams)} teams.")
            self.root.after(0, lambda: self.update_standings_display(self.all_teams))
            self.root.after(0, self._update_roster_tab_team_selector)
            self.root.after(0, lambda: self._update_league_player_stats_display(stats_source_attr='season_stats',
                                                                                log_prefix="Season"))
            self.root.after(0, self._update_career_player_stats_display)
            self.root.after(0, lambda: self._set_app_state("IDLE"))
        except Exception as e:
            self.log_message(f"Error during postseason preparation: {e}")
            self.root.after(0, lambda: messagebox.showerror("Postseason Error", str(e)))
            self.root.after(0, lambda: self._set_app_state("SEASON_CONCLUDED"))

    def update_standings_display(self, teams_to_display):
        self.log_message("Updating standings display...", internal=True)
        for i in self.standings_treeview.get_children():
            self.standings_treeview.delete(i)
        if not teams_to_display:
            self.log_message("No teams to display in standings.")
            return
        valid_teams_to_display = []
        for team in teams_to_display:
            if hasattr(team, 'team_stats') and team.team_stats is not None:
                valid_teams_to_display.append(team)
            else:
                self.log_message(f"Warning: Team {team.name} missing team_stats. Skipping from standings.")
        sorted_teams = sorted(valid_teams_to_display, key=lambda t: (t.team_stats.wins, t.team_stats.elo_rating),
                              reverse=True)
        for team in sorted_teams:
            stats = team.team_stats
            win_pct_str = f".{int(stats.calculate_win_pct() * 1000):03d}" if stats.games_played > 0 else ".000"
            elo_str = f"{stats.elo_rating:.0f}"
            values = (team.name, stats.wins, stats.losses, win_pct_str,
                      elo_str,
                      stats.team_runs_scored,
                      stats.team_runs_allowed,
                      stats.run_differential)
            self.standings_treeview.insert("", tk.END, values=values)
        self.log_message("Standings display updated.")

    def _update_league_player_stats_display(self, stats_source_attr='season_stats', batting_treeview=None,
                                            pitching_treeview=None, log_prefix="Season"):
        if batting_treeview is None: batting_treeview = self.league_batting_stats_treeview
        if pitching_treeview is None: pitching_treeview = self.league_pitching_stats_treeview

        self.log_message(f"Updating league-wide player {log_prefix.lower()} statistics...", internal=True)
        for i in batting_treeview.get_children(): batting_treeview.delete(i)
        for i in pitching_treeview.get_children(): pitching_treeview.delete(i)

        if not self.all_teams:
            self.log_message(f"No teams available to display league player {log_prefix.lower()} stats.")
            return

        unique_player_objects = set()
        for team_obj in self.all_teams:
            unique_player_objects.update(team_obj.batters)
            unique_player_objects.update(team_obj.bench)
            unique_player_objects.update(team_obj.all_pitchers)

        all_league_players_list = list(unique_player_objects)
        batting_entries = []
        pitching_entries = []

        for player in all_league_players_list:
            player_stats = getattr(player, stats_source_attr, None)
            if player_stats is None:
                player_stats = Stats()
                setattr(player, stats_source_attr, player_stats)

            team_name = player.team_name if hasattr(player, 'team_name') and player.team_name else "N/A"
            player_year = player.year if hasattr(player, 'year') and player.year else ""
            player_set = player.set if hasattr(player, 'set') and player.set else ""

            if isinstance(player, Batter):
                player_stats.update_hits()
                batting_values = (
                    player.name, player_year, player_set, team_name, player.position,
                    player_stats.plate_appearances, player_stats.at_bats,
                    player_stats.runs_scored, player_stats.hits,
                    player_stats.doubles, player_stats.triples,
                    player_stats.home_runs, player_stats.rbi,
                    player_stats.walks, player_stats.strikeouts,
                    player_stats.calculate_avg(), player_stats.calculate_obp(),
                    player_stats.calculate_slg(), player_stats.calculate_ops()
                )
                batting_entries.append(batting_values)

            elif isinstance(player, Pitcher):
                era_val = player_stats.calculate_era()
                whip_val = player_stats.calculate_whip()
                pitching_values = (
                    player.name, player_year, player_set, team_name, player.team_role or player.position,
                    player_stats.get_formatted_ip(),
                    f"{era_val:.2f}" if era_val != float('inf') else "INF",
                    f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                    player_stats.batters_faced, player_stats.strikeouts_thrown,
                    player_stats.walks_allowed, player_stats.hits_allowed,
                    player_stats.runs_allowed, player_stats.earned_runs_allowed,
                    player_stats.home_runs_allowed
                )
                pitching_entries.append(pitching_values)

        for entry in batting_entries: batting_treeview.insert("", tk.END, values=entry)
        for entry in pitching_entries: pitching_treeview.insert("", tk.END, values=entry)

        self.log_message(f"League-wide player {log_prefix.lower()} statistics updated.")

    def _update_career_player_stats_display(self):
        self._update_league_player_stats_display(
            stats_source_attr='career_stats',
            batting_treeview=self.career_batting_stats_treeview,
            pitching_treeview=self.career_pitching_stats_treeview,
            log_prefix="Career"
        )

    def _update_roster_tab_team_selector(self):
        self.log_message("Updating team selector for roster tab...", internal=True)
        team_names = [team.name for team in self.all_teams] if self.all_teams else []
        self.roster_team_combobox['values'] = team_names
        if team_names:
            current_selection = self.selected_team_for_roster_var.get()
            if current_selection in team_names:
                self.roster_team_combobox.set(current_selection)
            else:
                self.roster_team_combobox.set(team_names[0])
                self._on_roster_team_selected(None)
        else:
            self.roster_team_combobox.set('')
            self._clear_roster_stats_display()
        self.log_message("Roster team selector updated.")

    def _on_roster_team_selected(self, event):
        selected_team_name = self.selected_team_for_roster_var.get()
        if not selected_team_name:
            self._clear_roster_stats_display()
            return
        selected_team_obj = None
        for team in self.all_teams:
            if team.name == selected_team_name:
                selected_team_obj = team
                break
        if selected_team_obj:
            self.log_message(f"Displaying roster stats for team: {selected_team_name}")
            self._display_selected_team_stats(selected_team_obj)
        else:
            self.log_message(f"Could not find team object for: {selected_team_name}")
            self._clear_roster_stats_display()

    def _clear_roster_stats_display(self):
        for i in self.roster_batting_treeview.get_children():
            self.roster_batting_treeview.delete(i)
        for i in self.roster_pitching_treeview.get_children():
            self.roster_pitching_treeview.delete(i)

    def _display_selected_team_stats(self, team_obj):
        self._clear_roster_stats_display()
        batters_to_display = team_obj.batters + team_obj.bench
        for player in batters_to_display:
            if not isinstance(player, Batter) or not hasattr(player, 'season_stats') or player.season_stats is None:
                player.season_stats = Stats()
            player.season_stats.update_hits()
            values = (
                player.name,
                player.position,
                player.season_stats.plate_appearances, player.season_stats.at_bats,
                player.season_stats.runs_scored, player.season_stats.hits,
                player.season_stats.doubles, player.season_stats.triples,
                player.season_stats.home_runs, player.season_stats.rbi,
                player.season_stats.walks, player.season_stats.strikeouts,
                player.season_stats.calculate_avg(), player.season_stats.calculate_obp(),
                player.season_stats.calculate_slg(), player.season_stats.calculate_ops()
            )
            self.roster_batting_treeview.insert("", tk.END, values=values)

        for player in team_obj.all_pitchers:
            if not isinstance(player, Pitcher) or not hasattr(player, 'season_stats') or player.season_stats is None:
                player.season_stats = Stats()
            era_val = player.season_stats.calculate_era()
            whip_val = player.season_stats.calculate_whip()
            values = (
                player.name,
                player.team_role or player.position,
                player.season_stats.get_formatted_ip(),
                f"{era_val:.2f}" if era_val != float('inf') else "INF",
                f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                player.season_stats.batters_faced, player.season_stats.strikeouts_thrown,
                player.season_stats.walks_allowed, player.season_stats.hits_allowed,
                player.season_stats.runs_allowed, player.season_stats.earned_runs_allowed,
                player.season_stats.home_runs_allowed
            )
            self.roster_pitching_treeview.insert("", tk.END, values=values)


if __name__ == "__main__":
    if not os.path.exists(TEAMS_DIR):
        try:
            os.makedirs(TEAMS_DIR)
            print(f"Created teams directory: {TEAMS_DIR}")
        except OSError as e:
            print(f"Error creating teams directory {TEAMS_DIR}: {e}")

    root = tk.Tk()
    app = BaseballApp(root)
    root.mainloop()
