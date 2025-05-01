# constants.py
# Stores various constants used throughout the baseball simulation project.

# Mapping of common position abbreviations to full names (not strictly used in current logic, but good for reference)
POSITION_MAPPING = {
    'C': ['C'],
    '1B': ['1B'],
    '2B': ['2B'],
    '3B': ['3B'],
    'SS': ['SS'],
    'LF': ['LF'],
    'CF': ['CF'],
    'RF': ['RF'],
    'OF': ['LF', 'CF', 'RF'], # For players who can play any outfield position
    'IF': ['1B', '2B', '3B', 'SS'], # For players who can play any infield position
    'LFRF': ['LF', 'RF'], # Added back the LFRF mapping
    'P': ['P'],
    'SP': ['SP'],
    'RP': ['RP'],
    'CL': ['CL'],
    '2B-1B-3B': ['1B', '2B', '3B'],
    '1B-3B': ['1B', '3B'],
    '2B-3B': ['2B', '3B'],
    '2B-1B': ['1B', '2B']
}

# The required starting positions for a team lineup (excluding Pitcher, which is handled separately)
STARTING_POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']

# Default minimum and maximum total points for team creation
# MLB Showdown Rule: Max 5000 points for a 20-player team
MIN_TEAM_POINTS = 4500
MAX_TEAM_POINTS = 5000
