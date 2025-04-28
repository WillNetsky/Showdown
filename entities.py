# entities.py
# Contains the classes for game entities like Batter and Pitcher.

class Batter:
    def __init__(self, name, position, onbase, so, gb, fb, bb ,b1, b1p, b2, b3, hr, pts, year=None, set=None):
        """
        Initializes a batter with their attributes.

        Args:
            name (str): The name of the player.
            position (str): The position of the player (e.g., "1B", "CF"). This is the raw CSV position string.
            onbase (int): The player's On-Base number.
            so (int): Strikeout range end.
            gb (int): Ground ball range end.
            fb (int): Fly ball range end.
            bb (int): Walk range end.
            b1 (int): Single range end.
            b1p (int): Single + Batter takes 2nd range end.
            b2 (int): Double range end.
            b2 (int): Double range end. # Corrected typo, should be b2
            b3 (int): Triple range end.
            hr (int): Home run range end.
            pts (int): The player's points value from the CSV.
            year (str, optional): The year of the player's card. Defaults to None.
            set (str, optional): The set of the player's card. Defaults to None.
        """
        self.name = name
        self.position = position # Store the raw position string from CSV
        self.on_base = onbase # Corrected attribute name
        self.so = so
        self.gb = gb
        self.fb = fb
        self.bb = bb
        self.b1 = b1
        self.b1p = b1p
        self.b2 = b2
        self.b3 = b3
        self.pts = pts
        self.year = year
        self.set = set

        # Cap HR at 20 if the original value is > 20, as strategy cards are not implemented
        # This logic might need refinement based on exact card rules, but keeps it within 1-20 range.
        if hr > 20:
            self.hr = 20 # Cap at 20, not 0, if the value is out of standard range
        else:
            self.hr = hr

        # Calculate the 'Out' range end based on SO, GB, FB
        self.out = so + gb + fb

        # Stats to track during the game
        self.plate_appearances = 0
        self.at_bats = 0 # Added At Bats tracking
        self.runs_scored = 0
        self.rbi = 0
        self.singles = 0
        self.doubles = 0
        self.triples = 0
        self.home_runs = 0 # This is home runs *hit* by the batter
        self.walks = 0
        self.strikeouts = 0 # Added Strikeouts tracking for batters
        self.outs = 0 # Total outs recorded by this batter (this is more for game flow, not standard boxscore K)

    def can_play(self, required_position):
        """
        Checks if the batter can play a required position based on the mapping.
        Handles the special DH rule and multi-position players.

        Args:
            required_position (str): The required position to check against (e.g., '1B', 'CF', 'DH').

        Returns:
            bool: True if the batter can play the position, False otherwise.
        """
        # Handle 'Unknown' position explicitly
        if self.position == 'Unknown':
            return False

        csv_positions = [pos.strip() for pos in self.position.split('/')]

        # Special rule for DH: if 'DH' is listed on the card, they can ONLY be a DH.
        if 'DH' in csv_positions:
            return required_position == 'DH'

        # If DH is not on the card, check other positions based on mapping
        if required_position == 'DH':
             # Any batter can be a DH if their card doesn't explicitly say DH (handled above)
             # and they are not already selected for another position.
             return True

        # For other positions, check the mapping
        from constants import POSITION_MAPPING # Import here to avoid circular dependency

        for csv_pos in csv_positions:
            # Get the list of positions this CSV position maps to
            # Ensure POSITION_MAPPING values are lists or handle single string
            mapped_positions = POSITION_MAPPING.get(csv_pos)
            if isinstance(mapped_positions, list):
                 if required_position in mapped_positions:
                     return True
            elif isinstance(mapped_positions, str):
                 if required_position == mapped_positions:
                      return True


        return False


    def calculate_avg(self):
        """Calculates batting average (Hits / At Bats)."""
        total_hits = self.singles + self.doubles + self.triples + self.home_runs
        if self.at_bats == 0:
            return 0.000
        return total_hits / self.at_bats

    def calculate_ops(self):
        """Calculates On-base Plus Slugging (OBP + SLG)."""
        total_hits = self.singles + self.doubles + self.triples + self.home_runs
        # Calculate On-base Percentage (OBP)
        obp_denominator = self.at_bats + self.walks # Assuming no HBP or Sacrifice flies in current sim
        obp = (total_hits + self.walks) / obp_denominator if obp_denominator > 0 else 0.0

        # Calculate Slugging Percentage (SLG)
        total_bases = (self.singles * 1) + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        slg = total_bases / self.at_bats if self.at_bats > 0 else 0.0

        return obp + slg


    def __str__(self):
        """
        Returns a string representation of the Batter object with basic info and stats.
        """
        # Display basic info (Name - YearSet (Pos, Pts)) and current stats
        display_name = self.name
        if self.year and self.set:
            display_name = f"{self.name} - {self.year}{self.set}"
        elif self.year:
             display_name = f"{self.name} - {self.year}"
        elif self.set:
             display_name = f"{self.name} - {self.set}"

        # Simplified stats display for now - will be formatted in main.py
        stats_display = f"PA: {self.plate_appearances}, R: {self.runs_scored}, RBI: {self.rbi}"


        return f"{display_name} ({self.position}, {self.pts} pts) | {stats_display}"


    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Batter object.
        """
        return (f"Batter(name='{self.name}', position='{self.position}', onbase={self.on_base}, "
                f"so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, b1={self.b1}, "
                f"b1p={self.b1p}, b2={self.b2}, b3={self.b3}, hr={self.hr}, pts={self.pts}, year='{self.year}', set='{self.set}')")


class Pitcher:
    def __init__(self, name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_limit=None, year=None, set=None):
        """
        Initializes a pitcher with their attributes.

        Args:
            name (str): The name of the player.
            position (str): The position of the player (e.g., "P", "SP", "RP", "CL").
            control (int): The pitcher's Control rating.
            pu (int): Pop up range end.
            so (int): Strikeout range end.
            gb (int): Ground ball range end.
            fb (int): Fly ball range end.
            bb (int): Walk range end.
            b1 (int): Single range end.
            b2 (int): Double range end.
            hr (int): Home run range end. # This is the HR *range* on the card
            pts (int): The player's points value from the CSV.
            ip_limit (float, optional): The innings pitched limit for this pitcher (can be fractional). Defaults to None.
            year (str, optional): The year of the player's card. Defaults to None.
            set (str, optional): The set of the player's card. Defaults to None.
        """
        self.name = name
        self.position = position # Now can be "P", "SP", "RP", "CL"
        self.control = control
        self.pu = pu
        self.so = so
        self.gb = gb
        self.fb = fb
        self.bb = bb
        self.b1 = b1
        self.b2 = b2
        self.hr = hr # Pitchers can also have HR allowed ranges (from card)
        self.pts = pts
        self.ip_limit = ip_limit
        self.year = year
        self.set = set

        # Calculate the 'Out' range end based on PU, SO, GB, FB
        self.out = pu + so + gb + fb

        # Stats to track during the game
        self.batters_faced = 0
        self.runs_allowed = 0
        self.earned_runs_allowed = 0 # Simplified - doesn't track errors yet
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.strikeouts_thrown = 0 # Corrected attribute name for clarity
        self.outs_recorded = 0 # Total outs recorded by this pitcher
        self.innings_pitched = 0.0 # Track innings pitched
        self.home_runs_allowed = 0 # Added stat to track HRs allowed during the game


    def calculate_era(self):
        """Calculates Earned Run Average (ERA)."""
        # ERA = (Earned Runs * 9) / Innings Pitched
        # Handle cases where IP is 0
        if self.innings_pitched == 0:
            return 0.00 # Or potentially infinity, but 0.00 is common in boxscores for 0 IP
        return (self.earned_runs_allowed * 9.0) / self.innings_pitched


    def __str__(self):
        """
        Returns a string representation of the Pitcher object with basic info and stats.
        """
        # Display basic info (Name - YearSet (Pos, Pts, IP Limit)) and current stats
        display_name = self.name
        if self.year and self.set:
            display_name = f"{self.name} - {self.year}{self.set}"
        elif self.year:
             display_name = f"{self.name} - {self.year}"
        elif self.set:
             display_name = f"{self.name} - {self.set}"

        ip_limit_display = f"IP Limit: {self.ip_limit:.1f}" if self.ip_limit is not None else "IP Limit: N/A"


        # Concise stats display - will be formatted in main.py
        stats_display = (f"IP: {self.innings_pitched:.1f}, BF: {self.batters_faced}, "
                         f"H: {self.hits_allowed}, R: {self.runs_allowed}, ER: {self.earned_runs_allowed}, "
                         f"BB: {self.walks_allowed}, SO: {self.strikeouts_thrown}")

        return f"{display_name} ({self.position}, {self.pts} pts) | {ip_limit_display}, Stats: {stats_display}"


    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Pitcher object.
        """
        # Removed the incorrect reference to b3
        return (f"Pitcher(name='{self.name}', position='{self.position}', control={self.control}, "
                f"pu={self.pu}, so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, "
                f"b1={self.b1}, b2={self.b2}, hr={self.hr}, pts={self.pts}, ip_limit={self.ip_limit}, year='{self.year}', set='{self.set}')")

