# stats.py
# Stat tracking for players and teams

# from entities import Team


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
            return ".000"  # Standard display for 0 AB
        avg = self.hits / self.at_bats
        avg_str = "{:.3f}".format(avg)
        if avg < 1.0 and avg_str.startswith("0."):
            return avg_str[1:]
        return avg_str  # Should not happen for AVG but safe

    def calculate_obp(self):
        """
        Calculates the On-base Percentage (OBP).
        OBP = (Hits + Walks) / (At-bats + Walks)

        Returns:
            str: The OBP, or .000 if the denominator is zero.
        """
        self.update_hits()
        denominator = self.at_bats + self.walks + self.plate_appearances - self.at_bats - self.walks  # More robust: PA = AB+BB+HBP+SF+SH. Assuming no HBP/SF/SH for now.
        # A simpler, common formula is (H+BB) / (AB+BB) but often HBP and SF are included in PA for OBP.
        # For this game, (H+BB)/(AB+BB) is fine if plate_appearances isn't fully detailed.
        # Let's stick to the provided formula: (H+BB) / (AB+BB)
        # The denominator in your original code was (self.at_bats + self.walks)
        # If we want to include other ways to reach base, PA should be used.
        # For now, let's assume PA is only AB + BB for this stat as HBP/SF not tracked.
        # OBP = (Hits + Walks) / (At Bats + Walks + Hit By Pitch + Sacrifice Flies)
        # Given current stats, (Hits + Walks) / Plate Appearances is more accurate if PA tracks everything.
        # If PA is just AB + outcomes, then (H+BB)/(AB+BB) is fine.
        # Let's use the original denominator for consistency with previous behavior if PA isn't fully granular.

        effective_pa_for_obp = self.at_bats + self.walks  # Assuming HBP/SF are not tracked or part of these
        if effective_pa_for_obp == 0:  # Denominator for OBP
            return ".000"
        obp = (self.hits + self.walks) / effective_pa_for_obp
        obp_str = "{:.3f}".format(obp)
        if obp < 1.0 and obp_str.startswith("0."):
            return obp_str[1:]
        return obp_str  # Should not happen for OBP but safe

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
        slg = total_bases / self.at_bats
        slg_str = "{:.3f}".format(slg)
        # SLG can exceed 1.000 (e.g., player hits only HRs)
        if slg < 1.0 and slg_str.startswith("0."):
            return slg_str[1:]
        return slg_str

    def calculate_ops(self):
        """
        Calculates the On-base Plus Slugging (OPS).
        OPS = OBP + SLG

        Returns:
            str: The OPS, formatted to three decimal places.
        """
        # Get OBP and SLG as float values first
        # The calculate_obp/slg methods return strings like ".300" or "1.200"
        # We need to convert them to float correctly.

        str_obp = self.calculate_obp()
        str_slg = self.calculate_slg()

        # Convert string stats to float. If they start with ".", prepend "0"
        try:
            obp_val = float("0" + str_obp if str_obp.startswith(".") else str_obp)
        except ValueError:
            obp_val = 0.0  # Handle cases like ".---" or if it's already a valid float string

        try:
            slg_val = float("0" + str_slg if str_slg.startswith(".") else str_slg)
        except ValueError:
            slg_val = 0.0

        ops_val = obp_val + slg_val
        ops_str = "{:.3f}".format(ops_val)  # Format the sum

        # If the original sum was less than 1.0 AND the formatted string starts with "0."
        # then remove the leading "0". Otherwise, return the full string (e.g., "1.234").
        if ops_val < 1.0 and ops_str.startswith("0."):
            return ops_str[1:]
        else:
            return ops_str

    # Pitching stat calculations
    def calculate_era(self):
        """
        Calculates the Earned Run Average (ERA).
        ERA = (Earned Runs Allowed * 9) / Innings Pitched
        Innings Pitched = Outs Recorded / 3

        Returns:
            float: The ERA, or 0.0 if innings pitched are zero. Can be 'inf'.
        """
        if self.outs_recorded == 0:
            # If ER > 0 and IP == 0, ERA is infinite. Otherwise, 0.00
            return float('inf') if self.earned_runs_allowed > 0 else 0.0
        innings_pitched = self.outs_recorded / 3.0
        return (self.earned_runs_allowed * 9) / innings_pitched

    def calculate_whip(self):
        """
        Calculates the Walks plus Hits per Innings Pitched (WHIP).
        WHIP = (Walks Allowed + Hits Allowed) / Innings Pitched

        Returns:
            float: The WHIP, or 0.0 if innings pitched are zero. Can be 'inf'.
        """
        if self.outs_recorded == 0:
            return float('inf') if (self.walks_allowed + self.hits_allowed) > 0 else 0.0
        innings_pitched = self.outs_recorded / 3.0
        return (self.walks_allowed + self.hits_allowed) / innings_pitched

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
            if isinstance(value, (int, float)):  # Only add numeric types
                current_value = getattr(self, attr, 0)
                setattr(self, attr, current_value + value)
        return self

    def reset(self):
        """Reset all stats to zero"""
        for attr in vars(self):
            if isinstance(getattr(self, attr), (int, float)):
                setattr(self, attr, 0)
        # Ensure hits are also reset if they are calculated separately
        self.hits = 0

    def __str__(self):
        """String representation showing key stats"""
        self.update_hits()  # Ensure hits are current before calculating batting stats
        batting = f"AVG: {self.calculate_avg()}, OPS: {self.calculate_ops()}"

        era_val = self.calculate_era()
        whip_val = self.calculate_whip()
        era_str = f"{era_val:.2f}" if era_val != float('inf') else "INF"
        whip_str = f"{whip_val:.2f}" if whip_val != float('inf') else "INF"

        pitching = f"ERA: {era_str}, WHIP: {whip_str}"
        return f"{batting} | {pitching}"


class TeamStats(Stats):  # TeamStats inherits batting/pitching stats if a team itself could bat/pitch
    def __init__(self):
        super().__init__()  # Initialize player-level stats (e.g. for team totals)
        # Team record
        self.wins = 0
        self.losses = 0
        self.games_played = 0  # ties are not explicitly tracked in your W/L logic
        self.elo_rating = 1500  # Starting ELO rating
        self.highest_elo = 1500  # Track highest achieved ELO
        self.lowest_elo = 1500  # Track lowest ELO
        self.elo_history = []  # Track ELO over time (tuples of game_num, elo_rating)

        # Season tracking
        self.season_number = 1  # Current season number
        # List of tuples: (season_num, wins, losses, final_elo, run_diff)
        self.historical_records = []

        # Team performance metrics (these are team totals, not player averages)
        self.team_runs_scored = 0  # Distinct from inherited runs_scored which might be for a "team player"
        self.team_runs_allowed = 0
        self.run_differential = 0
        self.shutouts_for = 0  # Games where this team shut out the opponent
        self.shutouts_against = 0  # Games where this team was shut out
        # Comeback wins might need more complex game state tracking

    def calculate_win_pct(self):
        """
        Calculate winning percentage.
        Returns float: Winning percentage, or 0.0 if no games played.
        """
        if self.games_played == 0:
            return 0.0
        return self.wins / self.games_played

    def calculate_pythagorean_wins(self):
        """
        Calculate expected wins using Pythagorean expectation.
        Requires team_runs_scored and team_runs_allowed to be populated.
        Returns float: Expected win total.
        """
        if self.team_runs_scored == 0 and self.team_runs_allowed == 0:  # Avoid division by zero if no runs at all
            return 0.0
        # Common exponent is 1.83 for baseball, or 2
        exponent = 1.83
        runs_scored_sq = self.team_runs_scored ** exponent
        runs_allowed_sq = self.team_runs_allowed ** exponent
        if (runs_scored_sq + runs_allowed_sq) == 0:  # Should only happen if both are 0
            return 0.0
        expected_win_pct = runs_scored_sq / (runs_scored_sq + runs_allowed_sq)
        return expected_win_pct * self.games_played

    def update_from_game(self, game_result):
        """
        Update team stats from a completed game.
        Args:
            game_result (dict): Dictionary containing game results data.
                                Expected keys: 'win' (bool), 'loss' (bool),
                                'runs_scored' (int for this team),
                                'runs_allowed' (int by this team),
                                'opponent_elo' (float).
        """
        self.games_played += 1

        if game_result.get('win', False):
            self.wins += 1
        elif game_result.get('loss', False):  # Should be mutually exclusive with win
            self.losses += 1
        # Not explicitly handling ties here, assuming games don't tie or it's not tracked in W/L

        rs = game_result.get('runs_scored', 0)
        ra = game_result.get('runs_allowed', 0)
        self.team_runs_scored += rs
        self.team_runs_allowed += ra
        self.run_differential = self.team_runs_scored - self.team_runs_allowed

        if ra == 0 and rs > 0:  # This team pitched a shutout and won
            self.shutouts_for += 1
        if rs == 0 and ra > 0:  # This team was shut out and lost
            self.shutouts_against += 1

        if 'opponent_elo' in game_result:
            self.update_elo(
                opponent_elo=game_result['opponent_elo'],
                win=game_result.get('win', False),  # Pass the win/loss status
                runs_scored=rs,
                runs_allowed=ra
            )

    def reset_for_new_season(self, maintain_elo=True):
        """
        Reset team stats for a new season while preserving historical data.
        Args:
            maintain_elo (bool): If True, current ELO is carried over (possibly with regression).
                                 If False, ELO resets to default 1500.
        """
        # Store current season record before resetting
        if self.games_played > 0:  # Only store if games were played
            self.historical_records.append((
                self.season_number,
                self.wins,
                self.losses,
                self.elo_rating,  # Store ELO at end of season
                self.run_differential
            ))

        # Reset game counts and W/L for the new season
        self.wins = 0
        self.losses = 0
        self.games_played = 0

        # Reset team run totals for the new season
        self.team_runs_scored = 0
        self.team_runs_allowed = 0
        self.run_differential = 0
        self.shutouts_for = 0
        self.shutouts_against = 0

        # Player-level stats inherited from Stats (like for team totals if used that way) are reset by super().reset()
        # If TeamStats is purely for W/L and ELO, and player stats are separate,
        # then resetting inherited Stats might not be desired unless it represents team aggregate player stats.
        # For now, let's assume the inherited Stats are for team totals if they were ever used.
        # If not, this call to super().reset() might be irrelevant or could be removed
        # if TeamStats doesn't use the inherited batting/pitching attributes directly.
        # Given the context, it's likely TeamStats uses its own team_runs_scored etc.
        # However, to be safe and match original structure:
        super().reset()

        if not maintain_elo:
            self.elo_rating = 1500
            self.highest_elo = 1500  # Reset ELO tracking if ELO itself is reset
            self.lowest_elo = 1500
        # else: # Optional: ELO regression towards the mean
        # regression_factor = 0.33 # e.g., regress 1/3rd towards 1500
        # self.elo_rating = 1500 + (self.elo_rating - 1500) * (1 - regression_factor)

        # Add a marker or clear history for the new season's ELO progression
        # self.elo_history.append(None) # Or start a new list if preferred per season
        # A common practice is to keep a continuous history and just note season changes.
        # For simplicity, we'll just let it append. If plotting, one might handle season breaks.

        self.season_number += 1  # Increment for the next season
        return self.season_number

    def update_elo(self, opponent_elo, win, runs_scored=0, runs_allowed=0, k_factor=20):
        """
        Update team's ELO rating based on game result.
        Args:
            opponent_elo (float): Opponent's ELO.
            win (bool): True if this team won, False if lost. (Ties are not handled by this bool)
            runs_scored (int): Runs scored by this team.
            runs_allowed (int): Runs allowed by this team.
            k_factor (int): ELO K-factor.
        """
        expected_win_prob = 1.0 / (1.0 + 10 ** ((opponent_elo - self.elo_rating) / 400.0))

        actual_score = 1.0 if win else 0.0  # 0.5 for a tie, not handled by 'win' bool

        elo_change_base = k_factor * (actual_score - expected_win_prob)

        # Margin of Victory Multiplier (optional, from Glicko/Elo extensions)
        # This can make ELO more responsive to decisive wins/losses.
        # Example: ln(abs(RD) + 1) * (2.2 / ((WinnerElo - LoserElo)*0.001 + 2.2))
        # For simplicity, a basic MOV multiplier:
        mov_multiplier = 1.0
        if runs_scored != runs_allowed:  # Only apply if not a tie in score
            run_diff = abs(runs_scored - runs_allowed)
            # Simple multiplier: increases with run diff, capped.
            # This is a very basic example; sophisticated MOV multipliers exist.
            if run_diff == 1:
                mov_multiplier = 1.0
            elif run_diff == 2:
                mov_multiplier = 1.05
            elif run_diff == 3:
                mov_multiplier = 1.1
            elif run_diff <= 5:
                mov_multiplier = 1.15
            else:
                mov_multiplier = 1.2
            # Ensure multiplier doesn't excessively inflate for huge blowouts if not desired
            mov_multiplier = min(mov_multiplier, 1.5)

        elo_change = elo_change_base * mov_multiplier

        self.elo_rating += elo_change
        self.highest_elo = max(self.highest_elo, self.elo_rating)
        self.lowest_elo = min(self.lowest_elo, self.elo_rating)
        self.elo_history.append(
            (self.games_played, self.elo_rating))  # Record ELO after game (games_played already incremented)

        return elo_change

    def __str__(self):
        """String representation of team stats summary."""
        win_pct = self.calculate_win_pct()
        return (f"Record: {self.wins}-{self.losses} ({win_pct:.3f}), "
                f"ELO: {self.elo_rating:.0f}, "
                f"RS: {self.team_runs_scored}, RA: {self.team_runs_allowed}, "
                f"Diff: {self.run_differential:+d}")

