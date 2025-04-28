# team.py
# Defines the Team class to hold players and manage the lineup/pitching staff.

from entities import Batter, Pitcher # Import necessary classes
import random # Import random for potential future use, though not strictly needed for current get_available_pitcher logic

class Team:
    def __init__(self, name, batters, starters, relievers, closers, bench):
        """
        Initializes a Team object with specific pitcher roles and a bench.

        Args:
            name (str): The name of the team.
            batters (list): A list of Batter objects for the starting lineup (9 players).
            starters (list): A list of Pitcher objects who are starters.
            relievers (list): A list of Pitcher objects who are relievers.
            closers (list): A list of Pitcher objects who are closers.
            bench (list): A list of Batter objects for the bench.
        """
        self.name = name
        self.batters = batters # This is now explicitly the starting lineup (9 players)
        self.starters = starters
        self.relievers = relievers
        self.closers = closers
        self.bench = bench # Added bench attribute (1 player)
        # Combine all pitchers into one list for easier iteration if needed
        self.all_pitchers = starters + relievers + closers
        # Set the initial current pitcher - this will be set in play_game now
        self.current_pitcher = None

        # Keep track of which starters have been used to ensure only one starts per game
        self.used_starters = []
        # Keep track of which relievers/closers have already pitched in this game
        self.used_relievers = []
        self.used_closers = []


        self.current_batter_index = 0 # Index of the next batter in the lineup

        # Calculate total team points
        self.total_points = sum(b.pts for b in self.batters) + sum(b.pts for b in self.bench) + sum(p.pts for p in self.all_pitchers)


    def get_next_batter(self):
        """
        Gets the next batter in the lineup and updates the index.

        Returns:
            Batter: The next Batter object.
        """
        batter = self.batters[self.current_batter_index]
        self.current_batter_index = (self.current_batter_index + 1) % len(self.batters)
        return batter

    def get_available_starter(self):
        """
        Gets the first available starting pitcher who has not been used and is under their IP limit.

        Returns:
            Pitcher or None: An available Starting Pitcher, or None if none are available.
        """
        for starter in self.starters:
            # Check if the starter has not been used yet AND has not reached their IP limit
            if starter not in self.used_starters and (starter.ip_limit is None or starter.innings_pitched < starter.ip_limit):
                return starter
        return None # No available starters

    def get_available_relief_pitcher(self):
        """
        Gets the next available reliever or closer who has not been used and is under their IP limit.
        Prioritizes relievers over closers for general relief situations.

        Returns:
            Pitcher or None: An available Reliever or Closer, or None if none are available.
        """
        # Try relievers first
        for reliever in self.relievers:
            if reliever not in self.used_relievers and (reliever.ip_limit is None or reliever.innings_pitched < reliever.ip_limit):
                return reliever

        # If no relievers available, try closers
        for closer in self.closers:
             if closer not in self.used_closers and (closer.ip_limit is None or closer.innings_pitched < closer.ip_limit):
                  return closer

        return None # No available relief pitchers


    def __str__(self):
        """
        Returns a string representation of the Team object.
        """
        batter_names = [f"{b.name} ({b.position})" for b in self.batters]
        pitcher_names = [f"{p.name} ({p.position})" for p in self.all_pitchers]
        bench_names = [f"{b.name} ({b.position})" for b in self.bench]

        return (f"Team: {self.name} (Total Points: {self.total_points})\n"
                f"  Lineup: {', '.join(batter_names)}\n"
                f"  Pitchers: {', '.join(pitcher_names)}\n"
                f"  Bench: {', '.join(bench_names)}")

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Team object.
        """
        return (f"Team(name='{self.name}', batters={self.batters}, starters={self.starters}, "
                f"relievers={self.relievers}, closers={self.closers}, bench={self.bench})")

