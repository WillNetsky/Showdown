# gui/standings_tab.py
import tkinter as tk
from tkinter import ttk


class StandingsTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller):
        """
        Initializes the Standings Tab.

        Args:
            parent_notebook (ttk.Notebook): The parent notebook widget.
            app_controller (BaseballApp): The main application controller instance.
        """
        super().__init__(parent_notebook)
        self.app_controller = app_controller

        # Define column configuration
        self.cols_standings = ("Team", "W", "L", "Win%", "ELO", "R", "RA", "Run Diff")

        self._setup_widgets()

    def _setup_widgets(self):
        """Creates and lays out the widgets for this tab."""
        self.standings_treeview = ttk.Treeview(self, columns=self.cols_standings, show='headings')
        for col in self.cols_standings:
            self.standings_treeview.heading(col, text=col,
                                            command=lambda c=col: self.app_controller._treeview_sort_column(
                                                self.standings_treeview, c, False))
            self.standings_treeview.column(col, width=85, anchor=tk.CENTER, stretch=tk.YES)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.standings_treeview.yview)
        self.standings_treeview.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.standings_treeview.pack(fill="both", expand=True, padx=5, pady=5)

    def update_display(self, teams_to_display):
        """Clears and repopulates the standings treeview."""
        for i in self.standings_treeview.get_children():
            self.standings_treeview.delete(i)

        if not teams_to_display:
            return

        valid_teams_to_display = []
        for team in teams_to_display:
            if hasattr(team, 'team_stats') and team.team_stats is not None:
                valid_teams_to_display.append(team)
            else:
                # Use app_controller's logger if available
                if hasattr(self.app_controller, 'log_message'):
                    self.app_controller.log_message(
                        f"Warning: Team {team.name if hasattr(team, 'name') else 'Unnamed Team'} missing team_stats. Skipping from standings.")
                else:
                    print(
                        f"Warning: Team {team.name if hasattr(team, 'name') else 'Unnamed Team'} missing team_stats (StandingsTab).")

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

    def clear_display(self):
        """Clears all data from the treeview in this tab."""
        for i in self.standings_treeview.get_children():
            self.standings_treeview.delete(i)