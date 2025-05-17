# gui/team_roster_tab.py
import tkinter as tk
from tkinter import ttk

# For type hinting and accessing Stats methods
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from stats import Stats, DEFAULT_FIP_CONSTANT  # Import a default FIP constant
    from entities import Batter, Pitcher, Team  # For type hinting
except ImportError:
    print(
        "ERROR in team_roster_tab.py: Could not import Stats, DEFAULT_FIP_CONSTANT, Batter, Pitcher, Team. Check paths.")
    # Define dummy classes and constants if needed for the script to be parsable,
    # but it won't run correctly without the actual modules.
    DEFAULT_FIP_CONSTANT = 3.15  # Fallback if not imported


    class Stats:
        def calculate_batting_runs(self): return 0.0

        def update_hits(self): pass

        def calculate_avg(self): return ".000"

        def calculate_obp(self): return ".000"

        def calculate_slg(self): return ".000"

        def calculate_ops(self): return ".000"

        def get_innings_pitched(self): return 0.0

        def get_formatted_ip(self): return "0.0"

        def calculate_era(self): return float('inf')

        def calculate_whip(self): return float('inf')

        def calculate_k_per_9(self): return 0.0

        def calculate_fip(self, fip_constant=3.15, include_hbp=False): return float('inf')

        def calculate_pitching_runs_saved_era_based(self, league_avg_era_per_9): return 0.0

        def calculate_pitching_runs_saved_fip_based(self, league_avg_era_per_9, fip_constant=3.15,
                                                    include_hbp_in_fip=False): return 0.0

        def __init__(self):
            self.plate_appearances = 0;
            self.at_bats = 0;
            self.runs_scored = 0;
            self.hits = 0
            self.doubles = 0;
            self.triples = 0;
            self.home_runs = 0;
            self.rbi = 0
            self.walks = 0;
            self.strikeouts = 0;
            self.outs = 0;
            self.singles = 0
            self.batters_faced = 0;
            self.strikeouts_thrown = 0;
            self.walks_allowed = 0
            self.hits_allowed = 0;
            self.runs_allowed = 0;
            self.earned_runs_allowed = 0
            self.home_runs_allowed = 0;
            self.outs_recorded = 0;
            self.hbp_allowed = 0


    class Batter:
        pass


    class Pitcher:
        pass


    class Team:
        pass

# Placeholder for league average ERA for this tab's context.
DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER_ROSTER = 4.30


class TeamRosterTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        super().__init__(parent_notebook)
        self.app_controller = app_controller

        self.selected_team_var = tk.StringVar()

        # Updated Column definitions
        self.cols_batting = ("Name", "Year", "Set", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO",
                             "AVG", "OBP", "SLG", "OPS", "BatRuns")
        self.cols_pitching = ("Name", "Year", "Set", "Role", "IP", "ERA", "WHIP", "FIP", "K/9", "BB/9", "HR/9", "RSAA",
                              "FIP-RS", "BF", "K", "BB", "H", "R", "ER", "HR")

        self._setup_widgets()

    def _setup_widgets(self):
        roster_selector_frame = ttk.Frame(self)
        roster_selector_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(roster_selector_frame, text="Select Team:").pack(side=tk.LEFT, padx=(0, 5))
        self.team_combobox = ttk.Combobox(roster_selector_frame, textvariable=self.selected_team_var,
                                          state="readonly", width=40)
        self.team_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.team_combobox.bind("<<ComboboxSelected>>", self._on_team_selected_from_combobox)

        roster_stats_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        roster_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        roster_batting_frame = ttk.LabelFrame(roster_stats_pane, text="Batting Stats (Season)")
        roster_stats_pane.add(roster_batting_frame, weight=1)
        self.batting_treeview = ttk.Treeview(roster_batting_frame, columns=self.cols_batting, show='headings', height=8)
        for col in self.cols_batting:
            w = 110 if col == "Name" else \
                (45 if col == "Year" else \
                     (60 if col == "Set" else \
                          (35 if col == "Pos" else \
                               (40 if col in ["PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else \
                                    (60 if col not in ["BatRuns"] else 65)))))  # Adjusted for Year/Set
            anchor = tk.W if col == "Name" or col == "Set" else tk.CENTER  # Left align Set
            self.batting_treeview.heading(col, text=col,
                                          command=lambda c=col: self.app_controller._treeview_sort_column(
                                              self.batting_treeview, c, False))
            self.batting_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        bat_scrollbar_y = ttk.Scrollbar(roster_batting_frame, orient="vertical", command=self.batting_treeview.yview)
        bat_scrollbar_x = ttk.Scrollbar(roster_batting_frame, orient="horizontal", command=self.batting_treeview.xview)
        self.batting_treeview.configure(yscrollcommand=bat_scrollbar_y.set, xscrollcommand=bat_scrollbar_x.set)
        bat_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        bat_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        roster_pitching_frame = ttk.LabelFrame(roster_stats_pane, text="Pitching Stats (Season)")
        roster_stats_pane.add(roster_pitching_frame, weight=1)
        self.pitching_treeview = ttk.Treeview(roster_pitching_frame, columns=self.cols_pitching, show='headings',
                                              height=6)
        for col in self.cols_pitching:
            w = 100 if col == "Name" else \
                (45 if col == "Year" else \
                     (60 if col == "Set" else \
                          (40 if col == "Role" else \
                               (35 if col == "IP" else \
                                    (45 if col in ["ERA", "WHIP", "FIP", "RSAA", "FIP-RS"] else \
                                         (40 if col in ["K/9", "BB/9", "HR/9", "BF", "K", "BB", "H", "R", "ER",
                                                        "HR"] else 50))))))
            anchor = tk.W if col == "Name" or col == "Set" else tk.CENTER  # Left align Set
            self.pitching_treeview.heading(col, text=col,
                                           command=lambda c=col: self.app_controller._treeview_sort_column(
                                               self.pitching_treeview, c, False))
            self.pitching_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        pitch_scrollbar_y = ttk.Scrollbar(roster_pitching_frame, orient="vertical",
                                          command=self.pitching_treeview.yview)
        pitch_scrollbar_x = ttk.Scrollbar(roster_pitching_frame, orient="horizontal",
                                          command=self.pitching_treeview.xview)
        self.pitching_treeview.configure(yscrollcommand=pitch_scrollbar_y.set, xscrollcommand=pitch_scrollbar_x.set)
        pitch_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        pitch_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def update_team_selector(self):
        team_names = [team.name for team in self.app_controller.all_teams] if self.app_controller.all_teams else []
        current_selection = self.selected_team_var.get()
        self.team_combobox['values'] = team_names
        if team_names:
            if current_selection in team_names:
                self.team_combobox.set(current_selection)
            else:
                self.team_combobox.set(team_names[0])
            self._on_team_selected_from_combobox(None)
        else:
            self.team_combobox.set(''); self._clear_stats_display_internal()

    def _on_team_selected_from_combobox(self, event):
        selected_team_name = self.selected_team_var.get()
        if not selected_team_name: self._clear_stats_display_internal(); return
        selected_team_obj = next((team for team in self.app_controller.all_teams if team.name == selected_team_name),
                                 None)
        if selected_team_obj:
            self._display_team_stats_internal(selected_team_obj)
        else:
            if hasattr(self.app_controller, 'log_message'): self.app_controller.log_message(
                f"TeamRosterTab: Team not found '{selected_team_name}'")
            self._clear_stats_display_internal()

    def _clear_stats_display_internal(self):
        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)

    def _display_team_stats_internal(self, team_obj: Team):
        self._clear_stats_display_internal()
        # Use placeholder league average for RSAA/FIP-RS calculations on this tab for now
        # Or, app_controller could pass its current_league_avg_era if desired for consistency
        lg_avg_era = DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER_ROSTER
        if hasattr(self.app_controller, 'get_current_league_average_era'):
            lg_avg_era = self.app_controller.get_current_league_average_era()

        for player in team_obj.batters + team_obj.bench:
            s = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                      Stats) else Stats()
            s.update_hits();
            batting_runs = s.calculate_batting_runs()
            player_year = player.year if hasattr(player, 'year') else ""
            player_set = player.set if hasattr(player, 'set') else ""
            self.batting_treeview.insert("", tk.END, values=(
                player.name, player_year, player_set, player.position,
                s.plate_appearances, s.at_bats, s.runs_scored, s.hits, s.doubles, s.triples, s.home_runs,
                s.rbi, s.walks, s.strikeouts, s.calculate_avg(), s.calculate_obp(), s.calculate_slg(),
                s.calculate_ops(), f"{batting_runs:.2f}"
            ))

        for player in team_obj.all_pitchers:
            s = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                      Stats) else Stats()
            player_year = player.year if hasattr(player, 'year') else ""
            player_set = player.set if hasattr(player, 'set') else ""

            era, whip = s.calculate_era(), s.calculate_whip()
            fip = s.calculate_fip(fip_constant=DEFAULT_FIP_CONSTANT, include_hbp=(hasattr(s, 'hbp_allowed')))
            k_per_9 = s.calculate_k_per_9()
            bb_per_9 = (s.walks_allowed * 9) / s.get_innings_pitched() if s.get_innings_pitched() > 0 else 0.0
            hr_per_9 = (s.home_runs_allowed * 9) / s.get_innings_pitched() if s.get_innings_pitched() > 0 else 0.0
            rsaa = s.calculate_pitching_runs_saved_era_based(lg_avg_era)
            fip_rs = s.calculate_pitching_runs_saved_fip_based(lg_avg_era,
                                                               fip_constant=DEFAULT_FIP_CONSTANT,
                                                               include_hbp_in_fip=(hasattr(s, 'hbp_allowed')))

            self.pitching_treeview.insert("", tk.END, values=(
                player.name, player_year, player_set, player.team_role or player.position,
                s.get_formatted_ip(),
                f"{era:.2f}" if era != float('inf') else "INF",
                f"{whip:.2f}" if whip != float('inf') else "INF",
                f"{fip:.2f}" if fip != float('inf') else "INF",
                f"{k_per_9:.2f}", f"{bb_per_9:.2f}", f"{hr_per_9:.2f}",
                f"{rsaa:.2f}", f"{fip_rs:.2f}",
                s.batters_faced, s.strikeouts_thrown, s.walks_allowed, s.hits_allowed,
                s.runs_allowed, s.earned_runs_allowed, s.home_runs_allowed
            ))

    def clear_display(self):
        self.selected_team_var.set('')
        self.team_combobox['values'] = []
        self._clear_stats_display_internal()