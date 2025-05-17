# gui/ga_optimizer_tab.py
import tkinter as tk
from tkinter import ttk, messagebox  # Ensure messagebox is imported if _handle_select_benchmark_teams uses it.
import os
import re

# Matplotlib imports
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Dialog import
try:
    from .dialogs import TeamSelectionDialog
except ImportError:  # Fallback for direct execution or different structure
    from dialogs import TeamSelectionDialog

# System path modification for project modules
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from stats import Stats, DEFAULT_FIP_CONSTANT  # Import a default FIP constant
    from entities import Batter, Pitcher, Team
    from optimizer_ga import GACandidate  # Import GACandidate for type hinting
except ImportError:
    print(
        "ERROR in ga_optimizer_tab.py: Could not import Stats, Entities, GACandidate, or DEFAULT_FIP_CONSTANT. Check paths.")
    DEFAULT_FIP_CONSTANT = 3.15  # Fallback


    class Stats:
        def calculate_batting_runs(self): return 0.0

        def update_hits(self): pass

        def calculate_avg(self): return ".000";

        def calculate_obp(self): return ".000"

        def calculate_slg(self): return ".000";

        def calculate_ops(self): return ".000"

        def get_innings_pitched(self): return 0.0;

        def get_formatted_ip(self): return "0.0"

        def calculate_era(self): return float('inf');

        def calculate_whip(self): return float('inf')

        def calculate_k_per_9(self): return 0.0

        def calculate_fip(self, fip_constant=3.15, include_hbp=False): return float('inf')

        def calculate_pitching_runs_saved_era_based(self, league_avg_era_per_9): return 0.0

        def calculate_pitching_runs_saved_fip_based(self, league_avg_era_per_9, fip_constant=3.15,
                                                    include_hbp_in_fip=False): return 0.0

        def __init__(self):
            attrs = ['plate_appearances', 'at_bats', 'runs_scored', 'hits', 'doubles', 'triples', 'home_runs', 'rbi',
                     'walks', 'strikeouts', 'outs', 'singles', 'batters_faced', 'strikeouts_thrown', 'walks_allowed',
                     'hits_allowed', 'runs_allowed', 'earned_runs_allowed', 'home_runs_allowed', 'outs_recorded',
                     'hbp_allowed']
            for attr in attrs: setattr(self, attr, 0)


    class Batter:
        pass

    class Pitcher:
        pass


    class Team:
        pass

    class GACandidate:
        pass

# Placeholder for league average ERA for GA display context.
# For GA, you might use a fixed target average or average of benchmarks.
DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER_GA = 4.30


class GAOptimizerTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        super().__init__(parent_notebook)
        self.app_controller = app_controller

        # GA Parameters (Tkinter variables specific to this tab)
        self.pop_size_var = tk.IntVar(value=20)
        self.num_generations_var = tk.IntVar(value=20)
        self.mutation_rate_var = tk.DoubleVar(value=0.8)
        self.mutation_swaps_var = tk.IntVar(value=1)
        self.elitism_count_var = tk.IntVar(value=2)

        # num_benchmark_teams_var is in app_controller, GAOptimizerTab reads it
        # self.num_benchmark_teams_display_var = tk.IntVar(value=self.app_controller.ga_num_benchmark_teams_var.get()) # To reflect controller's var
        # self.app_controller.ga_num_benchmark_teams_var.trace_add("write", self._sync_num_benchmark_teams_display) # Sync if var changes

        self.games_vs_each_benchmark_var = tk.IntVar(value=100)
        self.immigration_rate_var = tk.DoubleVar(value=0.1)

        self.selected_benchmark_filepaths = []
        self.selected_benchmarks_label_var = tk.StringVar()
        self._update_selected_benchmarks_label_display()  # Initialize

        # Fitness Plot Data
        self.fitness_generations = []
        self.fitness_best_values = []
        self.fitness_avg_values = []
        self.plot_initialized = False

        # Best GA Team Display
        self.best_team_info_var = tk.StringVar(value="Best: N/A | Fitness: N/A | Pts: N/A")

        # Column definitions for the GA tab's best team display
        self.cols_roster_batting_ga = ("Name", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG",
                                       "OBP", "SLG", "OPS", "BatRuns")
        self.cols_roster_pitching_ga = ("Name", "Role", "IP", "ERA", "WHIP", "FIP", "K/9", "BB/9", "HR/9", "RSAA",
                                        "FIP-RS", "BF", "K", "BB", "H", "R", "ER", "HR")  # ADDED new stats

        self._setup_widgets()

    def _sync_num_benchmark_teams_display(self, *args):  # Called when app_controller.ga_num_benchmark_teams_var changes
        self._update_selected_benchmarks_label_display()

    def _setup_widgets(self):
        params_and_benchmark_select_outer_frame = ttk.Frame(self)
        params_and_benchmark_select_outer_frame.pack(padx=10, pady=10, fill="x", anchor="n")

        params_frame = ttk.LabelFrame(params_and_benchmark_select_outer_frame, text="GA Parameters")
        params_frame.pack(side=tk.LEFT, fill="y", expand=False, padx=(0, 10), anchor='nw')

        benchmark_select_frame_container = ttk.Frame(params_and_benchmark_select_outer_frame)
        benchmark_select_frame_container.pack(side=tk.LEFT, fill="x", expand=True, anchor='ne')

        benchmark_select_frame = ttk.LabelFrame(benchmark_select_frame_container, text="Benchmark Teams Setup")
        benchmark_select_frame.pack(pady=0, fill="x")

        self.select_benchmarks_button = ttk.Button(benchmark_select_frame, text="Select Custom Benchmark Teams",
                                                   command=self._handle_select_benchmark_teams)
        self.select_benchmarks_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.selected_benchmarks_display_label = ttk.Label(benchmark_select_frame,
                                                           textvariable=self.selected_benchmarks_label_var)
        self.selected_benchmarks_display_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(benchmark_select_frame, text=(
            "If fewer custom benchmarks are selected than 'Num Benchmark Teams',\n"
            "remaining slots will be filled by new random teams."),
                  wraplength=350, justify=tk.LEFT).grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        param_labels_with_ranges = [
            ("Population Size:", "(1-500)"),
            ("Num Generations:", "(1-2000)"),
            ("Mutation Rate:", "(0.0-1.0)"),
            ("Mutation Swaps:", "(1-10)"),
            ("Elitism Count:", "(0 to PopSize-1)"),
            ("Num Benchmark Teams (Total):", "(0-20)"),  # This entry uses app_controller's var
            ("Games vs Each Benchmark:", "(1-1000)"),
            ("Immigration Rate:", "(0.0-0.5)")
        ]

        param_vars = [self.pop_size_var, self.num_generations_var, self.mutation_rate_var,
                      self.mutation_swaps_var, self.elitism_count_var,
                      self.app_controller.ga_num_benchmark_teams_var,  # Read/write app_controller's var
                      self.games_vs_each_benchmark_var, self.immigration_rate_var]

        for i, ((label_text, range_text), var) in enumerate(zip(param_labels_with_ranges, param_vars)):
            full_label_text = f"{label_text} {range_text}"
            ttk.Label(params_frame, text=full_label_text).grid(row=i, column=0, padx=5, pady=3, sticky="w")
            ttk.Entry(params_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=3, sticky="ew")

        # GA Controls (Start/Stop)
        ga_control_frame = ttk.Frame(self)
        ga_control_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        self.start_ga_button = ttk.Button(ga_control_frame, text="Start GA Search",
                                          command=self._handle_start_ga_search)
        self.start_ga_button.pack(side=tk.LEFT, padx=5)
        self.stop_ga_button = ttk.Button(ga_control_frame, text="Stop GA Search", command=self._handle_stop_ga_search,
                                         state=tk.DISABLED)
        self.stop_ga_button.pack(side=tk.LEFT, padx=5)

        # Progress Bar and Status Label
        progress_frame = ttk.LabelFrame(self, text="GA Progress")
        progress_frame.pack(padx=10, pady=5, fill="x", anchor="n")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progressbar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progressbar.pack(fill="x", padx=5, pady=5, expand=True)
        self.status_label_var = tk.StringVar(value="Status: Idle")
        ttk.Label(progress_frame, textvariable=self.status_label_var).pack(fill="x", padx=5, pady=2)

        # Best team display area (Plot on left, Details on right)
        best_team_frame_outer = ttk.Frame(self)
        best_team_frame_outer.pack(padx=10, pady=10, fill="both", expand=True)

        plot_frame = ttk.LabelFrame(best_team_frame_outer, text="GA Fitness Over Generations")
        plot_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 5))
        self.fig = Figure(figsize=(6, 3.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        try:
            self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
            self.toolbar.update()
            self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        except Exception as e:
            if hasattr(self.app_controller, 'log_message'):
                self.app_controller.log_message(f"Matplotlib toolbar error: {e}", internal=True)
            else:
                print(f"Matplotlib toolbar error: {e}")  # Fallback
        self.plot_initialized = True
        self.draw_fitness_plot()  # Initial empty plot

        best_team_details_frame = ttk.LabelFrame(best_team_frame_outer, text="Best Team Found by GA")
        best_team_details_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=(5, 0))
        ttk.Label(best_team_details_frame, textvariable=self.best_team_info_var).pack(pady=5, fill="x", padx=5)

        best_team_stats_pane = ttk.PanedWindow(best_team_details_frame, orient=tk.VERTICAL)
        best_team_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ga_batting_frame = ttk.LabelFrame(best_team_stats_pane, text="Best Team - Batting (Eval Stats)")
        best_team_stats_pane.add(ga_batting_frame, weight=1)
        self.best_team_batting_treeview = ttk.Treeview(ga_batting_frame, columns=self.cols_roster_batting_ga,
                                                       show='headings', height=6)
        for col in self.cols_roster_batting_ga:
            width = 110 if col == "Name" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    60 if col != "BatRuns" else 65))
            anchor = tk.W if col == "Name" else tk.CENTER
            self.best_team_batting_treeview.heading(col, text=col,
                                                    command=lambda c=col: self.app_controller._treeview_sort_column(
                                                        self.best_team_batting_treeview, c, False))
            self.best_team_batting_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        bt_scrollbar_y = ttk.Scrollbar(ga_batting_frame, orient="vertical",
                                       command=self.best_team_batting_treeview.yview)
        bt_scrollbar_x = ttk.Scrollbar(ga_batting_frame, orient="horizontal",
                                       command=self.best_team_batting_treeview.xview)
        self.best_team_batting_treeview.configure(yscrollcommand=bt_scrollbar_y.set, xscrollcommand=bt_scrollbar_x.set)
        bt_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        bt_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.best_team_batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        ga_pitching_frame = ttk.LabelFrame(best_team_stats_pane, text="Best Team - Pitching (Eval Stats)")
        best_team_stats_pane.add(ga_pitching_frame, weight=1)
        self.best_team_pitching_treeview = ttk.Treeview(ga_pitching_frame, columns=self.cols_roster_pitching_ga,
                                                        show='headings', height=5)
        for col in self.cols_roster_pitching_ga:
            w = 100 if col == "Name" else \
                (40 if col == "Role" else \
                     (35 if col == "IP" else \
                          (45 if col in ["ERA", "WHIP", "FIP", "RSAA", "FIP-RS"] else \
                               (40 if col in ["K/9", "BB/9", "HR/9", "BF", "K", "BB", "H", "R", "ER", "HR"] else 50))))
            anchor = tk.W if col == "Name" else tk.CENTER
            self.best_team_pitching_treeview.heading(col, text=col,
                                                     command=lambda c=col: self.app_controller._treeview_sort_column(
                                                         self.best_team_pitching_treeview, c, False))
            self.best_team_pitching_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)
        pt_scrollbar_y = ttk.Scrollbar(ga_pitching_frame, orient="vertical",
                                       command=self.best_team_pitching_treeview.yview)
        pt_scrollbar_x = ttk.Scrollbar(ga_pitching_frame, orient="horizontal",
                                       command=self.best_team_pitching_treeview.xview)
        self.best_team_pitching_treeview.configure(yscrollcommand=pt_scrollbar_y.set, xscrollcommand=pt_scrollbar_x.set)
        pt_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        pt_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.best_team_pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def _update_selected_benchmarks_label_display(self, *args):
        try:
            num_selected = len(self.selected_benchmark_filepaths)
            num_desired = self.app_controller.ga_num_benchmark_teams_var.get()
            self.selected_benchmarks_label_var.set(f"Custom Benchmarks Selected: {num_selected} / {num_desired}")
        except tk.TclError:
            pass
        except Exception as e:
            if hasattr(self.app_controller, 'log_message'):
                self.app_controller.log_message(f"Error updating benchmark label: {e}", internal=True)

    def _handle_select_benchmark_teams(self):
        if not self.app_controller.all_players_data:
            messagebox.showerror("Error", "Player data not loaded.", parent=self.app_controller.root)
            return
        try:
            num_benchmarks_max = self.app_controller.ga_num_benchmark_teams_var.get()
        except tk.TclError:
            messagebox.showerror("Invalid Input", "'Num Benchmark Teams' must be a number.",
                                 parent=self.app_controller.root)
            return

        if num_benchmarks_max <= 0:
            messagebox.showinfo("Info",
                                "Num Benchmark Teams is <= 0. All benchmarks will be random if 'Num Benchmark Teams' > 0.",
                                parent=self.app_controller.root)
            self.selected_benchmark_filepaths = []
            self._update_selected_benchmarks_label_display()
            return

        dialog = TeamSelectionDialog(self.app_controller.root,
                                     teams_needed_or_allowed=num_benchmarks_max,
                                     dialog_title=f"Select up to {num_benchmarks_max} Custom Benchmarks")

        if dialog.selected_team_filepaths is not None:
            self.selected_benchmark_filepaths = dialog.selected_team_filepaths
            if hasattr(self.app_controller, 'log_message'):
                self.app_controller.log_message(
                    f"Selected {len(self.selected_benchmark_filepaths)} custom benchmark teams.")
        else:
            if hasattr(self.app_controller, 'log_message'):
                self.app_controller.log_message("Benchmark selection cancelled.")
        self._update_selected_benchmarks_label_display()

    def _handle_start_ga_search(self):
        if not self.app_controller.all_players_data:
            messagebox.showerror("Error", "Player data not loaded.", parent=self.app_controller.root)
            return
        if self.app_controller.ga_optimizer_thread and self.app_controller.ga_optimizer_thread.is_alive():
            messagebox.showwarning("In Progress", "GA search already running.", parent=self.app_controller.root)
            return
        try:
            ga_params = {
                "population_size": self.pop_size_var.get(),
                "num_generations": self.num_generations_var.get(),
                "mutation_rate": self.mutation_rate_var.get(),
                "num_mutation_swaps": self.mutation_swaps_var.get(),
                "elitism_count": self.elitism_count_var.get(),
                "num_benchmark_teams": self.app_controller.ga_num_benchmark_teams_var.get(),
                "games_vs_each_benchmark": self.games_vs_each_benchmark_var.get(),
                "immigration_rate": self.immigration_rate_var.get()
            }
            if not (0 < ga_params["population_size"] <= 500 and \
                    0 < ga_params["num_generations"] <= 2000 and \
                    0.0 <= ga_params["mutation_rate"] <= 1.0 and \
                    0 < ga_params["num_mutation_swaps"] <= 10 and \
                    0 <= ga_params["elitism_count"] < ga_params["population_size"] and \
                    0 <= ga_params["num_benchmark_teams"] <= 20 and \
                    0 < ga_params["games_vs_each_benchmark"] <= 1000 and \
                    0.0 <= ga_params["immigration_rate"] <= 0.5):
                messagebox.showerror("Invalid GA Parameters", "Check parameter ranges.",
                                     parent=self.app_controller.root)
                return
        except tk.TclError:
            messagebox.showerror("Invalid Input", "GA parameters must be numbers.", parent=self.app_controller.root)
            return

        # Pass a copy of the selected filepaths to the app controller
        self.app_controller.start_ga_optimizer_process(ga_params, list(self.selected_benchmark_filepaths))

    def _handle_stop_ga_search(self):
        self.app_controller.stop_ga_search()

    def update_progress_display(self, percentage, message):
        self.progress_var.set(percentage)
        self.status_label_var.set(f"Status: {message}")

    def update_plot_data(self, generation_num, best_fitness, avg_fitness):
        if not self.fitness_generations or generation_num > self.fitness_generations[-1]:
            self.fitness_generations.append(generation_num)
            self.fitness_best_values.append(best_fitness)
            self.fitness_avg_values.append(avg_fitness)
        elif generation_num == self.fitness_generations[-1]:
            self.fitness_best_values[-1] = best_fitness
            self.fitness_avg_values[-1] = avg_fitness

        if self.plot_initialized:
            # Ensure plot drawing happens in main thread, app_controller handles root.after
            self.app_controller.root.after(0, self.draw_fitness_plot)

    def draw_fitness_plot(self):
        if not self.plot_initialized or not hasattr(self, 'ax'): return
        self.ax.clear()
        if self.fitness_generations:
            self.ax.plot(self.fitness_generations, self.fitness_best_values, marker='o', linestyle='-',
                         label='Best Fitness')
            self.ax.plot(self.fitness_generations, self.fitness_avg_values, marker='x', linestyle='--',
                         label='Average Fitness')
            self.ax.set_xlabel("Generation");
            self.ax.set_ylabel("Fitness (RunDiff)")
            self.ax.set_title("GA Fitness Progression");
            self.ax.legend(loc='best');
            self.ax.grid(True)
        else:
            self.ax.set_xlabel("Generation");
            self.ax.set_ylabel("Fitness (RunDiff)")
            self.ax.set_title("GA Fitness Progression");
            self.ax.text(0.5, 0.5, 'GA not run.', ha='center', va='center', transform=self.ax.transAxes);
            self.ax.grid(True)
        try:
            self.fig.tight_layout()
        except Exception:
            pass
        self.canvas.draw()

    def display_best_ga_team(self, best_candidate: GACandidate):
        if not best_candidate or not best_candidate.team:
            self.best_team_info_var.set("Best: N/A | Fitness: N/A | Pts: N/A")
            for tv in [self.best_team_batting_treeview, self.best_team_pitching_treeview]:
                for i in tv.get_children(): tv.delete(i)
            return

        team_obj = best_candidate.team
        self.best_team_info_var.set(
            f"Best: {team_obj.name} | Fitness: {best_candidate.fitness:.0f} | Pts: {team_obj.total_points}")

        for i in self.best_team_batting_treeview.get_children(): self.best_team_batting_treeview.delete(i)
        for player in team_obj.batters + team_obj.bench:
            s = player.season_stats if hasattr(player, 'season_stats') and player.season_stats else Stats()
            s.update_hits();
            bat_runs = s.calculate_batting_runs()
            self.best_team_batting_treeview.insert("", tk.END, values=(player.name, player.position,
                                                                       s.plate_appearances, s.at_bats, s.runs_scored,
                                                                       s.hits, s.doubles, s.triples, s.home_runs,
                                                                       s.rbi, s.walks, s.strikeouts, s.calculate_avg(),
                                                                       s.calculate_obp(), s.calculate_slg(),
                                                                       s.calculate_ops(), f"{bat_runs:.2f}"))

        for i in self.best_team_pitching_treeview.get_children(): self.best_team_pitching_treeview.delete(i)
        for player in team_obj.all_pitchers:
            s = player.season_stats if hasattr(player, 'season_stats') and player.season_stats else Stats()
            era, whip = s.calculate_era(), s.calculate_whip()
            fip = s.calculate_fip(fip_constant=DEFAULT_FIP_CONSTANT, include_hbp=(hasattr(s, 'hbp_allowed')))
            k_per_9 = s.calculate_k_per_9()
            bb_per_9 = (s.walks_allowed * 9) / s.get_innings_pitched() if s.get_innings_pitched() > 0 else 0.0
            hr_per_9 = (s.home_runs_allowed * 9) / s.get_innings_pitched() if s.get_innings_pitched() > 0 else 0.0
            rsaa = s.calculate_pitching_runs_saved_era_based(DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER_GA)
            fip_rs = s.calculate_pitching_runs_saved_fip_based(DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER_GA,
                                                               fip_constant=DEFAULT_FIP_CONSTANT,
                                                               include_hbp_in_fip=(hasattr(s, 'hbp_allowed')))

            self.best_team_pitching_treeview.insert("", tk.END, values=(
                player.name, player.team_role or player.position,
                s.get_formatted_ip(),
                f"{era:.2f}" if era != float('inf') else "INF",
                f"{whip:.2f}" if whip != float('inf') else "INF",
                f"{fip:.2f}" if fip != float('inf') else "INF",
                f"{k_per_9:.2f}", f"{bb_per_9:.2f}", f"{hr_per_9:.2f}",
                f"{rsaa:.2f}", f"{fip_rs:.2f}",
                s.batters_faced, s.strikeouts_thrown, s.walks_allowed, s.hits_allowed,
                s.runs_allowed, s.earned_runs_allowed, s.home_runs_allowed
            ))
        if hasattr(self.app_controller, 'log_message'):
            self.app_controller.log_message(f"Displayed stats for best GA team: {team_obj.name}", internal=True)

    def reset_ui(self):
        self.best_team_info_var.set("Best: N/A | Fitness: N/A | Pts: N/A")
        self.progress_var.set(0.0);
        self.status_label_var.set("Status: Idle")
        self.selected_benchmark_filepaths.clear();
        self._update_selected_benchmarks_label_display()
        self.fitness_generations.clear();
        self.fitness_best_values.clear();
        self.fitness_avg_values.clear()
        if self.plot_initialized: self.draw_fitness_plot()
        for tv in [self.best_team_batting_treeview, self.best_team_pitching_treeview]:
            for i in tv.get_children(): tv.delete(i)