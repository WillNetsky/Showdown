# entities.py
# Contains the core data structures for players (Batter and Pitcher).

# No local constants needed here, they will be imported if necessary

class Batter:
    def __init__(self, name, position, onbase, so, gb, fb, bb ,b1, b1p, b2, b3, hr, pts):
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
        """
        self.name = name
        self.position = position # Store the raw position string from CSV
        self.on_base = onbase
        self.so = so
        self.gb = gb
        self.fb = fb
        self.bb = bb
        self.b1 = b1
        self.b1p = b1p
        self.b2 = b2
        self.b3 = b3
        self.pts = pts # Added points attribute
        # Cap HR at 20 based on original comment logic
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
        # Import POSITION_MAPPING locally to avoid circular dependency if entities imports constants
        from constants import POSITION_MAPPING

        csv_positions = self.position.split('/')
        # Special rule for DH: if 'DH' is on the card, they can ONLY be a DH.
        if 'DH' in csv_positions:
            return required_position == 'DH'

        # If DH is not on the card, check other positions based on mapping
        if required_position == 'DH':
             # Any batter can be a DH if their card doesn't explicitly say DH (handled above)
             # and they are not already selected for another position.
             # The selection logic in create_random_team will handle if they are already selected.
             return True # For the purpose of this function, any non-DH-only player can be a DH

        # For other positions, check the mapping
        for csv_pos in csv_positions:
            mapped_positions = POSITION_MAPPING.get(csv_pos, [])
            if required_position in mapped_positions:
                return True
        return False


    def __str__(self):
        """
        Returns a string representation of the Batter object with stats.
        """
        # Display attributes and current stats, including points and RBI
        return (f"{self.name} ({self.position}): OB {self.on_base}, Out {self.out}, Pts {self.pts}, "
                f"Stats: PA {self.plate_appearances}, AB {self.at_bats}, R {self.runs_scored}, RBI {self.rbi}, "
                f"H ({self.singles}/{self.doubles}/{self.triples}/{self.home_runs}), BB {self.walks}, SO {self.strikeouts}")

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Batter object.
        """
        return (f"Batter(name='{self.name}', position='{self.position}', onbase={self.on_base}, "
                f"so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, b1={self.b1}, "
                f"b1p={self.b1p}, b2={self.b2}, b3={self.b3}, hr={self.hr}, pts={self.pts})")

class Pitcher:
    def __init__(self, name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_limit=None):
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
        self.hr = hr
        self.pts = pts # Added points attribute
        self.ip_limit = ip_limit # Added IP limit attribute
        # Cap HR at 20 based on original comment logic
        if hr > 20:
            self.hr = 0
        else:
            self.hr = hr
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
        Returns a string representation of the Pitcher object with stats.
        """
        # Display attributes and current stats, including points and IP
        return (f"{self.name} ({self.position}): Control {self.control}, Out {self.out}, Pts {self.pts}, "
                f"IP Limit: {self.ip_limit if self.ip_limit is not None else 'N/A'}, "
                f"Stats: BF {self.batters_faced}, IP {self.innings_pitched:.1f}, R {self.runs_allowed}, ER {self.earned_runs_allowed}, "
                f"H {self.hits_allowed}, BB {self.walks_allowed}, SO {self.strikeouts_thrown}")

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Pitcher object.
        """
        return (f"Pitcher(name='{self.name}', position='{self.position}', control={self.control}, "
                f"pu={self.pu}, so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, "
                f"b1={self.b1}, b2={self.b2}, b3={self.b3}, hr={self.hr}, pts={self.pts}, ip_limit={self.ip_limit})")
