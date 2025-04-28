# game_logic.py
# Contains the functions for simulating gameplay.

import random
import csv # Import the csv module
import os # Import os for file path joining in load_players_from_csv
import glob # Import glob for finding files in create_random_team

# Import necessary classes and constants from other modules
from entities import Batter, Pitcher
from team import Team
from constants import pitcher_hit_results, batter_hit_results, POSITION_MAPPING, STARTING_POSITIONS, MIN_TEAM_POINTS, MAX_TEAM_POINTS

def roll_dice(num_dice, sides):
    """
    Simulates rolling dice.

    Args:
        num_dice (int): The number of dice to roll.
        sides (int): The number of sides on each die.

    Returns:
        int: The sum of the dice rolls.
    """
    total = 0
    for _ in range(num_dice):
        total += random.randint(1, sides)
    return total

def get_chart_result(roll, player, pitcher, good_pitch):
    """
    Determines the result of a matchup based on the dice roll, player stats, and pitch quality.

    Args:
        roll (int): The result of the dice roll (1-20).
        player (Batter): The batter in the matchup.
        pitcher (Pitcher): The pitcher in the matchup.
        good_pitch (bool): True if the pitch was "good" (pitch_result > batter.on_base), False if "bad).

    Returns:
        str: The result of the matchup (e.g., "Out", "BB", "1B", "HR").
    """
    if good_pitch:
        # Use pitcher's chart
        # Determine the outcome based on the roll and pitcher's ranges
        if roll <= pitcher.out:
            return "Out"
        else:
            # Calculate the cumulative ranges for hits
            pitcher_ranges = {
                'BB': pitcher.bb,
                '1B': pitcher.b1,
                '2B': pitcher.b2,
                'HR': pitcher.hr
            }
            cumulative_range = pitcher.out
            for result, value in pitcher_ranges.items():
                cumulative_range += value
                if roll <= cumulative_range:
                    return result
            # Should not reach here if ranges cover 1-20
            return "Unknown Pitcher Result"
    else:
        # Use batter's chart
        # Determine the outcome based on the roll and batter's ranges
        if roll <= player.out:
            return "Out"
        else:
            # Calculate the cumulative ranges for hits
            batter_ranges = {
                'BB': player.bb,
                '1B': player.b1,
                '1BP': player.b1p,
                '2B': player.b2,
                '3B': player.b3,
                'HR': player.hr
            }
            cumulative_range = player.out
            for result, value in batter_ranges.items():
                cumulative_range += value
                if roll <= cumulative_range:
                    return result
            # Should not reach here if ranges cover 1-20
            return "Unknown Batter Result"


def handle_base_hit(runners, result, current_batter):
    """
    Calculates runs scored and new baserunning state after a base hit or walk.
    Also updates the runs_scored stat for batters who score.

    Args:
        runners: A list of three elements representing runners on the bases.
                 Index 0 is 1st base, Index 1 is 2nd base, Index 2 is 3rd base.
                 Each element is either a Batter object (if a runner is on base) or None.
                 Example: [batter1, None, batter3] means batter1 on 1st and batter3 on 3rd.
        result (str): The result of the at-bat ("BB", "1B", "1BP", "2B", "3B", "HR").
        current_batter (Batter): The batter who just had the plate appearance.


    Returns:
        A tuple: (runs_scored, new_runners)
        runs_scored (int): The number of runs scored on the play.
        new_runners (list): A list of three elements representing the new
                            runners on [1st, 2nd, 3rd] (Batter objects or None).
    """
    runs_scored = 0
    # Initialize new_runners with all bases empty
    new_runners = [None, None, None]
    # Unpack the current runner state for easier reading
    on_1b, on_2b, on_3b = runners

    if result == "BB":
        # Forced advances on a walk.
        # Start with the current runners and apply forced moves.
        # A runner is forced to advance if the base behind them becomes occupied.

        # Create a temporary list to build the new state
        temp_new_runners = list(runners)

        # Batter goes to 1st. If 1st is occupied, the runner on 1st is forced.
        if temp_new_runners[0] is not None: # If 1st is already occupied by a runner
            # Runner on 1st is forced to 2nd
            if temp_new_runners[1] is not None: # If 2nd is already occupied
                # Runner on 2nd is forced to 3rd
                if temp_new_runners[2] is not None: # If 3rd is already occupied
                    # Runner on 3rd is forced home
                    runner_scored = temp_new_runners[2]
                    if isinstance(runner_scored, Batter): # Ensure it's a Batter object
                        runner_scored.runs_scored += 1
                        runs_scored += 1
                temp_new_runners[2] = temp_new_runners[1] # R2 goes to 3rd
            temp_new_runners[1] = temp_new_runners[0] # R1 goes to 2nd
        temp_new_runners[0] = current_batter # Batter goes to 1st

        new_runners = temp_new_runners # Update the main new_runners list

    elif result == "1B":
        # Existing runners advance one base, batter to 1st
        # Process from 3rd to 1st to handle runs correctly
        if on_3b is not None:
            if isinstance(on_3b, Batter): # Ensure it's a Batter object
                on_3b.runs_scored += 1  # R3 scores
                runs_scored += 1
        if on_2b is not None:
            new_runners[2] = on_2b # R2 to 3rd
        if on_1b is not None:
            new_runners[1] = on_1b # R1 to 2nd
        new_runners[0] = current_batter # Batter to 1st

    elif result == "1BP":
        # Existing runners advance one base as if it were a standard single.
        # Process from 3rd to 1st first to determine where existing runners end up.
        temp_runners_after_single_advance = [None, None, None]
        temp_runs_scored = 0

        if on_3b is not None:
            if isinstance(on_3b, Batter): # Ensure it's a Batter object
                on_3b.runs_scored += 1 # R3 scores
                temp_runs_scored += 1
        if on_2b is not None:
            temp_runners_after_single_advance[2] = on_2b # R2 to 3rd
        if on_1b is not None:
            temp_runners_after_single_advance[1] = on_1b # R1 to 2nd

        # Now, place the batter based on the rule:
        # If 2nd base is open *after* existing runners moved, batter takes 2nd.
        # Otherwise, batter takes 1st.
        runs_scored = temp_runs_scored # Add runs from existing runners

        # Check the state of 2nd base *after* existing runners advanced
        if temp_runners_after_single_advance[1] is None: # If 2nd base is currently empty
            new_runners[1] = current_batter # Batter to 2nd
            # Existing runners who advanced to 3rd stay there
            new_runners[2] = temp_runners_after_single_advance[2]
        else:
            new_runners[0] = current_batter # Batter to 1st
            # Existing runners who advanced stay on their bases
            new_runners[1] = temp_runners_after_single_advance[1]
            new_runners[2] = temp_runners_after_single_advance[2]


    elif result == "2B":
        # Runners advance two bases, batter to 2nd
        # Process from 3rd to 1st to handle runs correctly
        if on_3b is not None:
            if isinstance(on_3b, Batter): # Ensure it's a Batter object
                on_3b.runs_scored += 1 # R3 scores
                runs_scored += 1
        if on_2b is not None:
             if isinstance(on_2b, Batter): # Ensure it's a Batter object
                on_2b.runs_scored += 1 # R2 scores
                runs_scored += 1
        if on_1b is not None:
            new_runners[2] = on_1b # R1 to 3rd
        new_runners[1] = current_batter # Batter to 2nd

    elif result == "3B":
        # Runners score, batter to 3rd
        # Process from 3rd to 1st to handle runs correctly
        if on_3b is not None:
            if isinstance(on_3b, Batter): # Ensure it's a Batter object
                on_3b.runs_scored += 1 # R3 scores
                runs_scored += 1
        if on_2b is not None:
            if isinstance(on_2b, Batter): # Ensure it's a Batter object
                on_2b.runs_scored += 1 # R2 scores
                runs_scored += 1
        if on_1b is not None:
             if isinstance(on_1b, Batter): # Ensure it's a Batter object
                on_1b.runs_scored += 1 # R1 scores
                runs_scored += 1
        new_runners[2] = current_batter # Batter to 3rd

    elif result == "HR":
        # All runners and batter score
        # Order doesn't strictly matter for scoring, but consistency is good
        if on_3b is not None:
            if isinstance(on_3b, Batter): # Ensure it's a Batter object
                on_3b.runs_scored += 1 # R3 scores
                runs_scored += 1
        if on_2b is not None:
            if isinstance(on_2b, Batter): # Ensure it's a Batter object
                on_2b.runs_scored += 1 # R2 scores
                runs_scored += 1
        if on_1b is not None:
             if isinstance(on_1b, Batter): # Ensure it's a Batter object
                on_1b.runs_scored += 1 # R1 scores
                runs_scored += 1
        if isinstance(current_batter, Batter): # Ensure it's a Batter object
            current_batter.runs_scored += 1 # Batter scores
            runs_scored += 1
        # new_runners remains [None, None, None] as all scored

    else:
        # Handle unexpected result types - maybe return original state and 0 runs
        # or raise an error. Returning original state here.
        print(f"Warning: Unhandled result type '{result}'. Returning original state.")
        return 0, runners


    return runs_scored, new_runners


def play_ball(batter: Batter, pitcher: Pitcher, inning_log, runners):
    """
    Simulates a single plate appearance.

    Args:
        batter (Batter): The batter object.
        pitcher (Pitcher): The pitcher object.
        inning_log (list): The log for the current inning.
        runners: A list of three elements representing runners on the bases [1st, 2nd, 3rd].

    Returns:
        tuple: (result, runs_scored, new_runners)
        result (str): The outcome of the plate appearance (e.g., "Out", "BB", "1B").
        runs_scored (int): The number of runs scored on the play.
        new_runners (list): The updated list of runners on the bases.
    """
    batter.plate_appearances += 1
    pitcher.batters_faced += 1

    # Roll the pitch result (1-20)
    pitch_result = roll_dice(1, 20)

    # Determine if it's a "good" or "bad" pitch based on the batter's On-Base number
    good_pitch = pitch_result > batter.on_base
    pitch_quality_text = "Good Pitch" if good_pitch else "Bad Pitch"

    # Roll the swing result (1-20)
    swing_roll = roll_dice(1, 20)

    # Get the result from the appropriate chart
    result = get_chart_result(swing_roll, batter, pitcher, good_pitch)

    runs_scored = 0
    new_runners = list(runners) # Start with the current runners

    # Create a readable string for the runners on base
    runner_names = []
    if runners[0] is not None:
        runner_names.append(f"1B: {runners[0].name}")
    if runners[1] is not None:
        runner_names.append(f"2B: {runners[1].name}")
    if runners[2] is not None:
        runner_names.append(f"3B: {runners[2].name}")
    runners_display = ", ".join(runner_names) if runner_names else "Bases Empty"

    # Include roll values and pitch quality in the log entry
    inning_log.append(f"{batter.name} vs. {pitcher.name} ({runners_display}) [Pitch Roll: {pitch_result} ({pitch_quality_text}), Swing Roll: {swing_roll}]: {result}")

    # Update stats and runners based on the result
    if result == "Out":
        batter.outs += 1
        pitcher.outs_recorded += 1
        # IP is updated in play_inning based on outs
    elif result == "BB":
        batter.walks += 1
        pitcher.walks_allowed += 1
        runs_scored, new_runners = handle_base_hit(runners, result, batter)
    elif result in ["1B", "1BP", "2B", "3B", "HR"]:
        batter.at_bats += 1 # Hits count as at-bats
        pitcher.hits_allowed += 1
        if result == "1B":
            batter.singles += 1
        elif result == "1BP":
             batter.singles += 1 # 1BP is still a single for batter stats
        elif result == "2B":
            batter.doubles += 1
        elif result == "3B":
            batter.triples += 1
        elif result == "HR":
            batter.home_runs += 1
            pitcher.runs_allowed += (sum(1 for r in runners if r is not None) + 1) # Count runners on base + batter
            pitcher.earned_runs_allowed += (sum(1 for r in runners if r is not None) + 1) # Assuming all runs are earned for simplicity
        runs_scored_on_play, new_runners = handle_base_hit(runners, result, batter)
        runs_scored += runs_scored_on_play # Add runs from base advancement

    else:
        # Handle unexpected results as outs for now
        inning_log.append(f"Warning: Unhandled result '{result}' for {batter.name}. Treating as Out.")
        result = "Out"
        batter.outs += 1
        pitcher.outs_recorded += 1
        # IP is updated in play_inning based on outs

    # Update RBI for the batter who drove in runs
    if runs_scored > 0:
        batter.rbi += runs_scored
        pitcher.runs_allowed += runs_scored
        pitcher.earned_runs_allowed += runs_scored # Assuming all runs are earned for simplicity


    return result, runs_scored, new_runners

def play_inning(batting_team: Team, pitching_team: Team, inning_number, game_log, half_inning, game_state):
    """
    Simulates a single inning of a game.

    Args:
        batting_team (Team): The batting team object.
        pitching_team (Team): The pitching team object.
        inning_number (int): The current inning number.
        game_log (list): A list to store the game log.
        half_inning (str): "Top" or "Bottom"
        game_state (dict): A dictionary containing the current state of the game (e.g., scores).

    Returns:
        int: The number of runs scored in the inning.
    """
    outs = 0
    runs_scored_this_inning = 0
    # Runners list now holds Batter objects or None
    runners = [None, None, None]
    inning_log = [] #use inning log to track events, then add to game log

    inning_log.append(f"--- {half_inning} of the {inning_number} Inning ---")

    # Get the current pitcher at the start of the inning
    pitcher = pitching_team.current_pitcher
    if pitcher is None:
        inning_log.append("Error: Pitcher not available for pitching team at start of inning.")
        game_log.extend(inning_log)
        return 0 # No runs scored if no pitcher

    # Check for pitching change right at the start of the inning if the pitcher is already at their limit
    # This handles cases where a pitcher finished the previous inning over their limit
    if pitcher and pitcher.ip_limit is not None and pitcher.innings_pitched >= pitcher.ip_limit:
        inning_log.append(f"Pitching Change: {pitcher.name} ({pitcher.innings_pitched:.1f} IP) reached IP limit and is replaced.")
        # Pass batting_team to handle_pitching_change
        pitcher = handle_pitching_change(pitching_team, batting_team, inning_number, half_inning, game_state, inning_log)
        # If handle_pitching_change returns None, the inning cannot continue
        if pitcher is None:
             inning_log.append("Error: No pitcher available to start inning.")
             game_log.extend(inning_log)
             return 0 # No runs scored if no pitcher


    while outs < 3:
        # If pitcher is None here, it means handle_pitching_change failed to find a new pitcher previously
        if pitcher is None:
             break # End the inning


        # Get the next batter from the batting team
        current_batter = batting_team.get_next_batter()

        # --- Check for pitching change BEFORE the plate appearance if facing this batter exceeds limit ---
        # This handles cases where a pitcher is just under their limit and the next batter would push them over
        if pitcher and pitcher.ip_limit is not None and (pitcher.innings_pitched + (1/3) > pitcher.ip_limit):
             inning_log.append(f"Pitching Change: {pitcher.name} ({pitcher.innings_pitched:.1f} IP) is replaced to avoid exceeding IP limit.")
             # Pass batting_team to handle_pitching_change
             pitcher = handle_pitching_change(pitching_team, batting_team, inning_number, half_inning, game_state, inning_log)
             # If handle_pitching_change returns None, the inning cannot continue
             if pitcher is None:
                  inning_log.append("Error: No pitcher available to continue inning.")
                  break # End the inning if no pitchers available

        # If pitcher is None after the proactive check, break the loop
        if pitcher is None:
             break


        result, runs_this_play, runners = play_ball(current_batter, pitcher, inning_log, runners)
        runs_scored_this_inning += runs_this_play

        # Update pitcher IP *after* the play if it was an out
        if result == "Out":
            pitcher.innings_pitched += 1/3
            # Round to one decimal place to avoid floating point issues with thirds
            pitcher.innings_pitched = round(pitcher.innings_pitched, 1)
            outs += 1
        elif result == "Error": # Handle errors from play_ball
             outs += 1 # Treat unknown results as outs for now
             pitcher.innings_pitched += 1/3
             pitcher.innings_pitched = round(pitcher.innings_pitched, 1)


    inning_log.append(f"End of {half_inning} {inning_number}, {runs_scored_this_inning} run(s) scored.")
    game_log.extend(inning_log) #add inning log to game log
    return runs_scored_this_inning

def handle_pitching_change(pitching_team: Team, batting_team: Team, inning_number, half_inning, game_state, inning_log):
    """
    Handles the logic for a pitching change, selecting the next available pitcher.
    Selects a random available reliever or closer.

    Args:
        pitching_team (Team): The team needing a pitching change.
        batting_team (Team): The team currently batting.
        inning_number (int): The current inning number.
        half_inning (str): "Top" or "Bottom".
        game_state (dict): A dictionary containing the current state of the game (e.g., scores).
        inning_log (list): The log for the current inning.

    Returns:
        Pitcher or None: The new current pitcher, or None if no available pitchers.
    """
    next_pitcher = None

    # Create a combined list of available relievers and closers
    available_rp_cl = pitching_team.get_available_reliever_or_closer_pool()

    if available_rp_cl:
        # Select a random pitcher from the available pool
        next_pitcher = random.choice(available_rp_cl)
        pitching_team.current_pitcher = next_pitcher

        # Add the selected pitcher to the appropriate used list
        if next_pitcher.position == 'CL':
            pitching_team.used_closers.append(next_pitcher)
            inning_log.append(f"Pitching Change: {pitching_team.current_pitcher.name} enters the game (Closer).")
        else: # Assumes 'RP' or 'P'
            pitching_team.used_relievers.append(next_pitcher)
            inning_log.append(f"Pitching Change: {pitching_team.current_pitcher.name} enters the game (Reliever).")
    else:
        inning_log.append("Error: No available relievers or closers for pitching change.")
        pitching_team.current_pitcher = None # No pitcher available

    return pitching_team.current_pitcher


def play_game(team1: Team, team2: Team, num_innings=9):
    """
    Simulates a complete game between two teams.

    Args:
        team1 (Team): The first team object.
        team2 (Team): The second team object.
        num_innings (int, optional): The number of innings to play. Defaults to 9.

    Returns:
        tuple: (score1, score2, game_log) - The final scores and the game log.
    """
    game_state = {
        team1.name: 0,
        team2.name: 0
    }
    game_log = []

    game_log.append(f"--- Game Start: {team1.name} vs. {team2.name} ---")

    for inning in range(1, num_innings + 1):
        # Top of the inning: Team 1 bats, Team 2 pitches
        runs_team1 = play_inning(team1, team2, inning, game_log, "Top", game_state)
        game_state[team1.name] += runs_team1

        # Bottom of the inning: Team 2 bats, Team 1 pitches
        # Only play bottom of 9th or later if Team 2 is not already winning
        if inning < num_innings or game_state[team2.name] <= game_state[team1.name]:
             runs_team2 = play_inning(team2, team1, inning, game_log, "Bottom", game_state)
             game_state[team2.name] += runs_team2

        # Check for game over after bottom of the inning if 9 innings are complete
        if inning >= num_innings and game_state[team1.name] != game_state[team2.name]:
            break # Game ends if not tied after regulation

    # Handle extra innings if tied after regulation
    while game_state[team1.name] == game_state[team2.name]:
        inning += 1
        game_log.append(f"--- Extra Inning: {inning} ---")

        # Top of the inning
        runs_team1 = play_inning(team1, team2, inning, game_log, "Top", game_state)
        game_state[team1.name] += runs_team1

        # Bottom of the inning
        runs_team2 = play_inning(team2, team1, inning, game_log, "Bottom", game_state)
        game_state[team2.name] += runs_team2

        # Check if the tie is broken after the bottom of the inning
        if game_state[team1.name] != game_state[team2.name]:
            break # Game ends if the tie is broken

    game_log.append(f"--- Game End: {team1.name} {game_state[team1.name]} - {team2.name} {game_state[team2.name]} ---")

    return game_state[team1.name], game_state[team2.name], game_log

# Helper function to load players from a CSV file
def load_players_from_csv(filepath):
    """
    Loads player data from a CSV file and creates Batter or Pitcher objects.
    Includes flexible header matching and error handling.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        list: A list of Batter and Pitcher objects.
    """
    players = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            csv_headers = [header.strip() for header in reader.fieldnames] if reader.fieldnames else []

            # Create a mapping from lowercase CSV headers to original headers
            header_map = {header.lower(): header for header in csv_headers}

            row_count = 0
            for row in reader:
                row_count += 1

                try:
                    # Access row data using lowercase keys and the header_map
                    # Provide default empty strings if the lowercase key isn't found
                    # This handles truly missing columns more gracefully during access
                    pts_str = row.get(header_map.get('pts', 'Pts'), '0').strip()
                    onbase_str = row.get(header_map.get('onbase', 'On Base'), '0').strip() # Use 'onbase' from CSV
                    so_str = row.get(header_map.get('so', 'SO'), '0').strip()
                    gb_str = row.get(header_map.get('gb', 'GB'), '0').strip() # Keep GB check, default to 0 if missing
                    fb_str = row.get(header_map.get('fo', 'FB'), '0').strip() # Map 'fo' from CSV to 'FB'
                    bb_str = row.get(header_map.get('bb', 'BB'), '0').strip()
                    b1_str = row.get(header_map.get('bi', '1B'), '0').strip() # Map 'bi' from CSV to '1B'
                    b1p_str = row.get(header_map.get('bip', '1BP'), '0').strip() # Map 'bip' from CSV to '1BP'
                    b2_str = row.get(header_map.get('b2', '2B'), '0').strip() # Map 'b2' from CSV to '2B'
                    b3_str = row.get(header_map.get('b3', '3B'), '0').strip() # Map 'b3' from CSV to '3B'
                    hr_str = row.get(header_map.get('hr', 'HR'), '0').strip()
                    control_str = row.get(header_map.get('control', 'Control'), '0').strip()
                    pu_str = row.get(header_map.get('pu', 'PU'), '0').strip()
                    ip_limit_str = row.get(header_map.get('ip limit', 'IP Limit'), '').strip() # Map 'ip' from CSV to 'IP Limit'
                    # Also check for 'ip' if 'ip limit' isn't found
                    if not ip_limit_str:
                         ip_limit_str = row.get(header_map.get('ip', 'ip'), '').strip()


                    # Attempt to convert strings to appropriate types, with specific error handling
                    try:
                        pts = int(pts_str)
                        onbase = int(onbase_str)
                        so = int(so_str)
                        gb = int(gb_str) # Will be 0 if 'gb' column is missing
                        fb = int(fb_str)
                        bb = int(bb_str)
                        b1 = int(b1_str) # Use the mapped b1 value
                        b1p = int(b1p_str) # Use the mapped b1p value
                        b2 = int(b2_str) # Use the mapped b2 value
                        b3 = int(b3_str) # Use the mapped b3 value
                        hr = int(hr_str)
                        control = int(control_str)
                        pu = int(pu_str)
                        ip_limit = float(ip_limit_str) if ip_limit_str else None # Convert to float if not empty, otherwise None
                    except ValueError as e:
                         print(f"Error converting numeric data in row {row_count} for player {row.get(header_map.get('name', 'Name'), 'Unknown')}: {e}. Data: {row}. Skipping row.")
                         continue # Skip this row if numeric conversion fails


                    player_type = row.get(header_map.get('type', 'Type'), '').strip()
                    player_name = row.get(header_map.get('name', 'Name'), 'Unknown Player').strip()
                    # Use the first position column found, prioritizing 'pos' then 'pos2', etc.
                    player_position_raw = row.get(header_map.get('pos', 'Position'), '').strip()
                    if not player_position_raw:
                         player_position_raw = row.get(header_map.get('pos2', 'pos2'), '').strip()
                    if not player_position_raw:
                         player_position_raw = row.get(header_map.get('pos3', 'pos3'), '').strip()
                    if not player_position_raw:
                         player_position_raw = row.get(header_map.get('pos4', 'pos4'), '').strip()
                    if not player_position_raw:
                         player_position_raw = 'Unknown' # Default if no position found


                    # --- Logic to infer player type if 'Type' column is missing ---
                    # If 'Type' is not provided, try to determine based on available stats
                    if not player_type:
                         # If 'control' is present and looks like a number, assume it's a Pitcher
                         if control_str and control_str.isdigit() and int(control_str) > 0: # Check if control is a positive number
                              player_type = 'P'
                         # If 'on base' is present and looks like a number, assume it's a Batter
                         elif onbase_str and onbase_str.isdigit() and int(onbase_str) > 0: # Check if onbase is a positive number
                              player_type = 'B'
                         else:
                              # If type cannot be determined, log a warning and skip the row
                              print(f"Warning: Could not determine player type for row {row_count} ({player_name}). Row data: {row}. Skipping row.")
                              continue


                    if player_type == 'B':
                        player = Batter(
                            name=player_name,
                            position=player_position_raw, # Store the raw position string from CSV
                            onbase=onbase,
                            so=so,
                            gb=gb, # Use the potentially defaulted gb value
                            fb=fb, # Use the mapped fb value
                            bb=bb,
                            b1=b1, # Use the mapped b1 value
                            b1p=b1p, # Use the mapped b1p value
                            b2=b2, # Use the mapped b2 value
                            b3=b3, # Use the mapped b3 value
                            hr=hr,
                            pts=pts
                        )
                        players.append(player)
                    elif player_type == 'P':
                         # Determine pitcher role more specifically from the raw position string
                         pitcher_role = 'P' # Default to generic P
                         # Check for full words "Starter", "Reliever", "Closer" case-insensitively
                         if 'STARTER' in player_position_raw.upper():
                             pitcher_role = 'SP'
                         elif 'RELIEVER' in player_position_raw.upper():
                             pitcher_role = 'RP'
                         elif 'CLOSER' in player_position_raw.upper():
                             pitcher_role = 'CL'

                         player = Pitcher(
                            name=player_name,
                            position=pitcher_role, # Store the determined role (SP, RP, CL, or P)
                            control=control,
                            pu=pu,
                            so=so,
                            gb=gb, # Use the potentially defaulted gb value (might not be relevant for pitchers if 'gb' is only in batter file)
                            fb=fb, # Use the mapped fb value
                            bb=bb,
                            b1=b1, # Use the mapped b1 value
                            b2=b2, # Use the mapped b2 value
                            hr=hr,
                            pts=pts,
                            ip_limit=ip_limit # Pass the IP limit (from 'ip' or 'IP Limit')
                        )
                         players.append(player)
                    else:
                        # This case should ideally not be reached with the type inference logic,
                        # but kept as a fallback.
                        print(f"Warning: Row {row_count} has unhandled player type '{player_type}' for player {player_name}. Row data: {row}. Skipping row.")

                except Exception as e:
                    # Catch any other unexpected errors during row processing
                    print(f"An unexpected error occurred while processing row {row_count} for player {row.get(header_map.get('name', 'Name'), 'Unknown')}: {e}. Row data: {row}. Skipping row.")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {filepath}")
        return None
    except Exception as e:
        # Catch errors related to opening or reading the file itself
        print(f"An unexpected error occurred while reading the CSV file {filepath}: {e}")
        return None

    return players

# Function to create a random team based on points and position requirements
def create_random_team(all_players, team_name, min_points, max_points):
    """
    Creates a random team (9 starters, 1 bench, 4 SP, 6 RP/CL) from a list of players,
    adhering to position requirements and total points limits.

    Args:
        all_players (list): A list of all available Batter and Pitcher objects.
        team_name (str): The name for the new team.
        min_points (int): The minimum total points for the team.
        max_points (int): The maximum total points for the team.

    Returns:
        Team or None: A randomly generated Team object or None if team creation fails.
    """
    # Separate players by type
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]

    # Separate pitchers by role
    available_sps = [p for p in available_pitchers if p.position == 'SP']
    available_rps_cls = [p for p in available_pitchers if p.position in ['RP', 'CL', 'P']] # Include generic P for RP/CL pool

    # Ensure enough players are available to even attempt team creation
    if len(available_batters) < 10 or len(available_sps) < 4 or len(available_rps_cls) < 6:
        print(f"Error: Not enough players available to form a team with the required roster size (10 Batters, 4 SP, 6 RP/CL).")
        print(f"Available Batters: {len(available_batters)}, Available SP: {len(available_sps)}, Available RP/CL/P: {len(available_rps_cls)}")
        return None


    # Attempt to create a valid team within the point range and roster size
    for attempt in range(1000): # Increased attempts
        selected_starters = []
        selected_bench = []
        selected_sps = []
        selected_rps = []
        selected_cls = []
        used_players = set() # Keep track of players already selected

        # --- Select Pitchers (exactly 4 SP and exactly 6 RP/CL) ---

        # Select Starting Pitchers (4)
        current_sps_pool = list(available_sps) # Create a mutable copy
        random.shuffle(current_sps_pool)
        for _ in range(4):
            if current_sps_pool:
                sp = current_sps_pool.pop(0)
                selected_sps.append(sp)
                used_players.add(sp)
            else:
                # Not enough dedicated SPs, team creation failed for this attempt
                break # Exit SP selection loop

        if len(selected_sps) < 4:
             continue # Not enough SPs selected, try again

        # Select Relievers and Closers (6 total)
        current_rps_cls_pool = [p for p in available_rps_cls if p not in used_players] # Pool of available RP/CL/P
        random.shuffle(current_rps_cls_pool)

        # Select 6 RP/CL from the available pool
        for _ in range(6):
             if current_rps_cls_pool:
                  rp_cl = current_rps_cls_pool.pop(0)
                  if rp_cl.position == 'CL':
                       selected_cls.append(rp_cl)
                  else: # Assumes 'RP' or 'P'
                       selected_rps.append(rp_cl)
                  used_players.add(rp_cl)
             else:
                  # Not enough RP/CL available
                  break # Exit RP/CL selection loop


        # Ensure exactly 6 RP/CL are selected
        if len(selected_rps) + len(selected_cls) != 6:
             continue # Incorrect number of RP/CL selected, try again


        # --- Select Batters (exactly 9 starters and exactly 1 bench) ---

        selected_starters_dict = {} # Use a dict to ensure one player per required position
        available_batters_for_selection = [b for b in available_batters if b not in used_players] # Batters not used as pitchers

        # Prioritize players with specific single positions first
        single_position_batters = [b for b in available_batters_for_selection if '/' not in b.position and b.position in STARTING_POSITIONS]
        multi_position_batters = [b for b in available_batters_for_selection if '/' in b.position or b.position not in STARTING_POSITIONS] # Includes OF, IF, etc.

        random.shuffle(single_position_batters)
        random.shuffle(multi_position_batters)

        # Try to fill required positions with single-position players first
        for required_pos in STARTING_POSITIONS:
            if required_pos not in selected_starters_dict:
                for batter in single_position_batters:
                    if batter not in used_players and batter.can_play(required_pos):
                        selected_starters_dict[required_pos] = batter
                        used_players.add(batter)
                        break # Move to the next required position

        # Fill remaining required positions with multi-position players
        for required_pos in STARTING_POSITIONS:
             if required_pos not in selected_starters_dict:
                  for batter in multi_position_batters:
                       if batter not in used_players and batter.can_play(required_pos):
                            selected_starters_dict[required_pos] = batter
                            used_players.add(batter)
                            break # Move to the next required position

        # If we don't have exactly 9 starters, team creation failed for this attempt
        if len(selected_starters_dict) != 9:
            continue # Not enough starters selected, try again

        # Convert the dictionary back to a list for the Team object, maintaining a consistent order (e.g., based on STARTING_POSITIONS)
        selected_starters = [selected_starters_dict[pos] for pos in STARTING_POSITIONS]


        # Select Bench Player (1) - any remaining batter not already used
        available_bench_batters = [b for b in available_batters_for_selection if b not in used_players]
        if available_bench_batters:
            # Ensure we only select one bench player
            selected_bench.append(random.choice(available_bench_batters))
            used_players.add(selected_bench[0]) # Add to used players
        else:
             # Not enough batters for bench, team creation failed
             continue # No bench player selected, try again

        # Ensure exactly 1 bench player is selected
        if len(selected_bench) != 1:
             continue # Incorrect number of bench players, try again


        # --- Final Roster Size Check ---
        total_batters_selected = len(selected_starters) + len(selected_bench)
        total_pitchers_selected = len(selected_sps) + len(selected_rps) + len(selected_cls)

        if total_batters_selected != 10 or total_pitchers_selected != 10:
             # This check should ideally not be needed if the selection logic above is correct,
             # but it's a good safeguard.
             print(f"DEBUG: Roster size mismatch. Batters: {total_batters_selected}, Pitchers: {total_pitchers_selected}. Expected 10 each.")
             continue # Roster size incorrect, try again


        # Calculate the total points of the selected team
        current_total_points = sum(p.pts for p in selected_starters + selected_bench + selected_sps + selected_rps + selected_cls)

        # Check if the team's total points are within the allowed range
        if min_points <= current_total_points <= max_points:
            print(f"Successfully created team {team_name} with {current_total_points} points.")
            return Team(team_name, selected_starters, selected_sps, selected_rps, selected_cls, selected_bench)
        else:
            # print(f"Attempt {attempt+1}: Team points {current_total_points} outside range [{min_points}, {max_points}]. Retrying...") # Keep this commented unless debugging point limits
            continue # Points outside range, try again

    print(f"Failed to create a valid team within the point range and roster requirements after {attempt+1} attempts.")
    return None # Return None if team creation failed after all attempts

