# gui/team_roster_tab.py
import tkinter as tk
from tkinter import ttk

# For type hinting and accessing Stats methods
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from stats import Stats  # Assuming Stats class has calculate_batting_runs()
    from entities import Batter, Pitcher, Team  # For type hinting
except ImportError:
    print("ERROR in team_roster_tab.py: Could not import Stats, Batter, Pitcher, Team. Check paths.")


    # Dummy classes for parsing if imports fail
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
            self.batters_faced = 0;
            self.strikeouts_thrown = 0
            self.walks_allowed = 0;
            self.hits_allowed = 0;
            self.runs_allowed = 0
            self.earned_runs_allowed = 0;
            self.home_runs_allowed = 0


    class Batter:
        pass


    class Pitcher:
        pass


    class Team:
        pass


class TeamRosterTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        super().__init__(parent_notebook)
        self.app_controller = app_controller

        # Tkinter variable for the Combobox
        self.selected_team_var = tk.StringVar()

        # Column definitions
        self.cols_batting = ("Name", "Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "AVG", "OBP",
                             "SLG", "OPS", "BatRuns")
        self.cols_pitching = ("Name", "Role", "IP", "ERA", "WHIP", "BF", "K", "BB", "H", "R", "ER", "HR")

        self._setup_widgets()

    def _setup_widgets(self):
        # --- Team Selector ---
        roster_selector_frame = ttk.Frame(self)
        roster_selector_frame.pack(padx=5, pady=5, fill="x")
        ttk.Label(roster_selector_frame, text="Select Team:").pack(side=tk.LEFT, padx=(0, 5))
        self.team_combobox = ttk.Combobox(roster_selector_frame, textvariable=self.selected_team_var,
                                          state="readonly", width=40)
        self.team_combobox.pack(side=tk.LEFT, fill="x", expand=True)
        self.team_combobox.bind("<<ComboboxSelected>>", self._on_team_selected_from_combobox)

        # --- Stats Display Panes ---
        roster_stats_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        roster_stats_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # Batting Stats Treeview
        roster_batting_frame = ttk.LabelFrame(roster_stats_pane, text="Batting Stats (Season)")
        roster_stats_pane.add(roster_batting_frame, weight=1)
        self.batting_treeview = ttk.Treeview(roster_batting_frame, columns=self.cols_batting, show='headings', height=8)
        for col in self.cols_batting:
            width = 110 if col == "Name" else (
                40 if col in ["Pos", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"] else (
                    60 if col != "BatRuns" else 65))
            anchor = tk.W if col == "Name" else tk.CENTER
            self.batting_treeview.heading(col, text=col,
                                          command=lambda c=col: self.app_controller._treeview_sort_column(
                                              self.batting_treeview, c, False))
            self.batting_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)

        bat_scrollbar = ttk.Scrollbar(roster_batting_frame, orient="vertical", command=self.batting_treeview.yview)
        self.batting_treeview.configure(yscrollcommand=bat_scrollbar.set)
        bat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batting_treeview.pack(fill="both", expand=True, padx=5, pady=5)

        # Pitching Stats Treeview
        roster_pitching_frame = ttk.LabelFrame(roster_stats_pane, text="Pitching Stats (Season)")
        roster_stats_pane.add(roster_pitching_frame, weight=1)
        self.pitching_treeview = ttk.Treeview(roster_pitching_frame, columns=self.cols_pitching, show='headings',
                                              height=6)
        for col in self.cols_pitching:
            width = 120 if col == "Name" else (50 if col == "IP" else 45)
            anchor = tk.W if col == "Name" else tk.CENTER
            self.pitching_treeview.heading(col, text=col,
                                           command=lambda c=col: self.app_controller._treeview_sort_column(
                                               self.pitching_treeview, c, False))
            self.pitching_treeview.column(col, width=width, anchor=anchor, stretch=tk.YES)

        pitch_scrollbar = ttk.Scrollbar(roster_pitching_frame, orient="vertical", command=self.pitching_treeview.yview)
        self.pitching_treeview.configure(yscrollcommand=pitch_scrollbar.set)
        pitch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pitching_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def update_team_selector(self):
        """Updates the team selection combobox with current teams."""
        team_names = [team.name for team in self.app_controller.all_teams] if self.app_controller.all_teams else []
        current_selection = self.selected_team_var.get()

        self.team_combobox['values'] = team_names
        if team_names:
            if current_selection in team_names:
                self.team_combobox.set(current_selection)
            else:
                self.team_combobox.set(team_names[0])
            self._on_team_selected_from_combobox(None)  # Trigger display update for current/new selection
        else:
            self.team_combobox.set('')
            self._clear_stats_display_internal()

    def _on_team_selected_from_combobox(self, event):
        """Handles selection change in the team combobox."""
        selected_team_name = self.selected_team_var.get()
        if not selected_team_name:
            self._clear_stats_display_internal()
            return

        selected_team_obj = next((team for team in self.app_controller.all_teams if team.name == selected_team_name),
                                 None)

        if selected_team_obj:
            self._display_team_stats_internal(selected_team_obj)
        else:
            if hasattr(self.app_controller, 'log_message'):
                self.app_controller.log_message(f"TeamRosterTab: Could not find team object for '{selected_team_name}'")
            self._clear_stats_display_internal()

    def _clear_stats_display_internal(self):
        """Clears the batting and pitching treeviews."""
        for i in self.batting_treeview.get_children(): self.batting_treeview.delete(i)
        for i in self.pitching_treeview.get_children(): self.pitching_treeview.delete(i)

    def _display_team_stats_internal(self, team_obj: Team):
        """Populates the treeviews with stats for the given team."""
        self._clear_stats_display_internal()

        # Batting Stats
        batters_to_display = team_obj.batters + team_obj.bench
        for player in batters_to_display:
            player_stats = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                                 Stats) else Stats()
            player_stats.update_hits()
            batting_runs = player_stats.calculate_batting_runs()
            values = (
                player.name, player.position,
                player_stats.plate_appearances, player_stats.at_bats,
                player_stats.runs_scored, player_stats.hits,
                player_stats.doubles, player_stats.triples,
                player_stats.home_runs, player_stats.rbi,
                player_stats.walks, player_stats.strikeouts,
                player_stats.calculate_avg(), player_stats.calculate_obp(),
                player_stats.calculate_slg(), player_stats.calculate_ops(),
                f"{batting_runs:.2f}"
            )
            self.batting_treeview.insert("", tk.END, values=values)

        # Pitching Stats
        for player in team_obj.all_pitchers:
            player_stats = player.season_stats if hasattr(player, 'season_stats') and isinstance(player.season_stats,
                                                                                                 Stats) else Stats()
            era_val = player_stats.calculate_era()
            whip_val = player_stats.calculate_whip()
            values = (
                player.name, player.team_role or player.position,
                player_stats.get_formatted_ip(),
                f"{era_val:.2f}" if era_val != float('inf') else "INF",
                f"{whip_val:.2f}" if whip_val != float('inf') else "INF",
                player_stats.batters_faced, player_stats.strikeouts_thrown,
                player_stats.walks_allowed, player_stats.hits_allowed,
                player_stats.runs_allowed, player_stats.earned_runs_allowed,
                player_stats.home_runs_allowed
            )
            self.pitching_treeview.insert("", tk.END, values=values)

    def clear_display(self):
        """Public method to clear the tab's display, e.g., when resetting data."""
        self.selected_team_var.set('')
        self.team_combobox['values'] = []
        self._clear_stats_display_internal()