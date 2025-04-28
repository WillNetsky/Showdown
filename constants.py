# constants.py

# Base numbers are from 2000's MLB Showdown
# You can adjust these to change the power of players. Keep them as integers.
# BASE_RUNNERS = ["None", "1B", "2B", "3B", "1B+2B"] # This constant is not used in the current logic
POSITIONS = ["C", "1B", "2B", "3B", "SS", "LFRF", "CF", "LFRF"] # Note: LFRF appears twice, P is missing

pitcher_hit_results = ['BB','1B','2B','HR']
batter_hit_results = ['BB','1B','1BP','2B','3B','HR']

# Mapping of CSV position values to required positions
POSITION_MAPPING = {
    'CF': ['CF'],
    'SS': ['SS'],
    'LFRF': ['LF', 'RF'],
    '3B': ['3B'],
    '2B': ['2B'],
    '1B': ['1B'],
    'C': ['C'],
    'OF': ['LF', 'CF', 'RF'],
    'LF': ['LF'],
    'DH': ['DH'], # DH is a special case, handled in selection logic
    '2B-1B-3B': ['1B', '2B', '3B'],
    '1B-3B': ['1B', '3B'],
    '2B-3B': ['2B', '3B'],
    '2B-1B': ['1B', '2B'],
    'IF': ['1B', '2B', '3B', 'SS']
}

# Required starting positions for the lineup
STARTING_POSITIONS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]

# Minimum and Maximum total points allowed for a team (9 starters + 1 bench + 4 SP + 6 RP/CL = 20 players)
MIN_TEAM_POINTS = 4500
MAX_TEAM_POINTS = 5000
