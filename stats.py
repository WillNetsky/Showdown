# stats.py
# Stat tracking for players and teams

#from entities import Team


class Stats:
    def __init__(self):
        # Batting stats to track
        self.plate_appearances = 0
        self.at_bats = 0
        self.runs_scored = 0
        self.rbi = 0
        self.singles = 0
        self.doubles = 0
        self.triples = 0
        self.home_runs = 0
        self.walks = 0
        self.strikeouts = 0
        self.outs = 0  # Total outs recorded by this batter
        self.hits = 0  # Combined hits stat - Will be calculated based on singles, doubles, triples, HR

        # Pitching stats to track
        self.batters_faced = 0
        self.runs_allowed = 0
        self.earned_runs_allowed = 0  # Simplified - doesn't track errors
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.strikeouts_thrown = 0
        self.outs_recorded = 0  # Total outs recorded by this pitcher
        self.home_runs_allowed = 0


    def update_hits(self):
        """Calculate total hits from individual hit types"""
        self.hits = self.singles + self.doubles + self.triples + self.home_runs

    # Batting stat calculations
    def calculate_avg(self):
        """
        Calculates the batting average (Hits / At-Bats).

        Returns:
            string: The batting average, or .000 if at-bats are zero.
        """
        self.update_hits()
        if self.at_bats == 0:
            return ".000"
        return "{:.3f}".format(self.hits / self.at_bats)[1:]

    def calculate_obp(self):
        """
        Calculates the On-base Percentage (OBP).
        OBP = (Hits + Walks) / (At-bats + Walks)

        Returns:
            str: The OBP, or .000 if the denominator is zero.
        """
        denominator = self.at_bats + self.walks
        if denominator == 0:
            return ".000"
        self.update_hits()
        return "{:.3f}".format((self.hits + self.walks) / denominator)[1:]

    def calculate_slg(self):
        """
        Calculates the Slugging Percentage (SLG).
        SLG = Total Bases / At-bats
        Total Bases = (Singles * 1) + (Doubles * 2) + (Triples * 3) + (Home Runs * 4)

        Returns:
            str: The SLG, or .000 if at-bats are zero.
        """
        if self.at_bats == 0:
            return ".000"
        total_bases = (self.singles * 1) + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        return "{:.3f}".format(total_bases / self.at_bats)[1:]

    def calculate_ops(self):
        """
        Calculates the On-base Plus Slugging (OPS).
        OPS = OBP + SLG

        Returns:
            str: The OPS.
        """
        return "{:.3f}".format(float(self.calculate_obp()) + float(self.calculate_slg()))[1:]
        # return float(self.calculate_obp()) + float(self.calculate_slg())

    # Pitching stat calculations
    def calculate_era(self):
        """
        Calculates the Earned Run Average (ERA).
        ERA = (Earned Runs Allowed * 9) / Innings Pitched

        Returns:
            float: The ERA, or 0.0 if innings pitched are zero.
        """
        if self.outs_recorded == 0:
            return 0.0
        return (self.earned_runs_allowed * 9) / float(self.outs_recorded / 3.0)

    def calculate_whip(self):
        """
        Calculates the Walks plus Hits per Innings Pitched (WHIP).
        WHIP = (Walks Allowed + Hits Allowed) / Innings Pitched

        Returns:
            float: The WHIP, or 0.0 if innings pitched are zero.
        """
        if self.outs_recorded == 0:
            return 0.0
        return (self.walks_allowed + self.hits_allowed) / float(self.outs_recorded / 3.0)

    def calculate_k_per_9(self):
        """
        Calculates strikeouts per 9 innings pitched (K/9).

        Returns:
            float: The K/9, or 0.0 if innings pitched are zero.
        """
        if self.outs_recorded == 0:
            return 0.0
        innings_pitched = self.outs_recorded / 3.0
        return (self.strikeouts_thrown * 9) / innings_pitched

    def get_formatted_ip(self):
        """
        Formats the innings pitched into standard baseball notation (X.Y where Y is 0, 1, or 2).

        Returns:
            str: The formatted innings pitched string.
        """
        # Get the whole innings and the fractional part
        whole_innings = int(self.outs_recorded / 3)
        fractional_part = self.outs_recorded % 3

        return f"{whole_innings}.{fractional_part}"

    def add_stats(self, other_stats):
        """
        Add another Stats object to this one (for cumulative stats)

        Args:
            other_stats: Another Stats object to add to this one

        Returns:
            self: Returns self for method chaining
        """
        for attr, value in vars(other_stats).items():
            if isinstance(value, (int, float)):
                current = getattr(self, attr, 0)
                setattr(self, attr, current + value)
        return self

    def reset(self):
        """Reset all stats to zero"""
        for attr in vars(self):
            if isinstance(getattr(self, attr), (int, float)):
                setattr(self, attr, 0)

    def __str__(self):
        """String representation showing key stats"""
        self.update_hits()
        batting = f"AVG: {self.calculate_avg()}, OPS: {self.calculate_ops()}"
        pitching = f"ERA: {self.calculate_era():.2f}, WHIP: {self.calculate_whip():.2f}"
        return f"{batting} | {pitching}"


class TeamStats(Stats):
    def __init__(self):
        super().__init__()
        # Team record
        self.wins = 0
        self.losses = 0
        self.games_played = 0
        self.elo_rating = 1500  # Starting ELO rating
        self.highest_elo = 1500  # Track highest achieved ELO
        self.lowest_elo = 1500  # Track lowest ELO
        self.elo_history = []  # Track ELO over time

        # Season tracking
        self.season_number = 1  # Current season number
        self.historical_records = []  # List of season records [(season, wins, losses, ties, elo)]

        # Team performance metrics
        self.shutouts = 0
        self.comeback_wins = 0
        self.run_differential = 0

    def calculate_win_pct(self):
        """
        Calculate winning percentage

        Returns:
            float: Winning percentage as a decimal
        """
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played

    def calculate_pythagorean_wins(self):
        """
        Calculate expected wins using Pythagorean expectation

        Returns:
            float: Expected win total based on runs scored/allowed
        """
        if self.runs_scored == 0 or self.runs_allowed == 0:
            return 0.0
        runs_scored_squared = self.runs_scored ** 2
        runs_allowed_squared = self.runs_allowed ** 2
        expected_win_pct = runs_scored_squared / (runs_scored_squared + runs_allowed_squared)
        return expected_win_pct * self.games_played

    def update_from_game(self, game_result):
        """
        Update team stats from a completed game

        Args:
            game_result: Dictionary containing game results data
        """
        self.games_played += 1

        # Update record
        if game_result.get('win', False):
            self.wins += 1
        elif game_result.get('loss', False):
            self.losses += 1
        else:
            self.ties += 1

        # Update runs
        self.runs_scored += game_result.get('runs_scored', 0)
        self.runs_allowed += game_result.get('runs_allowed', 0)
        self.run_differential = self.runs_scored - self.runs_allowed

        # Check for shutout
        if game_result.get('runs_allowed', 0) == 0:
            self.shutouts += 1


        # Update ELO if opponent_elo is provided
        if 'opponent_elo' in game_result:
            self.update_elo(
                opponent_elo=game_result['opponent_elo'],
                win=game_result.get('win', False),
                loss=game_result.get('loss', False),
                runs_scored=game_result.get('runs_scored', 0),
                runs_allowed=game_result.get('runs_allowed', 0)
            )

    def reset_for_new_season(self, maintain_elo=True):
        """
        Reset team stats for a new season while preserving historical data

        Args:
            maintain_elo (bool): Whether to maintain the current ELO rating (True) or reset to 1500 (False)

        Returns:
            int: The new season number
        """
        # Store current season record before resetting
        self.historical_records.append((
            self.season_number,
            self.wins,
            self.losses,
            self.elo_rating,
            self.run_differential
        ))

        # Increment season number
        self.season_number += 1

        # Store current ELO for potential reuse
        current_elo = self.elo_rating

        # Reset game results
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.games_played = 0

        # Reset performance metrics
        self.shutouts = 0
        self.complete_games = 0
        self.comeback_wins = 0
        self.run_differential = 0

        # Reset all batting and pitching stats
        for attr in vars(self):
            # Skip ELO-related attributes, season number, and historical records
            if attr in ['elo_rating', 'highest_elo', 'lowest_elo', 'elo_history',
                        'season_number', 'historical_records']:
                continue
            # Reset numeric attributes to zero
            if isinstance(getattr(self, attr), (int, float)):
                setattr(self, attr, 0)

        # Handle ELO rating for new season
        if not maintain_elo:
            self.elo_rating = 1500  # Reset to default
        # else:
        #     # Optional: Regress ELO toward the mean for competitive balance
        #     # This pulls very high or low ratings back toward 1500 by a certain percentage
        #     regression_factor = 0.25  # 25% regression toward the mean
        #     self.elo_rating = 1500 + (current_elo - 1500) * (1 - regression_factor)

        # Start a new ELO history list or mark the season boundary in the existing one
        # We add a None value as a season separator if we want to keep the history
        if len(self.elo_history) > 0:
            self.elo_history.append((self.games_played, None))  # Season separator

        return self.season_number  # Return the new season number

    def update_elo(self, opponent_elo, win=False, loss=False, runs_scored=0, runs_allowed=0, k_factor=32):
        """
        Update team's ELO rating based on game result

        Args:
            opponent_elo (float): The opponent's ELO rating
            win (bool): Whether this team won
            loss (bool): Whether this team lost
            runs_scored (int): Runs scored by this team
            runs_allowed (int): Runs allowed by this team
            k_factor (int): K-factor determining how much ELO can change (default: 32)
        """
        # Calculate expected win probability using ELO formula
        expected_win_prob = 1.0 / (1.0 + 10 ** ((opponent_elo - self.elo_rating) / 400.0))

        # Determine actual result (1 for win, 0.5 for tie, 0 for loss)
        if win:
            actual_result = 1.0
        elif loss:
            actual_result = 0.0
        else:
            actual_result = 0.5  # Tie

        # Calculate base ELO change
        elo_change = k_factor * (actual_result - expected_win_prob)

        # Apply margin of victory modifier (optional)
        # This gives more ELO points for dominant wins and takes away more for bad losses
        if runs_scored > 0 or runs_allowed > 0:
            run_diff = runs_scored - runs_allowed
            margin_multiplier = min(1.5, max(0.5, (abs(run_diff) + 3) / 8.0))

            # Only apply multiplier in the direction of the result
            if (win and run_diff > 0) or (loss and run_diff < 0):
                elo_change *= margin_multiplier

        # Update ELO rating
        self.elo_rating += elo_change

        # Track highest and lowest ELO
        self.highest_elo = max(self.highest_elo, self.elo_rating)
        self.lowest_elo = min(self.lowest_elo, self.elo_rating)

        # Add to history
        self.elo_history.append((self.games_played, self.elo_rating))

        return elo_change

    def __str__(self):
        """String representation of team stats"""
        record = f"Record: {self.wins}-{self.losses}"
        if self.ties > 0:
            record += f"-{self.ties}"
        win_pct = self.calculate_win_pct()
        return f"{record} ({win_pct:.3f}), Run Diff: {self.run_differential:+d}"

