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
        self.pts = pts # Added points attribute
        self.year = year # Added year attribute
        self.set = set # Added set attribute

        # Cap HR at 0 if the original value is > 20, as strategy cards are not implemented
        if hr > 20:
            self.hr = 0
        else:
            self.hr = hr

        # Calculate the 'Out' range end based on SO, GB, FB
        self.out = so + gb + fb

        # Stats to track during the game
        self.plate_appearances = 0
        self.at_bats = 0
        self.runs_scored = 0
        self.rbi = 0 # Added RBI attribute
        self.singles = 0
        self.doubles = 0
        self.triples = 0
        self.home_runs = 0
        self.walks = 0
        self.strikeouts = 0
        self.outs = 0 # Total outs recorded by this batter

    def can_play(self, required_position):
        """
        Checks if the batter can play a required position based on the mapping.
        Handles the special DH rule.

        Args:
            required_position (str): The required position to check against (e.g., '1B', 'CF', 'DH').

        Returns:
            bool: True if the batter can play the position, False otherwise.
        """
        # Split the player's listed position(s) from the CSV by '/'
        csv_positions = [pos.strip() for pos in self.position.split('/') if pos.strip()] # Split and remove empty strings

        # Special rule for DH: if 'DH' is listed on the card, they can ONLY be a DH.
        if 'DH' in csv_positions:
            return required_position == 'DH'

        # If DH is not on the card, check other positions based on mapping
        if required_position == 'DH':
             # Any batter can be a DH if their card doesn't explicitly say DH (handled above)
             # and they are not already selected for another position.
             # The selection logic in create_random_team will handle if they are already selected.
             return True # For the purpose of this function, any non-DH-only player can be a DH

        # For other positions, check the mapping
        # Use the POSITION_MAPPING from constants.py
        from constants import POSITION_MAPPING # Import here to avoid circular dependency

        for csv_pos in csv_positions:
            # Get the list of positions this CSV position maps to
            mapped_positions = POSITION_MAPPING.get(csv_pos, [])
            if required_position in mapped_positions:
                return True

        return False


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

        # Concise stats display
        stats_display = (f"PA: {self.plate_appearances}, AB: {self.at_bats}, R: {self.runs_scored}, "
                         f"H: {self.singles + self.doubles + self.triples + self.home_runs}, " # Total Hits
                         f"1B: {self.singles}, 2B: {self.doubles}, 3B: {self.triples}, HR: {self.home_runs}, "
                         f"BB: {self.walks}, RBI: {self.rbi}, Outs: {self.outs}")

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
            hr (int): Home run range end.
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
        self.hr = hr # Pitchers can also have HR allowed ranges
        self.pts = pts # Added points attribute
        self.ip_limit = ip_limit # Added IP limit attribute
        self.year = year # Added year attribute
        self.set = set # Added set attribute

        # Calculate the 'Out' range end based on PU, SO, GB, FB
        self.out = pu + so + gb + fb

        # Stats to track during the game
        self.batters_faced = 0
        self.runs_allowed = 0
        self.earned_runs_allowed = 0 # Simplified - doesn't track errors yet
        self.hits_allowed = 0
        self.walks_allowed = 0
        self.strikeouts_thrown = 0
        self.outs_recorded = 0 # Total outs recorded by this pitcher
        self.innings_pitched = 0.0 # Track innings pitched


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


        # Concise stats display
        stats_display = (f"IP: {self.innings_pitched:.1f}, BF: {self.batters_faced}, "
                         f"H: {self.hits_allowed}, R: {self.runs_allowed}, ER: {self.earned_runs_allowed}, "
                         f"BB: {self.walks_allowed}, SO: {self.strikeouts_thrown}")

        return f"{display_name} ({self.position}, {self.pts} pts) | {ip_limit_display}, Stats: {stats_display}"


    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Pitcher object.
        """
        return (f"Pitcher(name='{self.name}', position='{self.position}', control={self.control}, "
                f"pu={self.pu}, so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, "
                f"b1={self.b1}, b2={self.b2}, b3={self.b3}, hr={self.hr}, pts={self.pts}, ip_limit={self.ip_limit}, year='{self.year}', set='{self.set}')")
