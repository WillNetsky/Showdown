# stats.py
# Stat tracking for players and teams

# Linear weights for batting runs, could move to constants.py
BATTING_RUNS_WEIGHTS = {
    "BB": 0.292,  # Unintentional Walk
    # "HBP": 0.323,   # Hit By Pitch (add if you track it)
    "1B": 0.456,  # Single
    "2B": 0.763,  # Double
    "3B": 1.064,  # Triple
    "HR": 1.380,  # Home Run
    "OUT": -0.265  # Value of making an Out (all types of outs made by batter)
}

# Constants for FIP calculation (can be moved to a constants.py file later)
# This is an MLB-average constant; you might eventually derive one for your simulation.
DEFAULT_FIP_CONSTANT = 3.15


# Placeholder for league average ERA, to be determined or passed in for RSAA/FIP-Runs.
# For FIP calculation itself, only the FIP_CONSTANT is needed.
# For FIP-based Runs Saved, you'd also need a league average ERA or FIP.
DEFAULT_LEAGUE_AVG_ERA_PLACEHOLDER = 4.30

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
        self.outs = 0  # Total outs made by this batter at the plate
        self.hits = 0  # Combined hits stat
        # self.hbp = 0 # Add if you decide to track Hit By Pitch for batters

        # Pitching stats to track
        self.pitcher_wins = 0  # Example, if you track pitcher W/L
        self.pitcher_losses = 0
        self.games_started_pitcher = 0
        self.saves = 0
        self.batters_faced = 0
        self.runs_allowed = 0
        self.earned_runs_allowed = 0
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.strikeouts_thrown = 0  # K's by the pitcher
        self.outs_recorded = 0  # Outs recorded by this pitcher (used for IP)
        self.home_runs_allowed = 0
        self.hbp_allowed = 0  # Add for FIP calculation if you track pitcher HBP

    def update_hits(self):
        """Calculate total hits from individual hit types"""
        self.hits = self.singles + self.doubles + self.triples + self.home_runs

    def calculate_avg(self):
        self.update_hits()
        if self.at_bats == 0: return ".000"
        avg = self.hits / self.at_bats
        avg_str = "{:.3f}".format(avg)
        return avg_str[1:] if avg < 1.0 and avg_str.startswith("0.") else avg_str

    def calculate_obp(self):
        self.update_hits()
        # Using PA as the denominator if available and valid, else a simplified version
        # (H + BB + HBP) / (AB + BB + HBP + SF). Your PA should be the most accurate denominator.
        hbp_count = self.hbp if hasattr(self, 'hbp') else 0  # If you add HBP tracking for batters
        numerator = self.hits + self.walks + hbp_count
        denominator = self.plate_appearances

        if denominator == 0: return ".000"
        obp = numerator / denominator
        obp_str = "{:.3f}".format(obp)
        return obp_str[1:] if obp < 1.0 and obp_str.startswith("0.") else obp_str

    def calculate_slg(self):
        if self.at_bats == 0: return ".000"
        total_bases = (self.singles * 1) + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        slg = total_bases / self.at_bats
        slg_str = "{:.3f}".format(slg)
        return slg_str[1:] if slg < 1.0 and slg_str.startswith("0.") else slg_str

    def calculate_ops(self):
        # Ensure OBP and SLG return strings that can be converted to float, or handle errors
        str_obp = self.calculate_obp()
        str_slg = self.calculate_slg()
        try:
            obp_val = float("0" + str_obp if str_obp.startswith(".") and str_obp != ".---" else str_obp)
        except ValueError:
            obp_val = 0.0  # Or handle error appropriately
        try:
            slg_val = float("0" + str_slg if str_slg.startswith(".") and str_slg != ".---" else str_slg)
        except ValueError:
            slg_val = 0.0  # Or handle error appropriately

        ops_val = obp_val + slg_val
        ops_str = "{:.3f}".format(ops_val)
        # Handle cases like "1.000" correctly without removing "1."
        return ops_str if ops_val >= 1.0 else (ops_str[1:] if ops_str.startswith("0.") else ops_str)

    def calculate_batting_runs(self):
        batting_runs_value = 0.0
        batting_runs_value += self.walks * BATTING_RUNS_WEIGHTS["BB"]
        # if hasattr(self, 'hbp'):
        #     batting_runs_value += self.hbp * BATTING_RUNS_WEIGHTS["HBP"] # Add if HBP is tracked
        batting_runs_value += self.singles * BATTING_RUNS_WEIGHTS["1B"]
        batting_runs_value += self.doubles * BATTING_RUNS_WEIGHTS["2B"]
        batting_runs_value += self.triples * BATTING_RUNS_WEIGHTS["3B"]
        batting_runs_value += self.home_runs * BATTING_RUNS_WEIGHTS["HR"]
        batting_runs_value += self.outs * BATTING_RUNS_WEIGHTS["OUT"]
        return batting_runs_value

    # --- Pitching Specific Methods ---
    def get_innings_pitched(self):
        """Calculates and returns innings pitched as a float (e.g., 6.2 IP = 6.666...)."""
        return self.outs_recorded / 3.0

    def get_formatted_ip(self):
        """Returns innings pitched in the common baseball format (e.g., '6.2')."""
        whole_innings = int(self.outs_recorded / 3)
        fractional_part = self.outs_recorded % 3
        return f"{whole_innings}.{fractional_part}"

    def calculate_era(self):
        """Calculates Earned Run Average."""
        ip = self.get_innings_pitched()
        if ip == 0:
            return float('inf') if self.earned_runs_allowed > 0 else 0.0
        return (self.earned_runs_allowed * 9) / ip

    def calculate_whip(self):
        """Calculates Walks and Hits per Innings Pitched."""
        ip = self.get_innings_pitched()
        if ip == 0:
            return float('inf') if (self.walks_allowed + self.hits_allowed) > 0 else 0.0
        return (self.walks_allowed + self.hits_allowed) / ip

    def calculate_k_per_9(self):
        """Calculates Strikeouts per 9 Innings."""
        ip = self.get_innings_pitched()
        if ip == 0: return 0.0
        return (self.strikeouts_thrown * 9) / ip

    def calculate_fip(self, fip_constant=DEFAULT_FIP_CONSTANT, include_hbp=False):
        """
        Calculates Fielding Independent Pitching (FIP).
        Set include_hbp=True if self.hbp_allowed is tracked.
        """
        ip = self.get_innings_pitched()
        if ip == 0:
            # FIP is undefined for 0 IP. Could return a very high number if any detrimental events occurred.
            # For simplicity, if any HR, BB, or HBP occurred with 0 IP, it's infinitely bad.
            # Otherwise, if nothing happened, it's not meaningful, could be neutral.
            if self.home_runs_allowed > 0 or self.walks_allowed > 0 or \
                    (include_hbp and hasattr(self, 'hbp_allowed') and self.hbp_allowed > 0):
                return float('inf')
            return 0.0  # Or a neutral "league average" FIP like the constant itself if no events in 0 IP

        hr_comp = 13 * self.home_runs_allowed

        hbp_val = 0
        if include_hbp and hasattr(self, 'hbp_allowed'):
            hbp_val = self.hbp_allowed

        bb_hbp_comp = 3 * (self.walks_allowed + hbp_val)
        k_comp = 2 * self.strikeouts_thrown

        fip_numerator = hr_comp + bb_hbp_comp - k_comp
        fip = (fip_numerator / ip) + fip_constant
        return fip

    def calculate_pitching_runs_saved_era_based(self, league_avg_era_per_9):
        """Calculates Runs Saved Above Average (RSAA) based on ERA."""
        ip = self.get_innings_pitched()
        if ip == 0:
            return 0.0

        pitcher_era = self.calculate_era()

        # Handle infinite ERA case carefully
        if pitcher_era == float('inf'):
            # If ERA is infinite due to ER > 0 and IP == 0 (already handled by ip == 0 check above).
            # If ERA is infinite due to ER > 0 and IP > 0 (e.g. 1 ER in 0.1 IP -> ERA of 270),
            # the formula will produce a very large negative RSAA, which is appropriate.
            # If ERA is 0.0 because 0 ER / 0 IP, RSAA is 0.0.
            pass

        runs_saved_per_9 = league_avg_era_per_9 - pitcher_era
        total_runs_saved = (runs_saved_per_9 / 9.0) * ip
        return total_runs_saved

    def calculate_pitching_runs_saved_fip_based(self, league_avg_era_per_9, fip_constant=DEFAULT_FIP_CONSTANT,
                                                include_hbp_in_fip=False):
        """Calculates Runs Saved based on FIP compared to league average ERA."""
        ip = self.get_innings_pitched()
        if ip == 0:
            return 0.0

        pitcher_fip = self.calculate_fip(fip_constant=fip_constant, include_hbp=include_hbp_in_fip)

        if pitcher_fip == float('inf'):
            # Similar to ERA, an infinite FIP implies extremely poor performance for the IP.
            # The resulting RSAA will be very negative.
            pass

        runs_saved_per_9 = league_avg_era_per_9 - pitcher_fip
        total_runs_saved = (runs_saved_per_9 / 9.0) * ip
        return total_runs_saved

    def add_stats(self, other_stats):
        if other_stats is None: return self
        for attr, value in vars(other_stats).items():
            if isinstance(value, (int, float)):
                current_value = getattr(self, attr, 0)
                setattr(self, attr, current_value + value)
        return self

    def reset(self):
        """Resets countable player statistics."""
        # List all attributes that should be reset to 0 for a new period (e.g., game, season)
        # Ensure this list matches attributes defined in __init__ meant for counting.
        countable_attrs = [
            'plate_appearances', 'at_bats', 'runs_scored', 'rbi', 'singles',
            'doubles', 'triples', 'home_runs', 'walks', 'strikeouts', 'outs', 'hits',
            'pitcher_wins', 'pitcher_losses', 'games_started_pitcher', 'saves',  # Pitcher W/L/Sv
            'batters_faced', 'runs_allowed', 'earned_runs_allowed', 'hits_allowed',
            'walks_allowed', 'strikeouts_thrown', 'outs_recorded', 'home_runs_allowed',
            'hbp_allowed'  # Add if you track it
        ]
        if hasattr(self, 'hbp'):  # If batter HBP is tracked
            countable_attrs.append('hbp')

        for attr in countable_attrs:
            if hasattr(self, attr):  # Check if attribute exists before resetting
                setattr(self, attr, 0)

        # self.hits is recalculated by update_hits(), so setting to 0 is fine.

    def __str__(self):
        self.update_hits()  # Ensure hits are up-to-date for AVG/OPS
        batting_summary = f"AVG: {self.calculate_avg()}, OPS: {self.calculate_ops()}"

        pitching_summary = ""
        if self.outs_recorded > 0 or self.batters_faced > 0:  # Only show pitching if relevant
            era_val = self.calculate_era()
            whip_val = self.calculate_whip()
            era_str = f"{era_val:.2f}" if era_val != float('inf') else "INF"
            whip_str = f"{whip_val:.2f}" if whip_val != float('inf') else "INF"
            pitching_summary = f"ERA: {era_str}, WHIP: {whip_str}, IP: {self.get_formatted_ip()}"

        if pitching_summary:
            return f"{batting_summary} | {pitching_summary}"
        else:
            return batting_summary


class TeamStats(Stats):
    def __init__(self):
        super().__init__()
        self.wins = 0
        self.losses = 0
        self.games_played = 0
        self.elo_rating = 1500.0
        self.highest_elo = 1500.0
        self.lowest_elo = 1500.0
        self.elo_history = []
        self.season_number = 1
        self.historical_records = []

        self.team_runs_scored = 0
        self.team_runs_allowed = 0
        self.run_differential = 0
        self.shutouts_for = 0
        self.shutouts_against = 0

    def calculate_win_pct(self):
        if self.games_played == 0: return 0.0
        return self.wins / self.games_played

    def calculate_pythagorean_wins(self):
        if self.team_runs_scored == 0 and self.team_runs_allowed == 0: return 0.0
        exponent = 1.83  # Common exponent, can be researched/adjusted
        rs_sq = self.team_runs_scored ** exponent
        ra_sq = self.team_runs_allowed ** exponent
        if (rs_sq + ra_sq) == 0: return 0.0
        expected_win_pct = rs_sq / (rs_sq + ra_sq)
        return expected_win_pct * self.games_played

    def update_from_game(self, game_result):
        self.games_played += 1
        if game_result.get('win', False):
            self.wins += 1
        elif game_result.get('loss', False):
            self.losses += 1

        rs = game_result.get('runs_scored', 0)
        ra = game_result.get('runs_allowed', 0)
        self.team_runs_scored += rs
        self.team_runs_allowed += ra
        self.run_differential = self.team_runs_scored - self.team_runs_allowed

        if ra == 0 and rs > 0: self.shutouts_for += 1
        if rs == 0 and ra > 0: self.shutouts_against += 1

        if 'opponent_elo' in game_result:
            self.update_elo(opponent_elo=game_result['opponent_elo'],
                            win=game_result.get('win', False),
                            runs_scored=rs, runs_allowed=ra)

    def reset_for_new_season(self, maintain_elo=True, default_elo=1500.0, team_name_for_debug="UnknownTeam"):
        if self.games_played > 0:
            self.historical_records.append((
                self.season_number, self.wins, self.losses,
                self.elo_rating, self.run_differential))

        current_elo = self.elo_rating
        current_highest = self.highest_elo
        current_lowest = self.lowest_elo

        # Reset general team counters
        self.wins = 0;
        self.losses = 0;
        self.games_played = 0
        self.team_runs_scored = 0;
        self.team_runs_allowed = 0;
        self.run_differential = 0
        self.shutouts_for = 0;
        self.shutouts_against = 0

        super().reset()  # Resets inherited player-like stats if TeamStats uses them for totals

        if maintain_elo:
            self.elo_rating = current_elo
            self.highest_elo = current_highest
            self.lowest_elo = current_lowest
        else:
            self.elo_rating = default_elo
            self.highest_elo = default_elo
            self.lowest_elo = default_elo

        self.season_number += 1
        return self.season_number

    def update_elo(self, opponent_elo, win, runs_scored=0, runs_allowed=0, k_factor=20):
        expected_win_prob = 1.0 / (1.0 + 10 ** ((opponent_elo - self.elo_rating) / 400.0))
        actual_score = 1.0 if win else 0.0
        elo_change_base = k_factor * (actual_score - expected_win_prob)
        mov_multiplier = 1.0
        if runs_scored != runs_allowed:
            run_diff = abs(runs_scored - runs_allowed)
            # Simplified MoV multiplier, can be adjusted
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
            mov_multiplier = min(mov_multiplier, 1.5)  # Cap multiplier
        elo_change = elo_change_base * mov_multiplier
        self.elo_rating += elo_change
        self.highest_elo = max(self.highest_elo, self.elo_rating)
        self.lowest_elo = min(self.lowest_elo, self.elo_rating)
        if self.games_played > 0:  # Log ELO after at least one game, to tie it to game count
            self.elo_history.append((self.games_played, self.elo_rating))
        return elo_change

    def __str__(self):
        win_pct = self.calculate_win_pct()
        return (f"Record: {self.wins}-{self.losses} ({win_pct:.3f}), "
                f"ELO: {self.elo_rating:.0f}, "
                f"RS: {self.team_runs_scored}, RA: {self.team_runs_allowed}, "
                f"Diff: {self.run_differential:+d}")