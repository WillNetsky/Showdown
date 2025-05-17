# gui/player_league_stats_tab.py
import tkinter as tk
from tkinter import ttk

# For type hinting and accessing Stats methods
import sys
import os

# Ensure the project root directory (parent of 'gui') is in the Python path
# so that modules like 'stats' and 'entities' can be imported.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from stats import Stats, DEFAULT_FIP_CONSTANT  # Assuming DEFAULT_FIP_CONSTANT is in stats.py
    from entities import Batter, Pitcher
except ImportError:
    print(
        "ERROR in player_league_stats_tab.py: Could not import Stats, DEFAULT_FIP_CONSTANT, Batter, Pitcher. Check paths.")
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

# Placeholder for league average ERA. Ideally, this would be passed from app_controller
# or calculated dynamically based on the simulation's overall stats.
DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER = 4.30


class PlayerLeagueStatsTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller, stats_source_attr, tab_title_prefix):
        """
        Initializes a tab for displaying league-wide player statistics.

        Args:
            parent_notebook (ttk.Notebook): The parent notebook widget.
            app_controller (BaseballApp): The main application controller instance.
            stats_source_attr (str): Attribute for player stats (e.g., 'season_stats', 'career_stats').
            tab_title_prefix (str): Prefix for titles (e.g., "Season", "Career").
        """
        super().__init__(parent_notebook)
        self.app_controller = app_controller
        self.stats_source_attr = stats_source_attr
        self.tab_title_prefix = tab_title_prefix

        self.cols_batting = ("Name", "Year", "Set", "Team", "Pos", "PA", "AB", "R", "H",
                             "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP",
                             "SLG", "OPS", "BatRuns")
        self.cols_pitching = ("Name", "Year", "Set", "Team", "Role", "IP", "ERA", "WHIP",
                              "FIP", "K/9", "BB/9", "HR/9", "RSAA", "FIP-RS",
                              "BF", "K", "BB", "H", "R", "ER", "HR")

        self._setup_widgets()

    def _setup_widgets(self):
        stats_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Batting Stats Section ---
        batting_frame = ttk.LabelFrame(stats_pane, text=f"League Batting Stats ({self.tab_title_prefix})")
        stats_pane.add(batting_frame, weight=1)

        self.batting_treeview = ttk.Treeview(batting_frame, columns=self.cols_batting, show='headings', height=10)
        for col in self.cols_batting:
            w = 110 if col == "Name" else \
                (45 if col == "Year" else \
                     (65 if col == "Set" else \
                          (70 if col == "Team" else \
                               (35 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else \
                                    (55 if col != "BatRuns" else 60)))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.batting_treeview.heading(col, text=col,
                                          command=lambda c=col: self.app_controller._treeview_sort_column(
                                              self.batting_treeview, c, False))
            self.batting_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        bat_scrollbar_y = ttk.Scrollbar(batting_frame, orient="vertical", command=self.batting_treeview.yview)
        bat_scrollbar_x = ttk.Scrollbar(batting_frame, orient="horizontal", command=self.batting_treeview.xview)
        self.batting_treeview.configure(yscrollcommand=bat_scrollbar_y.set, xscrollcommand=bat_scrollbar_x.set)
        bat_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        bat_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Pitching Stats Section ---
        pitching_frame = ttk.LabelFrame(stats_pane, text=f"League Pitching Stats ({self.tab_title_prefix})")
        stats_pane.add(pitching_frame, weight=1)

        self.pitching_treeview = ttk.Treeview(pitching_frame, columns=self.cols_pitching, show='headings', height=10)
        for col in self.cols_pitching:
            w = 100 if col == "Name" else \
                (45 if col == "Year" else \
                     (60 if col == "Set" else \
                          (70 if col == "Team" else \
                               (35 if col == "Role" else \
                                    (40 if col == "IP" else \
                                         (50 if col in ["ERA", "WHIP", "FIP", "RSAA", "FIP-RS", "K/9", "BB/9",
                                                        "HR/9"] else \
                                              (40 if col in ["BF", "K", "BB", "H", "R", "ER", "HR"] else 60)))))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER
            self.pitching_treeview.heading(col, text=col,
                                           command=lambda c=col: self.app_controller._treeview_sort_column(
                                               self.pitching_treeview, c, False))
            self.pitching_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        pitch_scrollbar_y = ttk.Scrollbar(pitching_frame, orient="vertical", command=self.pitching_treeview.yview)
        pitch_scrollbar_x = ttk.Scrollbar(pitching_frame, orient="horizontal", command=self.pitching_treeview.xview)
        self.pitching_treeview.configure(yscrollcommand=pitch_scrollbar_y.set, xscrollcommand=pitch_scrollbar_x.set)
        pitch_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        pitch_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def update_display(self, league_avg_era_for_rsaa=None):
        if league_avg_era_for_rsaa is None:
            # Try to get from app_controller, or use placeholder
            if hasattr(self.app_controller, 'get_current_league_average_era'):
                league_avg_era_for_rsaa = self.app_controller.get_current_league_average_era()
            else:
                league_avg_era_for_rsaa = DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER

        # self.app_controller.log_message(f"Updating player {self.tab_title_prefix.lower()} stats display using lgERA: {league_avg_era_for_rsaa:.2f}", internal=True)

        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)

        if not self.app_controller.all_teams:
            return

        player_stats_map = {}
        for team_obj in self.app_controller.all_teams:
            for player in team_obj.batters + team_obj.bench + team_obj.all_pitchers:
                player_key = (player.name, player.year, player.set)
                if player_key not in player_stats_map:
                    player_stats_map[player_key] = {'player_obj': player, 'teams': set()}
                player_stats_map[player_key]['teams'].add(team_obj.name)

        batting_entries = []
        pitching_entries = []

        for data in player_stats_map.values():
            player = data['player_obj']
            team_name_for_display = player.team_name if hasattr(player, 'team_name') and player.team_name else (
                list(data['teams'])[0] if data['teams'] else "N/A")

            p_stats = getattr(player, self.stats_source_attr, None)  # Get the correct Stats object (season or career)
            if not isinstance(p_stats, Stats):  # Ensure it's a Stats object
                p_stats = Stats()

            player_year = player.year if hasattr(player, 'year') and player.year else ""
            player_set = player.set if hasattr(player, 'set') and player.set else ""

            if isinstance(player, Batter):
                p_stats.update_hits()
                batting_runs = p_stats.calculate_batting_runs()
                batting_values = (
                    player.name, player_year, player_set, team_name_for_display, player.position,
                    p_stats.plate_appearances, p_stats.at_bats,
                    p_stats.runs_scored, p_stats.hits,
                    p_stats.doubles, p_stats.triples,
                    p_stats.home_runs, p_stats.rbi,
                    p_stats.walks, p_stats.strikeouts,
                    p_stats.calculate_avg(), p_stats.calculate_obp(),
                    p_stats.calculate_slg(), p_stats.calculate_ops(),
                    f"{batting_runs:.2f}"
                )
                batting_entries.append(batting_values)
            elif isinstance(player, Pitcher):
                era, whip = p_stats.calculate_era(), p_stats.calculate_whip()
                # Assuming HBP is not tracked for FIP for now, so include_hbp=False
                fip = p_stats.calculate_fip(fip_constant=DEFAULT_FIP_CONSTANT, include_hbp=False)
                k_per_9 = p_stats.calculate_k_per_9()
                bb_per_9 = (
                                       p_stats.walks_allowed * 9) / p_stats.get_innings_pitched() if p_stats.get_innings_pitched() > 0 else 0.0
                hr_per_9 = (
                                       p_stats.home_runs_allowed * 9) / p_stats.get_innings_pitched() if p_stats.get_innings_pitched() > 0 else 0.0

                rsaa = p_stats.calculate_pitching_runs_saved_era_based(league_avg_era_for_rsaa)
                fip_rs = p_stats.calculate_pitching_runs_saved_fip_based(league_avg_era_for_rsaa,
                                                                         fip_constant=DEFAULT_FIP_CONSTANT,
                                                                         include_hbp_in_fip=False)

                pitching_values = (
                    player.name, player_year, player_set, team_name_for_display, player.team_role or player.position,
                    p_stats.get_formatted_ip(),
                    f"{era:.2f}" if era != float('inf') else "INF",
                    f"{whip:.2f}" if whip != float('inf') else "INF",
                    f"{fip:.2f}" if fip != float('inf') else "INF",
                    f"{k_per_9:.2f}",
                    f"{bb_per_9:.2f}",
                    f"{hr_per_9:.2f}",
                    f"{rsaa:.2f}",
                    f"{fip_rs:.2f}",
                    p_stats.batters_faced, p_stats.strikeouts_thrown,
                    p_stats.walks_allowed, p_stats.hits_allowed,
                    p_stats.runs_allowed, p_stats.earned_runs_allowed,
                    p_stats.home_runs_allowed
                )
                pitching_entries.append(pitching_values)

        for entry in batting_entries: self.batting_treeview.insert("", tk.END, values=entry)
        for entry in pitching_entries: self.pitching_treeview.insert("", tk.END, values=entry)

    def clear_display(self):
        """Clears all data from the treeviews in this tab."""
        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)