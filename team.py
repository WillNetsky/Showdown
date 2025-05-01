# team.py
# The Team class has been moved to entities.py to consolidate entity definitions.
# This file is now empty or serves as a placeholder.

# If you previously had a Team class defined here, remove it.
# The Team class is now imported from entities.py in main.py and team_management.py.



# # team.py
# # Contains the Team class to manage a team's roster and current state.
#
# import random
#
# class Team:
#     def __init__(self, name, batters, starters, relievers, closers, bench):
#         """
#         Initializes a Team object.
#
#         Args:
#             name (str): The name of the team.
#             batters (list): A list of Batter objects for the starting lineup (should be 9).
#             starters (list): A list of Pitcher objects for starting pitchers (should be 4).
#             relievers (list): A list of Pitcher objects for relief pitchers (should be 5). # Adjusted count based on typical roster
#             closers (list): A list of Pitcher objects for closers (should be 1). # Adjusted count based on typical roster
#             bench (list): A list of Batter objects for the bench (should be 1).
#         """
#         self.name = name
#         self.batters = batters # Starting lineup (9 players)
#         self.starters = starters # Starting pitchers (4 players)
#         self.relievers = relievers # Relief pitchers (5 players)
#         self.closers = closers # Closer pitchers (1 player)
#         self.bench = bench # Bench players (1 player)
#
#         # Combine all pitchers into one list for easier rotation
#         self.all_pitchers = self.starters + self.relievers + self.closers
#
#         # Ensure the total number of pitchers is 10 (4 SP + 5 RP + 1 CL)
#         if len(self.all_pitchers) != 10:
#             print(f"Warning: Team '{self.name}' initialized with {len(self.all_pitchers)} pitchers instead of 10.")
#
#         # Ensure the total number of batters is 10 (9 starters + 1 bench)
#         if len(self.batters) + len(self.bench) != 10:
#              print(f"Warning: Team '{self.name}' initialized with {len(self.batters) + len(self.bench)} batters instead of 10.")
#
#
#         # Initialize current batter and pitcher indices/pointers
#         self.current_batter_index = 0
#         self.current_pitcher_index = 0
#         self.current_pitcher = None # Attribute to hold the current active pitcher object
#
#         # Calculate initial total points
#         self.total_points = sum(p.pts for p in self.batters + self.bench + self.all_pitchers)
#
#
#     def get_next_batter(self):
#         """
#         Gets the next batter in the lineup. Cycles back to the top after the last batter.
#
#         Returns:
#             Batter: The next Batter object.
#         """
#         batter = self.batters[self.current_batter_index]
#         self.current_batter_index = (self.current_batter_index + 1) % len(self.batters)
#         return batter
#
#     def rotate_pitcher(self):
#         """
#         Rotates to the next available pitcher in the roster.
#         Cycles through starters, then relievers, then closers.
#         Sets the self.current_pitcher attribute.
#         Returns the newly selected pitcher, or None if no pitchers are available.
#         """
#         # Find the next pitcher who has not exceeded their IP limit
#         # Start checking from the pitcher *after* the current one
#         start_index = (self.current_pitcher_index + 1) % len(self.all_pitchers)
#         num_pitchers = len(self.all_pitchers)
#
#         for i in range(num_pitchers):
#             # Calculate the index to check, cycling through the list
#             pitcher_to_check_index = (start_index + i) % num_pitchers
#             next_pitcher = self.all_pitchers[pitcher_to_check_index]
#
#             # Check if the pitcher is available (hasn't exceeded IP limit)
#             # A pitcher is available if their outs_recorded is strictly LESS THAN their ip_limit_outs
#             # For ip_limit_outs = 0, they are only available if outs_recorded is also 0.
#             is_available = False
#             if next_pitcher.ip_limit_outs is None:
#                 is_available = True # No IP limit, always available
#             elif next_pitcher.ip_limit_outs == 0:
#                  if next_pitcher.outs_recorded == 0:
#                       is_available = True # 0 IP limit, available only if 0 outs recorded
#             elif next_pitcher.ip_limit_outs > 0:
#                  if next_pitcher.outs_recorded < next_pitcher.ip_limit_outs:
#                       is_available = True # Positive IP limit, available if outs recorded is less than limit
#
#
#             if is_available:
#                 self.current_pitcher = next_pitcher
#                 self.current_pitcher_index = pitcher_to_check_index # Update the index
#                 return self.current_pitcher # Return the newly selected pitcher
#
#         # If no available pitcher is found after checking all pitchers
#         self.current_pitcher = None
#         print(f"Warning: Team '{self.name}' has no available pitchers left!")
#         return None
#
#
#     def __str__(self):
#         """
#         Returns a string representation of the Team object.
#         """
#         return f"Team: {self.name} ({self.total_points} pts)"
#
#     def __repr__(self):
#         """
#         Returns a developer-friendly string representation of the Team object.
#         """
#         return (f"Team(name='{self.name}', batters={self.batters}, starters={self.starters}, "
#                 f"relievers={self.relievers}, closers={self.closers}, bench={self.bench})")
#
