# team.py
# Defines the Team class to hold players and manage team state.

import random

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
        # Set the initial current pitcher - prefer SP, then RP, then CL
        self.current_pitcher = None
        if self.starters:
            self.current_pitcher = self.starters[0]
        elif self.relievers:
            self.current_pitcher = self.relievers[0]
        elif self.closers:
            self.current_pitcher = self.closers[0]


        self.current_batter_index = 0 # Index of the next batter in the lineup

        # Keep track of which relievers/closers have already pitched
        # Note: Starters are not added to used_relievers/used_closers
        self.used_starters = [] # Track used starters
        self.used_relievers = []
        self.used_closers = []

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

    def get_available_reliever_or_closer_pool(self):
        """
        Gets a combined list of available relievers and closers who haven't pitched yet.

        Returns:
            list: A list of available Pitcher objects (RP or CL).
        """
        # Filter out pitchers who have already been used (either as RP or CL)
        available_pool = [p for p in self.relievers + self.closers if p not in self.used_relievers + self.used_closers]
        return available_pool


    def __str__(self):
        """
        Returns a string representation of the Team object.
        """
        # Display team name, total points, and roster summary
        starter_names = ", ".join([f"{b.name} ({b.position})" for b in self.batters])
        bench_names = ", ".join([f"{b.name} ({b.position})" for b in self.bench])
        sp_names = ", ".join([f"{p.name} ({p.position})" for p in self.starters])
        rp_names = ", ".join([f"{p.name} ({p.position})" for p in self.relievers])
        cl_names = ", ".join([f"{p.name} ({p.position})" for p in self.closers])


        return (f"Team Name: {self.name} (Total Points: {self.total_points})\n"
                f"Starting Lineup ({len(self.batters)}): {starter_names}\n"
                f"Bench ({len(self.bench)}): {bench_names}\n"
                f"Starting Pitchers ({len(self.starters)}): {sp_names}\n"
                f"Relief Pitchers ({len(self.relievers)}): {rp_names}\n"
                f"Closers ({len(self.closers)}): {cl_names}")

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Team object.
        """
        return (f"Team(name='{self.name}', batters={self.batters}, starters={self.starters}, "
                f"relievers={self.relievers}, closers={self.closers}, bench={self.bench})")
