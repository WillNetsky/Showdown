# baseball_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import glob
import time
import json
import re

# Matplotlib imports
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

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
from stats import Stats, TeamStats  # Assuming Stats class now has calculate_batting_runs()
from optimizer_ga import GeneticTeamOptimizer, GACandidate

try:
    from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS
except ImportError:
    MIN_TEAM_POINTS = 4500
    MAX_TEAM_POINTS = 5000


class TeamSelectionDialog(tk.Toplevel):
    def __init__(self, parent, teams_needed_or_allowed, dialog_title="Select Teams"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(dialog_title)
        self.parent = parent
        self.teams_needed_or_allowed = teams_needed_or_allowed
        self.selected_team_filepaths = None

        self.geometry("550x450")

        list_frame = ttk.Frame(self)
        list_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        instruction_text = f"Select up to {self.teams_needed_or_allowed} teams."
        if "Benchmark" in dialog_title:
            instruction_text += "\nSelected teams will be used as benchmarks. Remaining slots (if any, up to 'Num Benchmark Teams') will be filled by randomly generated teams."
        elif "Tournament" in dialog_title:
            instruction_text += "\nRemaining slots for the tournament will be auto-generated if fewer are selected."

        ttk.Label(list_frame, text=instruction_text, wraplength=500, justify=tk.LEFT).pack(pady=(0, 5))

        self.listbox_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.team_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, yscrollcommand=self.listbox_scrollbar.set,
                                       exportselection=False)
        self.listbox_scrollbar.config(command=self.team_listbox.yview)
        self.listbox_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.team_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.available_teams_data = []
        self._populate_team_list()

        button_frame = ttk.Frame(self)
        button_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.confirm_button = ttk.Button(button_frame, text="Confirm Selections", command=self._on_confirm)
        self.confirm_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.select_all_button = ttk.Button(button_frame, text="Select All Visible", command=self._select_all_visible)
        self.select_all_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.deselect_all_button = ttk.Button(button_frame, text="Deselect All", command=self._deselect_all)
        self.deselect_all_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=5, expand=True)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _populate_team_list(self):
        self.team_listbox.delete(0, tk.END)
        self.available_teams_data = []
        if not os.path.exists(TEAMS_DIR) or not os.path.isdir(TEAMS_DIR):
            self.team_listbox.insert(tk.END, f"Teams directory '{TEAMS_DIR}' not found.")
            return
        search_pattern = os.path.join(TEAMS_DIR, '**', '*.json')
        team_files = sorted(glob.glob(search_pattern, recursive=True))
        if not team_files:
            self.team_listbox.insert(tk.END, f"No saved teams (.json files) found in '{TEAMS_DIR}' or subdirectories.")
            return
        for filepath in team_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                team_name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
                elo = 1500.0
                if "team_stats_data" in data and data["team_stats_data"] is not None:
                    elo = data["team_stats_data"].get("elo_rating", 1500.0)
                relative_path = os.path.relpath(filepath, TEAMS_DIR)
                display_name_with_path = f"({os.path.dirname(relative_path)}) {team_name}" if relative_path != os.path.basename(
                    filepath) and os.path.dirname(relative_path) != '.' else team_name
                display_string = f"{display_name_with_path} (ELO: {elo:.0f})"
                self.available_teams_data.append((display_string, filepath))
                self.team_listbox.insert(tk.END, display_string)
            except Exception as e:
                log_msg = f"Error processing {filepath}: {e}"
                if hasattr(self.parent, 'log_message'):
                    self.parent.log_message(log_msg)
                else:
                    print(log_msg)
                self.team_listbox.insert(tk.END, f"Error: {os.path.basename(filepath)}")

    def _select_all_visible(self):
        self.team_listbox.select_set(0, tk.END)

    def _deselect_all(self):
        self.team_listbox.selection_clear(0, tk.END)

    def _on_confirm(self):
        selected_indices = self.team_listbox.curselection()
        if len(selected_indices) > self.teams_needed_or_allowed:
            messagebox.showwarning("Too Many Teams", f"Select no more than {self.teams_needed_or_allowed} teams.",
                                   parent=self)
            return
        self.selected_team_filepaths = [self.available_teams_data[i][1] for i in selected_indices]
        self.destroy()

    def _on_cancel(self):
        self.selected_team_filepaths = None
        self.destroy()


class BaseballApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Baseball Simulator GUI")
        self.root.geometry("1400x900")  # Adjusted width for new BatRuns column

        self.all_teams = []
        self.season_number = 0
        self.num_teams_var = tk.IntVar(value=20)
        self.all_players_data = None
        self.app_state = "IDLE"
        self.selected_team_for_roster_var = tk.StringVar()
        self.ga_optimizer_thread = None
        self.stop_ga_event = threading.Event()

        self.ga_pop_size_var = tk.IntVar(value=20)
        self.ga_num_generations_var = tk.IntVar(value=20)
        self.ga_mutation_rate_var = tk.DoubleVar(value=0.8)
        self.ga_mutation_swaps_var = tk.IntVar(value=1)
        self.ga_elitism_count_var = tk.IntVar(value=2)
        self.ga_num_benchmark_teams_var = tk.IntVar(value=5)
        self.ga_games_vs_each_benchmark_var = tk.IntVar(value=100)
        self.ga_immigration_rate_var = tk.DoubleVar(value=0.1)
        self.ga_selected_benchmark_filepaths = []
        self.ga_selected_benchmarks_label_var = tk.StringVar()
        self.ga_fitness_generations = []
        self.ga_fitness_best_values = []
        self.ga_fitness_avg_values = []
        self.ga_plot_initialized = False

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

        self.standings_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.standings_tab_frame, text='Standings')
        cols_standings = ("Team", "W", "L", "Win%", "ELO", "R", "RA", "Run Diff")
        self.standings_treeview = ttk.Treeview(self.standings_tab_frame, columns=cols_standings, show='headings')
        for col in cols_standings:
            self.standings_treeview.heading(col, text=col,
                                            command=lambda _c=col: self._treeview_sort_column(self.standings_treeview,
                                                                                              _c, False))
            self.standings_treeview.column(col, width=85, anchor=tk.CENTER, stretch=tk.YES)
        self.standings_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        self.player_stats_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.player_stats_tab_frame, text='Player Statistics (Season)')
        player_stats_pane = ttk.PanedWindow(self.player_stats_tab_frame, orient=tk.VERTICAL)
        player_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        league_batting_frame = ttk.LabelFrame(player_stats_pane, text="League Batting Stats (Season)")
        player_stats_pane.add(league_batting_frame, weight=1)
        self.cols_league_batting = ("Name", "Year", "Set", "Team", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI",
                                    "BB", "SO", "AVG", "OBP", "SLG", "OPS", "BatRuns")  # ADDED BatRuns
        self.league_batting_stats_treeview = ttk.Treeview(league_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)
        for col in self.cols_league_batting:
            w = 110 if col == "Name" else (45 if col == "Year" else (65 if col == "Set" else (70 if col == "Team" else (
                35 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    55 if col != "BatRuns" else 60)))))  # Adjusted widths
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

        self.career_stats_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.career_stats_tab_frame, text='Player Statistics (Career)')
        career_stats_pane = ttk.PanedWindow(self.career_stats_tab_frame, orient=tk.VERTICAL)
        career_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        career_batting_frame = ttk.LabelFrame(career_stats_pane, text="League Batting Stats (Career)")
        career_stats_pane.add(career_batting_frame, weight=1)
        self.career_batting_stats_treeview = ttk.Treeview(career_batting_frame, columns=self.cols_league_batting,
                                                          show='headings', height=10)  # Uses self.cols_league_batting
        for col in self.cols_league_batting:  # Reuses setup from league batting
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
                                                           show='headings', height=10)  # Uses self.cols_league_pitching
        for col in self.cols_league_pitching:  # Reuses setup from league pitching
            w = 120 if col == "Name" else (50 if col == "Year" else (70 if col == "Set" else (
                80 if col == "Team" else (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.career_pitching_stats_treeview.heading(col, text=col,
                                                        command=lambda _c=col: self._treeview_sort_column(
                                                            self.career_pitching_stats_treeview, _c, False))
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
                                    "OBP", "SLG", "OPS", "BatRuns")  # ADDED BatRuns
        self.roster_batting_treeview = ttk.Treeview(roster_batting_frame, columns=self.cols_roster_batting,
                                                    show='headings', height=8)
        for col in self.cols_roster_batting:
            width = 110 if col == "Name" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    60 if col != "BatRuns" else 65))  # Adjusted widths
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

        self.ga_optimizer_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.ga_optimizer_tab_frame, text='GA Team Optimizer')
        self._setup_ga_optimizer_tab()

        self.single_game_tab_frame = ttk.Frame(self.right_pane_notebook)
        self.right_pane_notebook.add(self.single_game_tab_frame, text='Play Single Game')
        ttk.Label(self.single_game_tab_frame, text="Detailed single game playout (Phase 2).").pack(padx=20, pady=20)

        self._set_app_state("LOADING_PLAYERS")
        self._load_all_player_data_async()
        self.update_button_states()
        self._update_selected_benchmarks_label()

    def _setup_ga_optimizer_tab(self):
        params_and_benchmark_select_outer_frame = ttk.Frame(self.ga_optimizer_tab_frame)
        params_and_benchmark_select_outer_frame.pack(padx=10, pady=10, fill="x")
        params_frame = ttk.LabelFrame(params_and_benchmark_select_outer_frame, text="GA Parameters")
        params_frame.pack(side=tk.LEFT, fill="y", expand=False, padx=(0, 10), anchor='nw')
        benchmark_select_frame_container = ttk.Frame(params_and_benchmark_select_outer_frame)
        benchmark_select_frame_container.pack(side=tk.LEFT, fill="x", expand=True, anchor='ne')
        benchmark_select_frame = ttk.LabelFrame(benchmark_select_frame_container, text="Benchmark Teams Setup")
        benchmark_select_frame.pack(pady=0, fill="x")
        self.select_benchmarks_button = ttk.Button(benchmark_select_frame, text="Select Custom Benchmark Teams",
                                                   command=self._select_ga_benchmark_teams)
        self.select_benchmarks_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ga_selected_benchmarks_display_label = ttk.Label(benchmark_select_frame,
                                                              textvariable=self.ga_selected_benchmarks_label_var)
        self.ga_selected_benchmarks_display_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(benchmark_select_frame, text=("If fewer custom benchmarks are selected than 'Num Benchmark Teams',\n"
                                                "remaining slots will be filled by new random teams."), wraplength=350,
                  justify=tk.LEFT).grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        param_labels = ["Population Size:", "Num Generations:", "Mutation Rate (0-1):",
                        "Mutation Swaps:", "Elitism Count:", "Num Benchmark Teams (Total):",
                        "Games vs Each Benchmark:", "Immigration Rate (0-1):"]
        param_vars = [self.ga_pop_size_var, self.ga_num_generations_var, self.ga_mutation_rate_var,
                      self.ga_mutation_swaps_var, self.ga_elitism_count_var, self.ga_num_benchmark_teams_var,
                      self.ga_games_vs_each_benchmark_var, self.ga_immigration_rate_var]
        for i, label_text in enumerate(param_labels):
            ttk.Label(params_frame, text=label_text).grid(row=i, column=0, padx=5, pady=3, sticky="w")
            ttk.Entry(params_frame, textvariable=param_vars[i], width=10).grid(row=i, column=1, padx=5, pady=3,
                                                                               sticky="ew")
        self.ga_num_benchmark_teams_var.trace_add("write", self._update_selected_benchmarks_label)

        ga_control_frame = ttk.Frame(self.ga_optimizer_tab_frame)
        ga_control_frame.pack(padx=10, pady=5, fill="x")
        self.start_ga_button = ttk.Button(ga_control_frame, text="Start GA Search",
                                          command=self.start_ga_search_threaded)
        self.start_ga_button.pack(side=tk.LEFT, padx=5)
        self.stop_ga_button = ttk.Button(ga_control_frame, text="Stop GA Search", command=self.stop_ga_search,
                                         state=tk.DISABLED)
        self.stop_ga_button.pack(side=tk.LEFT, padx=5)

        progress_frame = ttk.LabelFrame(self.ga_optimizer_tab_frame, text="GA Progress")
        progress_frame.pack(padx=10, pady=5, fill="x")
        self.ga_progress_var = tk.DoubleVar(value=0.0)
        self.ga_progressbar = ttk.Progressbar(progress_frame, variable=self.ga_progress_var, maximum=100)
        self.ga_progressbar.pack(fill="x", padx=5, pady=5, expand=True)
        self.ga_status_label_var = tk.StringVar(value="Status: Idle")
        ttk.Label(progress_frame, textvariable=self.ga_status_label_var).pack(fill="x", padx=5, pady=2)

        best_team_frame_outer = ttk.Frame(self.ga_optimizer_tab_frame)
        best_team_frame_outer.pack(padx=10, pady=10, fill="both", expand=True)
        plot_frame = ttk.LabelFrame(best_team_frame_outer, text="GA Fitness Over Generations")
        plot_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 5))
        self.ga_fig = Figure(figsize=(6, 3.5), dpi=100)  # Slightly smaller plot height
        self.ga_ax = self.ga_fig.add_subplot(111)
        self.ga_canvas = FigureCanvasTkAgg(self.ga_fig, master=plot_frame)
        self.ga_canvas_widget = self.ga_canvas.get_tk_widget()
        self.ga_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        try:
            toolbar = NavigationToolbar2Tk(self.ga_canvas, plot_frame, pack_toolbar=False)
            toolbar.update()
            toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        except Exception as e:
            self.log_message(f"Matplotlib toolbar error: {e}", internal=True)
        self.ga_plot_initialized = True
        self._draw_ga_fitness_plot()

        best_team_details_frame = ttk.LabelFrame(best_team_frame_outer, text="Best Team Found by GA")
        best_team_details_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=(5, 0))
        self.ga_best_team_info_var = tk.StringVar(value="Best: N/A | Fitness: N/A | Pts: N/A")
        ttk.Label(best_team_details_frame, textvariable=self.ga_best_team_info_var).pack(pady=5, fill="x", padx=5)
        best_team_stats_pane = ttk.PanedWindow(best_team_details_frame, orient=tk.VERTICAL)
        best_team_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        ga_batting_frame = ttk.LabelFrame(best_team_stats_pane, text="Best Team - Batting (Eval Stats)")
        best_team_stats_pane.add(ga_batting_frame, weight=1)
        # Use self.cols_roster_batting which now includes BatRuns
        self.ga_best_team_batting_treeview = ttk.Treeview(ga_batting_frame, columns=self.cols_roster_batting,
                                                          show='headings', height=6)
        for col in self.cols_roster_batting:
            width = 110 if col == "Name" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    60 if col != "BatRuns" else 65))
            anchor = tk.W if col == "Name" else tk.CENTER
            self.ga_best_team_batting_treeview.heading(col, text=col, command=lambda _c=col: self._treeview_sort_column(
                self.ga_best_team_batting_treeview, _c, False))
            self.ga_best_team_batting_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        self.ga_best_team_batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        ga_pitching_frame = ttk.LabelFrame(best_team_stats_pane, text="Best Team - Pitching (Eval Stats)")
        best_team_stats_pane.add(ga_pitching_frame, weight=1)
        self.ga_best_team_pitching_treeview = ttk.Treeview(ga_pitching_frame, columns=self.cols_roster_pitching,
                                                           show='headings', height=5)
        for col in self.cols_roster_pitching:
            width = 120 if col == "Name" else (50 if col == "IP" else 45)
            anchor = tk.W if col == "Name" else tk.CENTER
            self.ga_best_team_pitching_treeview.heading(col, text=col,
                                                        command=lambda _c=col: self._treeview_sort_column(
                                                            self.ga_best_team_pitching_treeview, _c, False))
            self.ga_best_team_pitching_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        self.ga_best_team_pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def _update_roster_tab_team_selector(self):
        # self.log_message("Updating team selector for roster tab...", internal=True)
        team_names = [team.name for team in self.all_teams] if self.all_teams else []
        current_selection = self.selected_team_for_roster_var.get()

        self.roster_team_combobox['values'] = team_names
        if team_names:
            if current_selection in team_names:
                self.roster_team_combobox.set(current_selection)
            else:  # If previous selection is gone (e.g. team eliminated), default to first team
                self.roster_team_combobox.set(team_names[0])
            # Trigger the update for the (newly) set current selection
            # This needs to call the method that populates the roster stats
            self._on_roster_team_selected(None)  # Pass None as event object
        else:  # No teams
            self.roster_team_combobox.set('')
            self._clear_roster_stats_display()
        # self.log_message("Roster team selector updated.", internal=True)

    def _on_roster_team_selected(self, event):  # The missing method
        selected_team_name = self.selected_team_for_roster_var.get()
        if not selected_team_name:
            self._clear_roster_stats_display()
            return

        selected_team_obj = None
        for team in self.all_teams:  # self.all_teams should hold the current list of Team objects
            if team.name == selected_team_name:
                selected_team_obj = team
                break

        if selected_team_obj:
            # self.log_message(f"Displaying roster stats for team: {selected_team_name}", internal=True)
            self._display_selected_team_stats(selected_team_obj)
        else:
            # This case should ideally not happen if combobox is populated from self.all_teams
            self.log_message(f"Could not find team object for: {selected_team_name} in _on_roster_team_selected")
            self._clear_roster_stats_display()

    def _clear_roster_stats_display(self):
        for i in self.roster_batting_treeview.get_children():
            self.roster_batting_treeview.delete(i)
        for i in self.roster_pitching_treeview.get_children():
            self.roster_pitching_treeview.delete(i)

    def _display_selected_team_stats(self, team_obj):
        self._clear_roster_stats_display()

        # Batting Stats for the selected team's roster
        batters_to_display = team_obj.batters + team_obj.bench
        for player in batters_to_display:
            # Ensure player.season_stats exists and is the correct type
            player_stats = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                                 Stats) else Stats()

            player_stats.update_hits()  # Ensure derived batting stats are correct
            batting_runs = player_stats.calculate_batting_runs()  # Calculate Batting Runs

            values = (
                player.name,
                player.position,
                player_stats.plate_appearances, player_stats.at_bats,
                player_stats.runs_scored, player_stats.hits,
                player_stats.doubles, player_stats.triples,
                player_stats.home_runs, player_stats.rbi,
                player_stats.walks, player_stats.strikeouts,
                player_stats.calculate_avg(), player_stats.calculate_obp(),
                player_stats.calculate_slg(), player_stats.calculate_ops(),
                f"{batting_runs:.2f}"  # Add formatted Batting Runs
            )
            self.roster_batting_treeview.insert("", tk.END, values=values)

        # Pitching Stats for the selected team's roster
        for player in team_obj.all_pitchers:
            player_stats = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                                 Stats) else Stats()

            era_val = player_stats.calculate_era()
            whip_val = player_stats.calculate_whip()
            values = (
                player.name,
                player.team_role or player.position,  # Display team_role if available, else card position
                player_stats.get_formatted_ip(),
                f"{era_val:.2f}" if era_val != float('inf') else "INF",
                f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                player_stats.batters_faced, player_stats.strikeouts_thrown,
                player_stats.walks_allowed, player_stats.hits_allowed,
                player_stats.runs_allowed, player_stats.earned_runs_allowed,
                player_stats.home_runs_allowed
            )
            self.roster_pitching_treeview.insert("", tk.END, values=values)

    def _update_selected_benchmarks_label(self, *args):
        try:
            num_selected = len(self.ga_selected_benchmark_filepaths)
            num_desired = self.ga_num_benchmark_teams_var.get()
            self.ga_selected_benchmarks_label_var.set(f"Custom Benchmarks Selected: {num_selected} / {num_desired}")
        except tk.TclError:
            pass
        except Exception as e:
            self.log_message(f"Error updating benchmark label: {e}", internal=True)

    def _select_ga_benchmark_teams(self):
        if not self.all_players_data: messagebox.showerror("Error", "Player data not loaded.", parent=self.root); return
        try:
            num_benchmarks_max = self.ga_num_benchmark_teams_var.get()
        except tk.TclError:
            messagebox.showerror("Invalid Input", "'Num Benchmark Teams' must be a number.", parent=self.root); return
        if num_benchmarks_max <= 0:
            messagebox.showinfo("Info", "Num Benchmark Teams is <= 0. All benchmarks will be random if any are used.",
                                parent=self.root)
            self.ga_selected_benchmark_filepaths = []
            self._update_selected_benchmarks_label()
            return
        dialog = TeamSelectionDialog(self.root, teams_needed_or_allowed=num_benchmarks_max,
                                     dialog_title=f"Select up to {num_benchmarks_max} Custom Benchmarks")
        if dialog.selected_team_filepaths is not None:
            self.ga_selected_benchmark_filepaths = dialog.selected_team_filepaths
            self.log_message(f"Selected {len(self.ga_selected_benchmark_filepaths)} custom benchmark teams.")
        else:
            self.log_message("Benchmark selection cancelled.")
        self._update_selected_benchmarks_label()

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
                    if tv == self.standings_treeview:
                        numeric_cols = ["W", "L", "Win%", "ELO", "R", "RA", "Run Diff"]
                    elif tv in [self.roster_batting_treeview, self.league_batting_stats_treeview,
                                self.career_batting_stats_treeview, self.ga_best_team_batting_treeview]:
                        numeric_cols = ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP", "SLG",
                                        "OPS", "BatRuns", "Year"]  # ADDED BatRuns
                    elif tv in [self.roster_pitching_treeview, self.league_pitching_stats_treeview,
                                self.career_pitching_stats_treeview, self.ga_best_team_pitching_treeview]:
                        numeric_cols = ["IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR", "Year"]

                    is_numeric_col = col in numeric_cols
                    if is_numeric_col:
                        cleaned_value = str(value).replace('%', '').replace('+',
                                                                            '')  # Ensure value is string for replace
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
                            numeric_value = float(cleaned_value)  # BatRuns will be float
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

        if is_ga_running or current_state == "GA_RUNNING":
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button, self.start_ga_button,
                        self.select_benchmarks_button]: btn.config(state=tk.DISABLED)
            self.stop_ga_button.config(state=tk.NORMAL)
        elif current_state in ["LOADING_PLAYERS", "INITIALIZING_TOURNAMENT", "SEASON_IN_PROGRESS",
                               "POSTSEASON_IN_PROGRESS"]:
            for btn in [self.init_button, self.run_season_button, self.run_postseason_button, self.start_ga_button,
                        self.stop_ga_button, self.select_benchmarks_button]: btn.config(state=tk.DISABLED)
        elif current_state == "IDLE":
            self.init_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
            self.run_season_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)
            self.run_postseason_button.config(state=tk.DISABLED)
            self.start_ga_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
            self.stop_ga_button.config(state=tk.DISABLED)
            self.select_benchmarks_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
        elif current_state == "SEASON_CONCLUDED":
            self.init_button.config(state=tk.DISABLED)
            self.run_season_button.config(state=tk.DISABLED)
            self.run_postseason_button.config(state=tk.NORMAL if self.all_teams else tk.DISABLED)
            self.start_ga_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)
            self.stop_ga_button.config(state=tk.DISABLED)
            self.select_benchmarks_button.config(state=tk.NORMAL if self.all_players_data else tk.DISABLED)

    def prompt_clear_tournament_data(self):
        if self.app_state not in ["IDLE", "SEASON_CONCLUDED"] or (
                self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive()):
            messagebox.showwarning("Operation in Progress", "Cannot clear data now.", parent=self.root);
            return
        if messagebox.askyesno("Confirm Clear", "Clear all tournament, GA data, and selected benchmarks?",
                               parent=self.root):
            self._clear_tournament_data_confirmed()

    def _clear_tournament_data_confirmed(self):
        self.log_message("Clearing all tournament and GA data...")
        self.all_teams = [];
        self.season_number = 0
        for tv in [self.standings_treeview, self.league_batting_stats_treeview, self.league_pitching_stats_treeview,
                   self.career_batting_stats_treeview, self.career_pitching_stats_treeview,
                   self.roster_batting_treeview, self.roster_pitching_treeview,
                   self.ga_best_team_batting_treeview, self.ga_best_team_pitching_treeview]:
            for i in tv.get_children(): tv.delete(i)
        self.ga_best_team_info_var.set("Best: N/A | Fitness: N/A | Pts: N/A")
        self.ga_progress_var.set(0.0);
        self.ga_status_label_var.set("Status: Idle")
        self.ga_selected_benchmark_filepaths = [];
        self._update_selected_benchmarks_label()
        self.ga_fitness_generations.clear();
        self.ga_fitness_best_values.clear();
        self.ga_fitness_avg_values.clear()
        if self.ga_plot_initialized: self.root.after(0, self._draw_ga_fitness_plot)
        self.log_text_widget.config(state=tk.NORMAL);
        self.log_text_widget.delete('1.0', tk.END);
        self.log_text_widget.config(state=tk.DISABLED)
        self.log_message("Data cleared. Ready for new run.")
        self._update_roster_tab_team_selector()
        self._set_app_state("IDLE")

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

    def run_season_threaded(self):
        if not self.all_teams: messagebox.showwarning("No Teams", "Initialize first."); return
        self._set_app_state("SEASON_IN_PROGRESS")
        self.log_message(f"Starting Season {self.season_number}...")
        thread = threading.Thread(target=self._run_season_logic, daemon=True);
        thread.start()

    def _run_season_logic(self):
        try:
            if self.season_number > 0:
                self.log_message(f"--- S{self.season_number}: Pre-season stat reset ---")
                tournament_preseason(self.all_teams, self.log_message)
            self.log_message(f"--- S{self.season_number}: Regular Season Playing ---")
            tournament_play_season(self.all_teams, self.log_message)  # play_game is called here
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

    def run_postseason_and_prepare_threaded(self):
        if not self.all_teams or self.app_state != "SEASON_CONCLUDED": messagebox.showwarning("Invalid State",
                                                                                              "Run season first."); return
        self._set_app_state("POSTSEASON_IN_PROGRESS")
        self.log_message(f"--- S{self.season_number} Post-season & Prep ---")
        thread = threading.Thread(target=self._run_postseason_and_prepare_logic, daemon=True);
        thread.start()

    def _run_postseason_and_prepare_logic(self):
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

    # Add these methods to your BaseballApp class in baseball_gui.py

    def update_standings_display(self, teams_to_display):
        # self.log_message("Updating standings display...", internal=True) # Optional: for debugging
        for i in self.standings_treeview.get_children():
            self.standings_treeview.delete(i)

        if not teams_to_display:
            # self.log_message("No teams to display in standings.", internal=True) # Optional
            return

        valid_teams_to_display = []
        for team in teams_to_display:
            if hasattr(team, 'team_stats') and team.team_stats is not None:
                valid_teams_to_display.append(team)
            else:
                self.log_message(
                    f"Warning: Team {team.name if hasattr(team, 'name') else 'Unnamed Team'} missing team_stats. Skipping from standings.")

        # Sort teams by wins, then ELO as a tie-breaker
        sorted_teams = sorted(valid_teams_to_display, key=lambda t: (t.team_stats.wins, t.team_stats.elo_rating),
                              reverse=True)

        for team in sorted_teams:
            stats = team.team_stats
            win_pct_str = f".{int(stats.calculate_win_pct() * 1000):03d}" if stats.games_played > 0 else ".000"
            elo_str = f"{stats.elo_rating:.0f}"
            values = (
                team.name,
                stats.wins,
                stats.losses,
                win_pct_str,
                elo_str,
                stats.team_runs_scored,
                stats.team_runs_allowed,
                stats.run_differential
            )
            self.standings_treeview.insert("", tk.END, values=values)
        # self.log_message("Standings display updated.", internal=True) # Optional

    def _update_league_player_stats_display(self, stats_source_attr='season_stats', batting_treeview=None,
                                            pitching_treeview=None, log_prefix="Season"):
        if batting_treeview is None:
            batting_treeview = self.league_batting_stats_treeview
        if pitching_treeview is None:
            pitching_treeview = self.league_pitching_stats_treeview

        # self.log_message(f"Updating league-wide player {log_prefix.lower()} statistics...", internal=True) # Optional
        for i in batting_treeview.get_children(): batting_treeview.delete(i)
        for i in pitching_treeview.get_children(): pitching_treeview.delete(i)

        if not self.all_teams:
            # self.log_message(f"No teams available to display league player {log_prefix.lower()} stats.", internal=True) # Optional
            return

        # Collect unique player objects across all teams to avoid double counting if a player card could appear on multiple teams
        # (though in a tournament, a player instance is usually tied to one team at a time)
        # For league-wide stats, we want each player card's cumulative stats for that period (season/career).
        player_stats_map = {}  # Key: (name, year, set), Value: (player_object_for_stats, list_of_team_names_they_played_for)

        for team_obj in self.all_teams:
            for player in team_obj.batters + team_obj.bench + team_obj.all_pitchers:
                player_key = (player.name, player.year, player.set)

                # For league-wide display, we need *the player's own accumulated stats object*.
                # If a player object might be shared or duplicated with different stat objects, this needs careful handling.
                # Assuming player objects in self.all_teams hold their definitive season/career stats:
                if player_key not in player_stats_map:
                    player_stats_map[player_key] = {'player_obj': player, 'teams': set()}
                player_stats_map[player_key]['teams'].add(team_obj.name)

        batting_entries = []
        pitching_entries = []

        for data in player_stats_map.values():
            player = data['player_obj']
            # Join team names if a player was on multiple teams (e.g., if traded, though less common in this sim type)
            # For display, typically show their current or primary team.
            # Let's just use the team name from the first encounter or a generic if multiple.
            # This part might need refinement based on how you want to attribute stats if players change teams.
            # For simplicity, we'll use the team name associated with the player object instance.
            team_name_for_display = player.team_name if hasattr(player, 'team_name') and player.team_name else \
            list(data['teams'])[0] if data['teams'] else "N/A"

            player_actual_stats = getattr(player, stats_source_attr, None)
            if not isinstance(player_actual_stats, Stats):  # Ensure it's a Stats object
                player_actual_stats = Stats()
                # Optionally log a warning if stats were missing and had to be created fresh
                # self.log_message(f"Warning: Missing {stats_source_attr} for {player.name} on {team_name_for_display}. Displaying empty stats.", internal=True)

            player_year = player.year if hasattr(player, 'year') and player.year else ""
            player_set = player.set if hasattr(player, 'set') and player.set else ""

            if isinstance(player, Batter):
                player_actual_stats.update_hits()  # Ensure derived batting stats like AVG/OBP/SLG are current
                batting_runs = player_actual_stats.calculate_batting_runs()  # Calculate Batting Runs

                batting_values = (
                    player.name, player_year, player_set, team_name_for_display, player.position,
                    player_actual_stats.plate_appearances, player_actual_stats.at_bats,
                    player_actual_stats.runs_scored, player_actual_stats.hits,
                    player_actual_stats.doubles, player_actual_stats.triples,
                    player_actual_stats.home_runs, player_actual_stats.rbi,
                    player_actual_stats.walks, player_actual_stats.strikeouts,
                    player_actual_stats.calculate_avg(), player_actual_stats.calculate_obp(),
                    player_actual_stats.calculate_slg(), player_actual_stats.calculate_ops(),
                    f"{batting_runs:.2f}"  # Add formatted Batting Runs
                )
                batting_entries.append(batting_values)
            elif isinstance(player, Pitcher):
                era_val = player_actual_stats.calculate_era()
                whip_val = player_actual_stats.calculate_whip()
                pitching_values = (
                    player.name, player_year, player_set, team_name_for_display,
                    player.team_role or player.position,
                    player_actual_stats.get_formatted_ip(),
                    f"{era_val:.2f}" if era_val != float('inf') else "INF",
                    f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                    player_actual_stats.batters_faced, player_actual_stats.strikeouts_thrown,
                    player_actual_stats.walks_allowed, player_actual_stats.hits_allowed,
                    player_actual_stats.runs_allowed, player_actual_stats.earned_runs_allowed,
                    player_actual_stats.home_runs_allowed
                )
                pitching_entries.append(pitching_values)

        for entry in batting_entries: batting_treeview.insert("", tk.END, values=entry)
        for entry in pitching_entries: pitching_treeview.insert("", tk.END, values=entry)
        # self.log_message(f"League-wide player {log_prefix.lower()} statistics updated.", internal=True) # Optional

    def _update_career_player_stats_display(self):
        self._update_league_player_stats_display(
            stats_source_attr='career_stats',  # Key difference
            batting_treeview=self.career_batting_stats_treeview,
            pitching_treeview=self.career_pitching_stats_treeview,
            log_prefix="Career"
        )

    # --- GA Methods (start_ga_search_threaded, _run_ga_logic, etc. as previously updated) ---
    # --- Plot Methods (_update_ga_progress, _draw_ga_fitness_plot as previously updated) ---
    # --- Display Best GA Team (_display_best_ga_team as previously updated, now including BatRuns) ---

    def start_ga_search_threaded(self):
        if not self.all_players_data: messagebox.showerror("Error", "Player data not loaded."); return
        if self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive(): messagebox.showwarning("In Progress",
                                                                                                    "GA search already running."); return
        self.log_message("Starting GA Team Optimizer search...")
        self._set_app_state("GA_RUNNING")
        self.stop_ga_event.clear()
        self.ga_fitness_generations.clear();
        self.ga_fitness_best_values.clear();
        self.ga_fitness_avg_values.clear()
        if self.ga_plot_initialized: self.root.after(0, self._draw_ga_fitness_plot)
        try:
            pop_size = self.ga_pop_size_var.get()
            num_gens = self.ga_num_generations_var.get()
            mut_rate = self.ga_mutation_rate_var.get()
            mut_swaps = self.ga_mutation_swaps_var.get()
            elitism = self.ga_elitism_count_var.get()
            num_bench_total = self.ga_num_benchmark_teams_var.get()
            games_vs_each = self.ga_games_vs_each_benchmark_var.get()
            imm_rate = self.ga_immigration_rate_var.get()
            custom_benchmark_files = list(self.ga_selected_benchmark_filepaths)
            if len(custom_benchmark_files) > num_bench_total:
                messagebox.showwarning("Benchmark Selection Truncated",
                                       f"Selected {len(custom_benchmark_files)}, using first {num_bench_total}.",
                                       parent=self.root)
                custom_benchmark_files = custom_benchmark_files[:num_bench_total]
            if not (0 < pop_size <= 500 and 0 < num_gens <= 2000 and 0.0 <= mut_rate <= 1.0 and \
                    0 < mut_swaps <= 10 and 0 <= elitism < pop_size and \
                    0 <= num_bench_total <= 20 and 0 < games_vs_each <= 1000 and 0.0 <= imm_rate <= 0.5):
                messagebox.showerror("Invalid GA Parameters", "Check ranges.", parent=self.root);
                self._set_app_state("IDLE");
                return
        except tk.TclError:
            messagebox.showerror("Invalid Input", "GA params must be numbers.", parent=self.root); self._set_app_state(
                "IDLE"); return
        self.ga_optimizer = GeneticTeamOptimizer(
            all_players_list=self.all_players_data, population_size=pop_size, num_generations=num_gens,
            mutation_rate=mut_rate, num_mutation_swaps=mut_swaps, elitism_count=elitism,
            num_benchmark_teams=num_bench_total, games_vs_each_benchmark=games_vs_each,
            immigration_rate=imm_rate, benchmark_archetype_files=custom_benchmark_files,
            min_team_points=MIN_TEAM_POINTS, max_team_points=MAX_TEAM_POINTS,
            log_callback=self.log_message, update_progress_callback=self._update_ga_progress,
            stop_event=self.stop_ga_event)
        self.ga_optimizer_thread = threading.Thread(target=self._run_ga_logic, daemon=True);
        self.ga_optimizer_thread.start()

    def _run_ga_logic(self):
        try:
            best_candidate = self.ga_optimizer.run()
            if self.stop_ga_event.is_set():
                self.log_message("GA run stopped by user.")
            elif best_candidate and best_candidate.team:
                self.root.after(0, lambda: self._display_best_ga_team(best_candidate))
                name_part = re.sub(r'[^\w.-]', '_', best_candidate.team.name)
                filename = os.path.join(TEAMS_DIR,
                                        f"GA_Best_{name_part}_Fit{best_candidate.fitness:.0f}_Pts{best_candidate.team.total_points}.json")
                save_team_to_json(best_candidate.team, filename)
                self.log_message(f"Best GA team saved: {os.path.basename(filename)}")
            else:
                self.log_message("GA: No valid best team or stopped early.")
        except Exception as e:
            self.log_message(f"GA execution error: {e}");
            self.root.after(0, lambda: messagebox.showerror("GA Error", f"Error: {e}", parent=self.root))
        finally:
            self.ga_optimizer_thread = None
            if self.ga_plot_initialized and self.ga_fitness_generations: self.root.after(0, self._draw_ga_fitness_plot)
            status = "Status: GA Finished"
            if self.stop_ga_event.is_set():
                status = "Status: GA Stopped"
            elif not self.ga_fitness_generations:
                status = "Status: GA Error/No Run"
            self.root.after(0, lambda: self.ga_status_label_var.set(status))
            self.root.after(0, lambda: self._set_app_state("IDLE"))

    def stop_ga_search(self):
        if self.ga_optimizer_thread and self.ga_optimizer_thread.is_alive():
            self.log_message("Attempting to stop GA...");
            self.stop_ga_event.set()
        else:
            self.log_message("GA not running.")

    def _update_ga_progress(self, percentage, message, generation_num=None, best_fitness=None, avg_fitness=None):
        self.root.after(0, lambda: self.ga_progress_var.set(percentage))
        self.root.after(0, lambda: self.ga_status_label_var.set(f"Status: {message}"))
        if generation_num is not None and best_fitness is not None and avg_fitness is not None:
            if not self.ga_fitness_generations or generation_num > self.ga_fitness_generations[-1]:
                self.ga_fitness_generations.append(generation_num);
                self.ga_fitness_best_values.append(best_fitness);
                self.ga_fitness_avg_values.append(avg_fitness)
            elif generation_num == self.ga_fitness_generations[-1]:
                self.ga_fitness_best_values[-1] = best_fitness;
                self.ga_fitness_avg_values[-1] = avg_fitness
            if self.ga_plot_initialized: self.root.after(0, self._draw_ga_fitness_plot)

    def _draw_ga_fitness_plot(self):
        if not self.ga_plot_initialized or not hasattr(self, 'ga_ax'): return
        self.ga_ax.clear()
        if self.ga_fitness_generations:
            self.ga_ax.plot(self.ga_fitness_generations, self.ga_fitness_best_values, marker='o', linestyle='-',
                            label='Best Fitness')
            self.ga_ax.plot(self.ga_fitness_generations, self.ga_fitness_avg_values, marker='x', linestyle='--',
                            label='Average Fitness')
            self.ga_ax.set_xlabel("Generation");
            self.ga_ax.set_ylabel("Fitness (RunDiff)")
            self.ga_ax.set_title("GA Fitness Progression");
            self.ga_ax.legend(loc='best');
            self.ga_ax.grid(True)
        else:
            self.ga_ax.set_xlabel("Generation");
            self.ga_ax.set_ylabel("Fitness (RunDiff)")
            self.ga_ax.set_title("GA Fitness Progression");
            self.ga_ax.text(0.5, 0.5, 'GA not run.', ha='center', va='center', transform=self.ga_ax.transAxes);
            self.ga_ax.grid(True)
        try:
            self.ga_fig.tight_layout()
        except Exception:
            pass  # Ignore if tight_layout fails
        self.ga_canvas.draw()

    def _display_best_ga_team(self, best_candidate: GACandidate):
        if not best_candidate or not best_candidate.team:
            self.ga_best_team_info_var.set("Best: N/A | Fitness: N/A | Pts: N/A")
            for tv in [self.ga_best_team_batting_treeview, self.ga_best_team_pitching_treeview]:
                for i in tv.get_children(): tv.delete(i)
            return
        team_obj = best_candidate.team
        self.ga_best_team_info_var.set(
            f"Best: {team_obj.name} | Fitness: {best_candidate.fitness:.0f} | Pts: {team_obj.total_points}")
        self.log_message(f"Displaying best GA team: {team_obj.name}, Fitness {best_candidate.fitness:.0f}")
        for tv in [self.ga_best_team_batting_treeview, self.ga_best_team_pitching_treeview]:
            for i in tv.get_children(): tv.delete(i)

        # Batting stats for best GA team (includes BatRuns)
        for player in team_obj.batters + team_obj.bench:
            s = player.season_stats if hasattr(player, 'season_stats') else Stats()  # These are eval stats
            s.update_hits()
            bat_runs = s.calculate_batting_runs()  # Calculate Batting Runs
            self.ga_best_team_batting_treeview.insert("", tk.END, values=(player.name, player.position,
                                                                          s.plate_appearances, s.at_bats, s.runs_scored,
                                                                          s.hits, s.doubles, s.triples, s.home_runs,
                                                                          s.rbi, s.walks, s.strikeouts,
                                                                          s.calculate_avg(), s.calculate_obp(),
                                                                          s.calculate_slg(),
                                                                          s.calculate_ops(),
                                                                          f"{bat_runs:.2f}"))  # Add BatRuns

        # Pitching stats for best GA team
        for player in team_obj.all_pitchers:
            s = player.season_stats if hasattr(player, 'season_stats') else Stats()
            era, whip = s.calculate_era(), s.calculate_whip()
            self.ga_best_team_pitching_treeview.insert("", tk.END,
                                                       values=(player.name, player.team_role or player.position,
                                                               s.get_formatted_ip(),
                                                               f"{era:.2f}" if era != float('inf') else "INF",
                                                               f"{whip:.2f}" if whip != float('inf') else "INF",
                                                               s.batters_faced, s.strikeouts_thrown, s.walks_allowed,
                                                               s.hits_allowed, s.runs_allowed,
                                                               s.earned_runs_allowed, s.home_runs_allowed))
        self.log_message(f"Displayed stats for best GA team: {team_obj.name}", internal=True)


if __name__ == "__main__":
    if not os.path.exists(TEAMS_DIR):
        try:
            os.makedirs(TEAMS_DIR)
        except OSError as e:
            print(f"Error creating teams directory {TEAMS_DIR}: {e}")
    root = tk.Tk()
    app = BaseballApp(root)
    root.mainloop()