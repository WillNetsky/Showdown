# team.py
# Defines the Team class to manage a team's roster and pitcher usage.

from entities import Batter, Pitcher # Import Batter and Pitcher classes

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
        self.batters = batters # This is now explicitly the starting lineup
        self.starters = starters
        self.relievers = relievers
        self.closers = closers
        self.bench = bench # Added bench attribute
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
        # Note: Starters are not added to used_relievers/used_closers by handle_pitching_change,
        # but they are added to used_starters in play_game.
        self.used_relievers = []
        self.used_closers = []
        # Track used starters separately to manage their IP limits across innings
        self.used_starters = []


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

    def get_available_reliever(self):
        """
        Gets the next available reliever who hasn't pitched yet and is within their IP limit.

        Returns:
            Pitcher or None: An available reliever, or None if none are available or within limit.
        """
        for reliever in self.relievers:
            # Check if the reliever hasn't been used yet and is within their IP limit
            # --- CORRECTED: Use pitcher.ip_limit and pitcher.outs_recorded ---
            if reliever not in self.used_relievers and (reliever.ip_limit is None or reliever.outs_recorded < reliever.ip_limit):
            # --- END CORRECTED ---
                return reliever
        return None # No available relievers

    def get_available_closer(self):
        """
        Gets the closer if available, not used yet, and within their IP limit.

        Returns:
            Pitcher or None: The closer if available, not used, and within limit, or None otherwise.
        """
        # Assuming only one closer for simplicity
        # --- CORRECTED: Use pitcher.ip_limit and pitcher.outs_recorded ---
        if self.closers and self.closers[0] not in self.used_closers and (self.closers[0].ip_limit is None or self.closers[0].outs_recorded < self.closers[0].ip_limit):
        # --- END CORRECTED ---
            return self.closers[0]
        return None # Closer not available, already used, or over limit

    def get_available_reliever_or_closer_pool(self):
        """
        Creates a pool of available relievers and closers who are within their IP limits.

        Returns:
            list: A list of available Pitcher objects (RP or CL).
        """
        available_pool = []
        for reliever in self.relievers:
            # --- CORRECTED: Use pitcher.ip_limit and pitcher.outs_recorded ---
            if reliever not in self.used_relievers and (reliever.ip_limit is None or reliever.outs_recorded < reliever.ip_limit):
            # --- END CORRECTED ---
                available_pool.append(reliever)

        # Assuming only one closer, add if not used and within limit
        # --- CORRECTED: Use pitcher.ip_limit and pitcher.outs_recorded ---
        if self.closers and self.closers[0] not in self.used_closers and (self.closers[0].ip_limit is None or self.closers[0].outs_recorded < self.closers[0].ip_limit):
        # --- END CORRECTED ---
             available_pool.append(self.closers[0])

        return available_pool

    def __str__(self):
        """
        Returns a string representation of the Team object.
        """
        batter_names = ", ".join([b.name for b in self.batters])
        bench_names = ", ".join([b.name for b in self.bench]) if self.bench else "None"
        sp_names = ", ".join([p.name for p in self.starters]) if self.starters else "None"
        rp_names = ", ".join([p.name for p in self.relievers]) if self.relievers else "None"
        cl_names = ", ".join([p.name for p in self.closers]) if self.closers else "None"

        return (f"Team Name: {self.name}\n"
                f"Total Points: {self.total_points}\n"
                f"Starting Lineup ({len(self.batters)}): {batter_names}\n"
                f"Bench ({len(self.bench)}): {bench_names}\n"
                f"Starting Pitchers ({len(self.starters)}): {sp_names}\n"
                f"Relief Pitchers ({len(self.relievers)}): {rp_names}\n"
                f"Closers ({len(self.closers)}): {cl_names}")

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Team object.
        """
        return (f"Team(name='{self.name}', batters={repr(self.batters)}, "
                f"starters={repr(self.starters)}, relievers={repr(self.relievers)}, "
                f"closers={repr(self.closers)}, bench={repr(self.bench)})")
