# stats.py
# Stat tracking for players and teams

# Linear weights for batting runs, could move to constants.py
BATTING_RUNS_WEIGHTS = {
    "BB": 0.292,    # Unintentional Walk
    #"HBP": 0.323,   # Hit By Pitch (add if you track it)
    "1B": 0.456,    # Single
    "2B": 0.763,    # Double
    "3B": 1.064,    # Triple
    "HR": 1.380,    # Home Run
    "OUT": -0.265   # Value of making an Out (all types of outs made by batter)
}

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

        # Pitching stats to track
        self.batters_faced = 0
        self.runs_allowed = 0
        self.earned_runs_allowed = 0
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.strikeouts_thrown = 0
        self.outs_recorded = 0  # Outs recorded by this pitcher
        self.home_runs_allowed = 0

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
        # Simplified OBP: (H + BB) / (AB + BB + SF + HBP)
        # Using available stats: (H + BB) / (AB + BB) assuming no SF/HBP tracked for PA.
        # Or more accurately if PA is tracked comprehensively: (H + BB) / PA
        # For now, using a common simplified denominator:
        denominator = self.at_bats + self.walks
        if self.plate_appearances > 0 and self.plate_appearances > denominator:  # If PA is more comprehensive
            denominator = self.plate_appearances
        if denominator == 0: return ".000"

        obp = (self.hits + self.walks) / denominator  # Assuming HBP not in numerator
        obp_str = "{:.3f}".format(obp)
        return obp_str[1:] if obp < 1.0 and obp_str.startswith("0.") else obp_str

    def calculate_slg(self):
        if self.at_bats == 0: return ".000"
        total_bases = (self.singles * 1) + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        slg = total_bases / self.at_bats
        slg_str = "{:.3f}".format(slg)
        return slg_str[1:] if slg < 1.0 and slg_str.startswith("0.") else slg_str

    def calculate_ops(self):
        str_obp = self.calculate_obp()
        str_slg = self.calculate_slg()
        try:
            obp_val = float("0" + str_obp if str_obp.startswith(".") and str_obp != ".---" else str_obp)
        except ValueError:
            obp_val = 0.0
        try:
            slg_val = float("0" + str_slg if str_slg.startswith(".") and str_slg != ".---" else str_slg)
        except ValueError:
            slg_val = 0.0

        ops_val = obp_val + slg_val
        ops_str = "{:.3f}".format(ops_val)
        return ops_str[1:] if ops_val < 1.0 and ops_str.startswith("0.") else ops_str

    def calculate_batting_runs(self):
        """
        Calculates Batting Runs based on linear weights.
        This version uses weights where positive events add value and outs subtract value.
        """
        batting_runs_value = 0.0

        batting_runs_value += self.walks * BATTING_RUNS_WEIGHTS["BB"]
        # if hasattr(self, 'hbp'): # Check if HBP is tracked
        #     batting_runs_value += self.hbp * BATTING_RUNS_WEIGHTS["HBP"]
        batting_runs_value += self.singles * BATTING_RUNS_WEIGHTS["1B"]
        batting_runs_value += self.doubles * BATTING_RUNS_WEIGHTS["2B"]
        batting_runs_value += self.triples * BATTING_RUNS_WEIGHTS["3B"]
        batting_runs_value += self.home_runs * BATTING_RUNS_WEIGHTS["HR"]

        # Add the negative value for all outs made by the batter
        # self.outs should accurately count each time this batter made an out.
        batting_runs_value += self.outs * BATTING_RUNS_WEIGHTS["OUT"]

        return batting_runs_value

    def calculate_era(self):
        if self.outs_recorded == 0:
            return float('inf') if self.earned_runs_allowed > 0 else 0.0
        return (self.earned_runs_allowed * 9) / (self.outs_recorded / 3.0)

    def calculate_whip(self):
        if self.outs_recorded == 0:
            return float('inf') if (self.walks_allowed + self.hits_allowed) > 0 else 0.0
        return (self.walks_allowed + self.hits_allowed) / (self.outs_recorded / 3.0)

    def calculate_k_per_9(self):
        if self.outs_recorded == 0: return 0.0
        return (self.strikeouts_thrown * 9) / (self.outs_recorded / 3.0)

    def get_formatted_ip(self):
        whole_innings = int(self.outs_recorded / 3)
        fractional_part = self.outs_recorded % 3
        return f"{whole_innings}.{fractional_part}"

    def add_stats(self, other_stats):
        if other_stats is None: return self
        for attr, value in vars(other_stats).items():
            if isinstance(value, (int, float)):
                current_value = getattr(self, attr, 0)
                setattr(self, attr, current_value + value)
        return self

    def reset(self):
        """Resets only the countable player statistics defined in this base class."""
        player_stat_attrs = [
            'plate_appearances', 'at_bats', 'runs_scored', 'rbi', 'singles',
            'doubles', 'triples', 'home_runs', 'walks', 'strikeouts', 'outs', 'hits',
            'batters_faced', 'runs_allowed', 'earned_runs_allowed', 'hits_allowed',
            'walks_allowed', 'strikeouts_thrown', 'outs_recorded', 'home_runs_allowed'
        ]
        for attr in player_stat_attrs:
            setattr(self, attr, 0)
        # self.hits = 0 # update_hits() will recalculate this when needed

    def __str__(self):
        self.update_hits()
        batting = f"AVG: {self.calculate_avg()}, OPS: {self.calculate_ops()}"
        era_val = self.calculate_era()
        whip_val = self.calculate_whip()
        era_str = f"{era_val:.2f}" if era_val != float('inf') else "INF"
        whip_str = f"{whip_val:.2f}" if whip_val != float('inf') else "INF"
        pitching = f"ERA: {era_str}, WHIP: {whip_str}"
        return f"{batting} | {pitching}"


class TeamStats(Stats):  # TeamStats can inherit player stats for team totals if needed
    def __init__(self):
        super().__init__()  # Initialize base Stats (for team totals of player-like stats if used)
        self.wins = 0
        self.losses = 0
        self.games_played = 0
        self.elo_rating = 1500.0
        self.highest_elo = 1500.0
        self.lowest_elo = 1500.0
        self.elo_history = []  # List of (games_played_at_update, elo_after_update)
        self.season_number = 1
        self.historical_records = []  # List of (season_num, wins, losses, final_elo, run_diff)

        # Team-specific aggregate counters (distinct from inherited player stats)
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
        exponent = 1.83
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
            self.update_elo(
                opponent_elo=game_result['opponent_elo'],
                win=game_result.get('win', False),
                runs_scored=rs,
                runs_allowed=ra
            )

    def reset_for_new_season(self, maintain_elo=True, default_elo=1500.0, team_name_for_debug="UnknownTeam"):
        """Resets team stats for a new season, carefully handling ELO."""
        # print(f"DEBUG: TeamStats.reset_for_new_season for {team_name_for_debug} - Entry ELO: {self.elo_rating}, maintain_elo: {maintain_elo}")

        if self.games_played > 0:  # Store record only if games were played
            self.historical_records.append((
                self.season_number, self.wins, self.losses,
                self.elo_rating, self.run_differential
            ))

        # Store ELO related values before any reset operation
        current_elo = self.elo_rating
        current_highest = self.highest_elo
        current_lowest = self.lowest_elo

        # Reset general team counters (W, L, runs, etc.)
        self.wins = 0
        self.losses = 0
        self.games_played = 0
        self.team_runs_scored = 0
        self.team_runs_allowed = 0
        self.run_differential = 0
        self.shutouts_for = 0
        self.shutouts_against = 0

        # Call super().reset() to reset any inherited player-like stats from the base Stats class.
        # The modified Stats.reset() will only touch base player stats, not ELO.
        super().reset()
        # print(f"DEBUG: {team_name_for_debug} - ELO after super().reset(): {self.elo_rating} (should be unchanged by Stats.reset)")

        # Now, explicitly handle ELO based on maintain_elo flag
        if maintain_elo:
            self.elo_rating = current_elo  # Restore the ELO captured before resets
            self.highest_elo = current_highest  # Restore if maintaining
            self.lowest_elo = current_lowest  # Restore if maintaining
            # Optional regression:
            # regression_factor = 0.33
            # self.elo_rating = default_elo + (self.elo_rating - default_elo) * (1 - regression_factor)
            # if self.elo_rating > self.highest_elo: self.highest_elo = self.elo_rating # Adjust if regressed
            # if self.elo_rating < self.lowest_elo: self.lowest_elo = self.elo_rating # Adjust if regressed

        else:  # Reset ELO to default
            self.elo_rating = default_elo
            self.highest_elo = default_elo
            self.lowest_elo = default_elo

        # elo_history can be managed per season or continuously.
        # If per season: self.elo_history = []
        # If continuous, it just keeps growing.
        # For now, let it be continuous. A marker could be added:
        # self.elo_history.append({'season_start': self.season_number + 1, 'elo': self.elo_rating})

        self.season_number += 1
        # print(f"DEBUG: {team_name_for_debug} - Exit ELO: {self.elo_rating}")
        return self.season_number

    def update_elo(self, opponent_elo, win, runs_scored=0, runs_allowed=0, k_factor=20):
        expected_win_prob = 1.0 / (1.0 + 10 ** ((opponent_elo - self.elo_rating) / 400.0))
        actual_score = 1.0 if win else 0.0
        elo_change_base = k_factor * (actual_score - expected_win_prob)
        mov_multiplier = 1.0
        if runs_scored != runs_allowed:
            run_diff = abs(runs_scored - runs_allowed)
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
            mov_multiplier = min(mov_multiplier, 1.5)
        elo_change = elo_change_base * mov_multiplier
        self.elo_rating += elo_change
        self.highest_elo = max(self.highest_elo, self.elo_rating)
        self.lowest_elo = min(self.lowest_elo, self.elo_rating)
        if self.games_played > 0:
            self.elo_history.append((self.games_played, self.elo_rating))
        return elo_change

    def __str__(self):
        win_pct = self.calculate_win_pct()
        return (f"Record: {self.wins}-{self.losses} ({win_pct:.3f}), "
                f"ELO: {self.elo_rating:.0f}, "
                f"RS: {self.team_runs_scored}, RA: {self.team_runs_allowed}, "
                f"Diff: {self.run_differential:+d}")

