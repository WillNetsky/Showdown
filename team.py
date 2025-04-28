# team.py
# Defines the Team class to manage players and roster.

import random
from entities import Batter, Pitcher # Import Batter and Pitcher classes

class Team:
    def __init__(self, name, starters, starting_pitchers, relievers, closers, bench):
        """
        Initializes a Team object.

        Args:
            name (str): The name of the team.
            starters (list): A list of 9 Batter objects for the starting lineup.
            starting_pitchers (list): A list of 4 Pitcher objects for starting rotation.
            relievers (list): A list of Pitcher objects for the bullpen (RP).
            closers (list): A list of Pitcher objects for the bullpen (CL).
            bench (list): A list of 1 Batter object for the bench.
        """
        self.name = name
        self.starters = starters # 9 batters
        self.starting_pitchers = starting_pitchers # 4 SPs
        self.relievers = relievers # RPs
        self.closers = closers # CLs
        self.bench = bench # 1 bench batter

        # Combine all pitchers for easier access (used for stats, etc.)
        self.all_pitchers = starting_pitchers + relievers + closers

        # Combine all batters for easier access (used for stats, etc.)
        self.batters = starters + bench

        self.current_pitcher = None # The pitcher currently on the mound
        self.used_starters = [] # Keep track of starting pitchers used in the game
        self.used_relievers = [] # Keep track of relievers used in the game
        self.used_closers = [] # Keep track of closers used in the game

        self.current_batter_index = 0 # Index for the batting order

        self.total_points = self.calculate_total_points()

        # Set the first starting pitcher when the team is created
        if self.starting_pitchers:
            self.current_pitcher = self.starting_pitchers[0]
            self.used_starters.append(self.current_pitcher) # Mark the first starter as used

    def calculate_total_points(self):
        """
        Calculates the total points of all players on the team.

        Returns:
            int: The total points of the team.
        """
        total_points = 0
        for player in self.batters + self.all_pitchers:
            total_points += player.pts
        return total_points

    def get_next_batter(self):
        """
        Gets the next batter in the lineup. Cycles through the starting lineup.

        Returns:
            Batter: The next Batter object.
        """
        batter = self.starters[self.current_batter_index]
        self.current_batter_index = (self.current_batter_index + 1) % len(self.starters)
        return batter

    def get_available_starter(self):
        """
        Gets the next available starting pitcher who hasn't reached their IP limit.

        Returns:
            Pitcher or None: The next available starting pitcher, or None if none are available.
        """
        for sp in self.starting_pitchers:
            if sp not in self.used_starters and (sp.ip_limit is None or sp.innings_pitched < sp.ip_limit):
                self.used_starters.append(sp)
                return sp
        return None # No available starters

    def get_available_reliever(self):
        """
        Gets the next available reliever who hasn't reached their IP limit.

        Returns:
            Pitcher or None: The next available reliever, or None if none are available.
        """
        for rp in self.relievers:
            if rp not in self.used_relievers and (rp.ip_limit is None or rp.innings_pitched < rp.ip_limit):
                self.used_relievers.append(rp)
                return rp
        return None # No available relievers

    def get_available_closer(self):
        """
        Gets the next available closer who hasn't reached their IP limit.

        Returns:
            Pitcher or None: The next available closer, or None if none are available.
        """
        for cl in self.closers:
            if cl not in self.used_closers and (cl.ip_limit is None or cl.innings_pitched < cl.ip_limit):
                self.used_closers.append(cl)
                return cl
        return None # No available closers

    def get_available_reliever_or_closer_pool(self):
        """
        Gets a combined list of available relievers and closers who haven't reached their IP limit.

        Returns:
            list: A list of available Reliever and Closer objects.
        """
        available_pool = []
        # Add available relievers
        for rp in self.relievers:
            if rp not in self.used_relievers and (rp.ip_limit is None or rp.innings_pitched < rp.ip_limit):
                available_pool.append(rp)
        # Add available closers
        for cl in self.closers:
             if cl not in self.used_closers and (cl.ip_limit is None or cl.innings_pitched < cl.ip_limit):
                  available_pool.append(cl)

        return available_pool

    def __str__(self):
        """
        Returns a string representation of the team.
        """
        starter_names = ", ".join([p.name for p in self.starters])
        bench_names = ", ".join([p.name for p in self.bench])
        sp_names = ", ".join([p.name for p in self.starting_pitchers])
        rp_names = ", ".join([p.name for p in self.relievers])
        cl_names = ", ".join([p.name for p in self.closers])

        return (f"Team Name: {self.name}\n"
                f"Total Points: {self.total_points}\n"
                f"Starters ({len(self.starters)}): {starter_names}\n"
                f"Bench ({len(self.bench)}): {bench_names}\n"
                f"Starting Pitchers ({len(self.starting_pitchers)}): {sp_names}\n"
                f"Relievers ({len(self.relievers)}): {rp_names}\n"
                f"Closers ({len(self.closers)}): {cl_names}\n"
                f"Current Pitcher: {self.current_pitcher.name if self.current_pitcher else 'None'}")

