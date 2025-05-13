# entities.py
# Defines the classes for Batter, Pitcher, and Team.

# Import necessary constants
from constants import POSITION_MAPPING # Import POSITION_MAPPING
from stats import Stats, TeamStats


class Batter:
    def __init__(self, name, position, on_base, so, gb, fb, bb ,b1, b1p, b2, b3, hr, pts, year=None, set_name=None, pos1='', fld1='', pos2='', fld2='', pos3='', fld3='', pos4='', fld4=''):
        """
        Initializes a batter with their attributes and optional year/set info.

        Args:
            name (str): The name of the player.
            position (str): The primary position of the player (raw string from data).
            on_base (int): The player's On-Base number.
            so (int): Strikeout range end.
            gb (int): Ground ball range end.
            fb (int): Fly ball range end.
            bb (int): Walk range end.
            b1 (int): Single range end.
            b1p (int): Single + Batter takes 2nd range end.
            b2 (int): Double range end.
            b3 (int): Triple range end.
            hr (int): Home run range end.
            pts (int): The player's points value.
            year (str, optional): The year of the player's card. Defaults to None.
            set_name (str, optional): The set the player belongs to. Defaults to None.
            pos1 (str, optional): Additional position 1. Defaults to ''.
            fld1 (str, optional): Fielding rating for pos1. Defaults to ''.
            pos2 (str, optional): Additional position 2. Defaults to ''.
            fld2 (str, optional): Fielding rating for fld2. Defaults to ''.
            pos3 (str, optional): Additional position 3. Defaults to ''.
            fld3 (str, optional): Fielding rating for fld3. Defaults to ''.
            pos4 (str, optional): Additional position 4. Defaults to ''.
            fld4 (str, optional): Fielding rating for fld4. Defaults to ''.
        """
        self.name = name
        self.position = position # Store the raw primary position string from data (defensive position)
        self.on_base = on_base
        self.so = so
        self.gb = gb
        self.fb = fb
        self.bb = bb
        self.b1 = b1
        self.b1p = b1p
        self.b2 = b2
        self.b3 = b3
        # Cap HR at 20 based on original comment logic
        if hr > 20:
            self.hr = 0
        else:
            self.hr = hr
        self.pts = pts
        self.year = year # Store year
        self.set = set_name # Store set name
        # Store additional positions and fielding ratings
        self.pos1 = pos1
        self.fld1 = fld1
        self.pos2 = pos2
        self.fld2 = fld2
        self.pos3 = pos3
        self.fld3 = fld3
        self.pos4 = pos4
        self.fld4 = fld4

        self.team_role = None # Will be set when added to a team roster (e.g., 'Starter', 'Bench')
        self.team_name = ""

        self.game_stats = Stats()
        self.season_stats = Stats()
        self.career_stats = Stats()

    def can_play(self, required_position):
        """
        Checks if the batter can play a required position based on their primary
        and additional positions. Handles the special DH rule.

        Args:
            required_position (str): The required position to check against (e.g., '1B', 'CF', 'DH').

        Returns:
            bool: True if the batter can play the position, False otherwise.
        """
        # Combine primary and additional positions for checking
        all_positions = [self.position, self.pos1, self.pos2, self.pos3, self.pos4]
        # Split any combined positions (like LFRF) and flatten the list
        split_positions = []
        for pos in all_positions:
            if pos: # Only process non-empty position strings
                split_positions.extend(pos.split('/'))

        # Special rule for DH: if 'DH' is among their listed positions, they can ONLY be a DH.
        if 'DH' in split_positions:
            return required_position == 'DH'

        # If DH is not on the card, check other positions based on mapping
        if required_position == 'DH':
             # Any batter can be a DH if their card doesn't explicitly say DH (handled above)
             # and they are not already selected for another position (handled in team creation).
             return True # For the purpose of this method, any non-DH-only player can be a DH

        # For other positions, check the mapping against all listed positions
        for listed_pos in split_positions:
            mapped_positions = POSITION_MAPPING.get(listed_pos, [])
            if required_position in mapped_positions:
                return True

        return False

    def __str__(self):
        """
        Returns a concise string representation of the Batter object.
        Includes team role and defensive position for starters, team role for bench.
        """
        year_set_info = f" - {self.year} {self.set}" if self.year or self.set else ""
        # --- CORRECTED: Display defensive position for Starters ---
        if self.team_role == 'Starter' and self.position:
             return f"{self.name}{year_set_info} ({self.position}, {self.pts} Pts)"
        elif self.team_role:
            # For Bench or other roles, just show the role
            return f"{self.name}{year_set_info} ({self.team_role}, {self.pts} Pts)"
        elif self.position:
            # Fallback to raw position if team_role is not set
            return f"{self.name}{year_set_info} ({self.position}, {self.pts} Pts)"
        else:
            # If neither team_role nor position is set
            return f"{self.name}{year_set_info} ({self.pts} Pts)"
        # --- END CORRECTED ---

    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Batter object.
        """
        return (f"Batter(name='{self.name}', position='{self.position}', onbase={self.on_base}, "
                f"so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, b1={self.b1}, "
                f"b1p={self.b1p}, b2={self.b2}, b3={self.b3}, hr={self.hr}, pts={self.pts}, "
                f"year='{self.year}', set_name='{self.set}', pos1='{self.pos1}', fld1='{self.fld1}', "
                f"pos2='{self.pos2}', fld2='{self.fld2}', pos3='{self.pos3}', fld3='{self.fld3}', "
                f"pos4='{self.pos4}', fld4='{self.fld4}', team_role='{self.team_role}')")


class Pitcher:
    def __init__(self, name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_out_limit=None, year=None, set_name=None):
        """
        Initializes a pitcher with their attributes and optional year/set info.

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
            pts (int): The player's points value.
            ip_out_limit (float, optional): The innings pitched limit for this pitcher (can be fractional). Defaults to None.
            year (str, optional): The year of the player's card. Defaults to None.
            set_name (str, optional): The set the player belongs to. Defaults to None.
        """
        self.name = name
        self.position = position # Now can be "P", "SP", "RP", "CL" from raw data
        self.control = control
        self.pu = pu
        self.so = so
        self.gb = gb
        self.fb = fb
        self.bb = bb
        self.b1 = b1
        self.b2 = b2
        self.hr = hr
        self.pts = pts
        self.out_limit = ip_out_limit # Added IP limit attribute
        self.year = year # Store year
        self.set = set_name # Store set name

        # Cap HR at 20, some values in the original game are above 20 to account for strategy cards, etc.
        if hr > 20:
            self.hr = 0
        # self.hr = hr if hr < 20 else self.hr = 0

        self.team_role = None # Will be set when added to a team roster (e.g., 'SP', 'RP', 'CL')
        self.team_name = ""

        self.game_stats = Stats()
        self.season_stats = Stats()
        self.career_stats = Stats()

    def __str__(self):
        """
        Returns a concise string representation of the Pitcher object.
        Includes team role if available, otherwise primary position if available.
        """
        year_set_info = f" - {self.year} {self.set}" if self.year or self.set else ""
        # --- CORRECTED: Prioritize team_role, then raw position ---
        if self.team_role:
            return f"{self.name}{year_set_info} ({self.team_role}, {self.pts} Pts)"
        elif self.position:
            return f"{self.name}{year_set_info} ({self.position}, {self.pts} Pts)"
        else:
            return f"{self.name}{year_set_info} ({self.pts} Pts)"
        # --- END CORRECTED ---


    def __repr__(self):
        """
        Returns a developer-friendly string representation of the Pitcher object.
        """
        return (f"Pitcher(name='{self.name}', position='{self.position}', control={self.control}, "
                f"pu={self.pu}, so={self.so}, gb={self.gb}, fb={self.fb}, bb={self.bb}, "
                f"b1={self.b1}, b2={self.b2}, hr={self.hr}, pts={self.pts}, out_limit={self.out_limit}, "
                f"year='{self.year}', set_name='{self.set}', team_role='{self.team_role}')")

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

        # Batters acts as the lineup and is by default sorted by descending pts (as per Showdown manual suggestion)
        self.batters = sorted(batters, key=lambda x: x.pts, reverse=True)
        self.bench = bench  # Added bench attribute

        # Starts will act as the rotation for multiple games as well, so we'll sort by pts
        self.starters = sorted(starters, key=lambda x: x.pts, reverse=True)

        # We'll do the same sorting for the bullpen
        self.relievers = relievers
        self.closers = closers
        self.bullpen = sorted(self.relievers+self.closers, key = lambda x: x.pts, reverse=True)

        # Combine all pitchers into one list for easier iteration if needed
        self.all_pitchers = starters + relievers + closers
        # Set the initial current pitcher - prefer SP, then RP, then CL
        self.current_pitcher = None
        self.starter_index = 0
        if self.starters:
            self.current_pitcher = self.starters[self.starter_index]
        elif self.relievers:
            self.current_pitcher = self.relievers[0]
        elif self.closers:
            self.current_pitcher = self.closers[0]

        self.current_batter_index = 0 # Index of the next batter in the lineup

        # Keep track of which relievers/closers have already pitched
        self.used_relievers = []
        self.used_closers = []
        self.used_starters = []

        # Calculate total team points
        self.total_points = sum(b.pts for b in self.batters) + sum(b.pts for b in self.bench) + sum(p.pts for p in self.all_pitchers)

        self.team_stats = TeamStats()



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
        Gets the next available reliever who hasn't pitched yet.

        Returns:
            Pitcher or None: An available reliever, or None if none are available.
        """
        for reliever in self.relievers:
            if reliever not in self.used_relievers:
                return reliever
        return None # No available relievers

    def get_available_closer(self):
        """
        Gets the closer if available and not used yet.

        Returns:
            Pitcher or None: The closer if available and not used, or None otherwise.
        """
        # Assuming only one closer for simplicity
        if self.closers and self.closers[0] not in self.used_closers:
            return self.closers[0]
        return None # Closer not available or already used

    def get_available_bullpen(self):
        """
        Creates a pool of available relievers and closers.

        Returns:
            list: A list of available Pitcher objects (RP or CL).
        """
        available_pool = []
        for reliever in self.bullpen:
            if reliever not in self.used_relievers:
                available_pool.append(reliever)

        return available_pool

    def post_game_team_cleanup(self):
        self.current_batter_index = 0  # Index of the next batter in the lineup

        # Keep track of which relievers/closers have already pitched
        self.used_relievers = []
        self.used_closers = []
        self.used_starters = []

        for pitcher in self.all_pitchers:
            pitcher.season_stats.add_stats(pitcher.game_stats)
            pitcher.career_stats.add_stats(pitcher.game_stats)
            pitcher.team_name = self.name
            pitcher.game_stats.reset()
        for batter in self.batters+self.bench:
            batter.season_stats.add_stats(batter.game_stats)
            batter.career_stats.add_stats(batter.game_stats)
            batter.team_name = self.name
            batter.game_stats.reset()
