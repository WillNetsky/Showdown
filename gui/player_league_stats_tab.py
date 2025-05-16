# gui/player_league_stats_tab.py
import tkinter as tk
from tkinter import ttk

# For type hinting and accessing Stats methods (like calculate_batting_runs)
# Adjust path if your project structure is different.
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from stats import Stats
    from entities import Batter, Pitcher
except ImportError:
    print("ERROR in player_league_stats_tab.py: Could not import Stats, Batter, Pitcher. Check paths.")


    # Define dummy classes if needed for the script to be parsable, but it won't run correctly
    class Stats:
        def calculate_batting_runs(self): return 0.0

        def update_hits(self): pass

        def calculate_avg(self): return ".000"

        def calculate_obp(self): return ".000"

        def calculate_slg(self): return ".000"

        def calculate_ops(self): return ".000"

        def get_formatted_ip(self): return "0.0"

        def calculate_era(self): return float('inf')

        def calculate_whip(self): return float('inf')

        def __init__(self):
            self.plate_appearances = 0
            self.at_bats = 0
            self.runs_scored = 0
            self.hits = 0
            self.doubles = 0
            self.triples = 0
            self.home_runs = 0
            self.rbi = 0
            self.walks = 0
            self.strikeouts = 0
            self.batters_faced = 0
            self.strikeouts_thrown = 0
            self.walks_allowed = 0
            self.hits_allowed = 0
            self.runs_allowed = 0
            self.earned_runs_allowed = 0
            self.home_runs_allowed = 0


    class Batter:
        pass


    class Pitcher:
        pass


class PlayerLeagueStatsTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller, stats_source_attr, tab_title_prefix):
        """
        Initializes a tab for displaying league-wide player statistics (either season or career).

        Args:
            parent_notebook (ttk.Notebook): The parent notebook widget.
            app_controller (BaseballApp): The main application controller instance.
            stats_source_attr (str): The attribute name for player stats (e.g., 'season_stats', 'career_stats').
            tab_title_prefix (str): Prefix for titles within the tab (e.g., "Season", "Career").
        """
        super().__init__(parent_notebook)
        self.app_controller = app_controller
        self.stats_source_attr = stats_source_attr
        self.tab_title_prefix = tab_title_prefix

        # Define column configurations (could be shared from a constants module too)
        self.cols_batting = ("Name", "Year", "Set", "Team", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB",
                             "SO", "AVG", "OBP", "SLG", "OPS", "BatRuns")
        self.cols_pitching = ("Name", "Year", "Set", "Team", "Role", "IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R",
                              "ER", "HR")

        self._setup_widgets()

    def _setup_widgets(self):
        """Creates and lays out the widgets for this tab."""
        # Main paned window for batting and pitching sections
        stats_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Batting Stats Section ---
        batting_frame = ttk.LabelFrame(stats_pane, text=f"League Batting Stats ({self.tab_title_prefix})")
        stats_pane.add(batting_frame, weight=1)

        self.batting_treeview = ttk.Treeview(batting_frame, columns=self.cols_batting, show='headings', height=10)
        for col in self.cols_batting:
            # Determine width and anchor based on column name (similar to app_controller)
            w = 110 if col == "Name" else \
                (45 if col == "Year" else \
                     (65 if col == "Set" else \
                          (70 if col == "Team" else \
                               (35 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else \
                                    (55 if col != "BatRuns" else 60)))))  # Adjusted widths
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER

            # Use app_controller's sort method, passing this tab's treeview
            self.batting_treeview.heading(col, text=col,
                                          command=lambda c=col: self.app_controller._treeview_sort_column(
                                              self.batting_treeview, c, False))
            self.batting_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        # Add scrollbar for batting treeview
        batting_scrollbar = ttk.Scrollbar(batting_frame, orient="vertical", command=self.batting_treeview.yview)
        self.batting_treeview.configure(yscrollcommand=batting_scrollbar.set)
        batting_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Pitching Stats Section ---
        pitching_frame = ttk.LabelFrame(stats_pane, text=f"League Pitching Stats ({self.tab_title_prefix})")
        stats_pane.add(pitching_frame, weight=1)

        self.pitching_treeview = ttk.Treeview(pitching_frame, columns=self.cols_pitching, show='headings', height=10)
        for col in self.cols_pitching:
            # Determine width and anchor based on column name
            w = 120 if col == "Name" else \
                (50 if col == "Year" else \
                     (70 if col == "Set" else \
                          (80 if col == "Team" else \
                               (45 if col in ["Role", "IP", "BF", "K", "BB", "H", "R", "ER", "HR"] else 60))))
            anchor = tk.W if col in ["Name", "Team", "Set"] else tk.CENTER

            self.pitching_treeview.heading(col, text=col,
                                           command=lambda c=col: self.app_controller._treeview_sort_column(
                                               self.pitching_treeview, c, False))
            self.pitching_treeview.column(col, width=w, anchor=anchor, stretch=tk.YES)

        # Add scrollbar for pitching treeview
        pitching_scrollbar = ttk.Scrollbar(pitching_frame, orient="vertical", command=self.pitching_treeview.yview)
        self.pitching_treeview.configure(yscrollcommand=pitching_scrollbar.set)
        pitching_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def update_display(self):
        """Clears and repopulates the treeviews with current player statistics."""
        # self.app_controller.log_message(f"Updating player {self.tab_title_prefix.lower()} stats display...", internal=True) # Optional logging

        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)

        if not self.app_controller.all_teams:
            # self.app_controller.log_message(f"No teams to display {self.tab_title_prefix.lower()} stats.", internal=True) # Optional
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

            player_actual_stats = getattr(player, self.stats_source_attr, None)
            if not isinstance(player_actual_stats, Stats):
                player_actual_stats = Stats()
                # self.app_controller.log_message(f"Warning: Missing {self.stats_source_attr} for {player.name} ({team_name_for_display}). Using empty stats.", internal=True)

            player_year = player.year if hasattr(player, 'year') and player.year else ""
            player_set = player.set if hasattr(player, 'set') and player.set else ""

            if isinstance(player, Batter):
                player_actual_stats.update_hits()
                batting_runs = player_actual_stats.calculate_batting_runs()

                batting_values = (
                    player.name, player_year, player_set, team_name_for_display, player.position,
                    player_actual_stats.plate_appearances, player_actual_stats.at_bats,
                    player_actual_stats.runs_scored, player_actual_stats.hits,
                    player_actual_stats.doubles, player_actual_stats.triples,
                    player_actual_stats.home_runs, player_actual_stats.rbi,
                    player_actual_stats.walks, player_actual_stats.strikeouts,
                    player_actual_stats.calculate_avg(), player_actual_stats.calculate_obp(),
                    player_actual_stats.calculate_slg(), player_actual_stats.calculate_ops(),
                    f"{batting_runs:.2f}"
                )
                batting_entries.append(batting_values)
            elif isinstance(player, Pitcher):
                era_val = player_actual_stats.calculate_era()
                whip_val = player_actual_stats.calculate_whip()
                pitching_values = (
                    player.name, player_year, player_set, team_name_for_display, player.team_role or player.position,
                    player_actual_stats.get_formatted_ip(),
                    f"{era_val:.2f}" if era_val != float('inf') else "INF",
                    f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                    player_actual_stats.batters_faced, player_actual_stats.strikeouts_thrown,
                    player_actual_stats.walks_allowed, player_actual_stats.hits_allowed,
                    player_actual_stats.runs_allowed, player_actual_stats.earned_runs_allowed,
                    player_actual_stats.home_runs_allowed
                )
                pitching_entries.append(pitching_values)

        for entry in batting_entries: self.batting_treeview.insert("", tk.END, values=entry)
        for entry in pitching_entries: self.pitching_treeview.insert("", tk.END, values=entry)
        # self.app_controller.log_message(f"Player {self.tab_title_prefix.lower()} stats updated.", internal=True) # Optional

    def clear_display(self):
        """Clears all data from the treeviews in this tab."""
        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)
