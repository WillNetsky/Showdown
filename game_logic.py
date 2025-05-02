# game_logic.py
# Contains the functions for simulating gameplay and displaying results.

import random
import math # Import math for floating point comparison

# Import necessary classes and constants from other modules
from entities import Batter, Pitcher, Team # Import Batter, Pitcher, and Team classes
from constants import POSITION_MAPPING, STARTING_POSITIONS, MIN_TEAM_POINTS, MAX_TEAM_POINTS

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
        # Ensure pitcher.out is calculated correctly in Pitcher class
        if roll <= pitcher.out:
            return "Out"
        else:
            # Calculate the cumulative ranges for hits and walks based on pitcher stats
            # Note: pitcher.out is the end of the Out range
            cumulative_range = pitcher.out
            if roll <= cumulative_range + pitcher.bb:
                return "BB"
            cumulative_range += pitcher.bb
            if roll <= cumulative_range + pitcher.b1:
                return "1B"
            cumulative_range += pitcher.b1
            if roll <= cumulative_range + pitcher.b2:
                return "2B"
            cumulative_range += pitcher.b2
            if roll <= cumulative_range + pitcher.hr:
                return "HR"

            # If the roll is higher than the cumulative range for defined results, it's an Out
            return "Out" # Default to Out if roll doesn't match any defined range

    else:
        # Use batter's chart
        # Determine the outcome based on the roll and batter's ranges
        # Ensure player.out is calculated correctly in Batter class
        if roll <= player.out:
            return "Out"
        else:
            # Calculate the cumulative ranges for hits and walks based on batter stats
            # Note: player.out is the end of the Out range
            cumulative_range = player.out
            if roll <= cumulative_range + player.bb:
                return "BB"
            cumulative_range += player.bb
            if roll <= cumulative_range + player.b1:
                return "1B"
            cumulative_range += player.b1
            if roll <= cumulative_range + player.b1p:
                return "1BP"
            cumulative_range += player.b1p
            if roll <= cumulative_range + player.b2:
                return "2B"
            cumulative_range += player.b2
            if roll <= cumulative_range + player.b3:
                return "3B"
            cumulative_range += player.b3
            if roll <= cumulative_range + player.hr:
                return "HR"

            # If the roll is higher than the cumulative range for defined results, it's an Out
            return "Out" # Default to Out if roll doesn't match any defined range


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
    good_pitch = pitch_result > batter.on_base # Corrected from batter.onbase to batter.on_base
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
        # Use the __str__ method for the runner's name to include year/set
        runner_names.append(f"1B: {runners[0].__str__().split(' |')[0]}") # Get info before the stats pipe
    if runners[1] is not None:
        # Use the __str__ method for the runner's name to include year/set
        runner_names.append(f"2B: {runners[1].__str__().split(' |')[0]}") # Get info before the stats pipe
    if runners[2] is not None:
        # Use the __str__ method for the runner's name to include year/set
        runner_names.append(f"3B: {runners[2].__str__().split(' |')[0]}") # Get info before the stats pipe
    runners_display = ", ".join(runner_names) if runner_names else "Bases Empty"

    # --- Construct the concise log entry ---
    # Get concise batter info (Name - YearSet (Pos, Pts))
    # Use the __str__ method and split to get the concise info
    concise_batter_info = batter.__str__().split(' |')[0]

    # Get concise pitcher info (Name - YearSet (Pos, Pts))
    # Use the __str__ method and split to get the concise info
    concise_pitcher_info = pitcher.__str__().split(' |')[0]


    # Include roll values and pitch quality in the log entry
    inning_log.append(f"{concise_batter_info} vs. {concise_pitcher_info} ({runners_display}) [Pitch Roll: {pitch_result} ({pitch_quality_text}), Swing Roll: {swing_roll}]: {result}")

    # Update stats and runners based on the result
    if result == "Out":
        batter.outs += 1
        # --- CORRECTED: Use outs_recorded instead of total_outs_pitched ---
        pitcher.outs_recorded += 1
        # --- END CORRECTED ---
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
            # Calculate runs scored on the HR based on who was on base + the batter
            runs_scored_on_hr = sum(1 for r in runners if r is not None) + 1
            pitcher.runs_allowed += runs_scored_on_hr
            pitcher.earned_runs_allowed += runs_scored_on_hr # Assuming all runs are earned for simplicity
            # Update runs_scored for the batter and runners who scored
            if isinstance(batter, Batter):
                batter.runs_scored += 1
            for runner in runners:
                if isinstance(runner, Batter):
                    runner.runs_scored += 1
            runs_scored += runs_scored_on_hr
            new_runners = [None, None, None] # Bases clear on a HR

        # Note: handle_base_hit is called for all hits (including HR in previous versions),
        # but for 1B, 1BP, 2B, 3B, we still need to call handle_base_hit to move runners.
        # HR is handled separately above for scoring and clearing bases.
        if result in ["1B", "1BP", "2B", "3B"]:
             runs_scored_on_play, new_runners = handle_base_hit(runners, result, batter)
             runs_scored += runs_scored_on_play # Add runs from base advancement


    else:
        # Handle unexpected results as outs for now
        inning_log.append(f"Warning: Unhandled result '{result}' for {batter.name}. Treating as Out.")
        result = "Out"
        batter.outs += 1
        # --- CORRECTED: Use outs_recorded instead of total_outs_pitched ---
        pitcher.outs_recorded += 1
        # --- END CORRECTED ---
        # IP is updated in play_inning based on outs

    # Update RBI for the batter who drove in runs
    if runs_scored > 0:
        batter.rbi += runs_scored
        # Note: Runs allowed and earned runs for the pitcher are handled in handle_base_hit
        # and the HR block. Avoid double counting here.


    return result, runs_scored, new_runners

def play_inning(batting_team: Team, pitching_team: Team, inning_number, game_log, half_inning, game_state):
    """
    Simulates a single inning of a game.

    Args:
        batting_team (Team): The batting team object.
        pitching_team (Team): The pitching team object.
        inning_number (int): The current inning number.
        game_log (list): A list to store the game log.
        half_inning (str): "Top" or "Bottom".
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

        # --- Check for Walk-Off ---
        # If it's the bottom of the 9th or later, and the home team (batting_team) takes the lead
        if half_inning == "Bottom" and inning_number >= 9:
            # Calculate the potential score if the current runs scored are added
            batting_team_potential_score = game_state[batting_team.name] + runs_scored_this_inning
            pitching_team_current_score = game_state[pitching_team.name]

            if batting_team_potential_score > pitching_team_current_score:
                inning_log.append(f"Walk-Off {result}!")
                # Update the game state with the runs scored *before* ending the inning
                game_state[batting_team.name] += runs_scored_this_inning
                runs_scored_this_inning = 0 # Reset runs for the inning as they've been added to game_state
                break # End the inning immediately on a walk-off


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
    # Only add runs_scored_this_inning to game_state here if it wasn't a walk-off
    # In a walk-off, runs were added to game_state within the walk-off check
    if not (half_inning == "Bottom" and inning_number >= 9 and game_state[batting_team.name] > game_state[pitching_team.name]):
         game_state[batting_team.name] += runs_scored_this_inning


    game_log.extend(inning_log) #add inning log to game log
    return runs_scored_this_inning # Return the runs scored in this segment of the inning

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
        team1 (Team): The first team object (Away).
        team2 (Team): The second team object (Home).
        num_innings (int, optional): The number of innings to play initially. Defaults to 9.

    Returns:
        tuple: (score1, score2, game_log, team1_inning_runs, team2_inning_runs) -
               The final scores, game log, and lists of runs scored per inning for each team.
    """
    game_state = {
        team1.name: 0,
        team2.name: 0
    }
    game_log = []
    current_inning = 1

    # Lists to store runs scored per inning for the linescore
    team1_inning_runs = []
    team2_inning_runs = []

    game_log.append(f"--- Game Start: {team1.name} vs. {team2.name} ---")

    # Set the initial starting pitchers for each team
    if team1.starters:
        team1.current_pitcher = team1.starters[0]
        # Ensure used_starters is initialized (should be in Team.__init__)
        if not hasattr(team1, 'used_starters'):
             team1.used_starters = []
        team1.used_starters.append(team1.current_pitcher)
    else:
        game_log.append(f"Warning: {team1.name} has no starting pitchers.")
        team1.current_pitcher = None # Ensure it's None if no SPs

    if team2.starters:
        team2.current_pitcher = team2.starters[0]
        # Ensure used_starters is initialized (should be in Team.__init__)
        if not hasattr(team2, 'used_starters'):
             team2.used_starters = []
        team2.used_starters.append(team2.current_pitcher)
    else:
         game_log.append(f"Warning: {team2.name} has no starting pitchers.")
         team2.current_pitcher = None # Ensure it's None if no SPs


    # --- Modified game loop for extra innings and collecting inning scores ---
    game_over = False
    while not game_over:
        # Top of the inning: Team 1 bats, Team 2 pitches
        runs_team1_this_inning = play_inning(team1, team2, current_inning, game_log, "Top", game_state)
        team1_inning_runs.append(runs_team1_this_inning) # Record runs for the inning

        # Check for game end after the top of the 9th or later if the away team is ahead
        if current_inning >= num_innings and game_state[team1.name] > game_state[team2.name]:
            game_log.append(f"--- Game End: {team1.name} {game_state[team1.name]} - {team2.name} {game_state[team2.name]} ---")
            game_over = True
            # Add 0 runs for the bottom of the inning if it wasn't played
            team2_inning_runs.append(0)
            break # End the game

        # Bottom of the inning: Team 2 bats, Team 1 pitches
        # Only play the bottom of the inning if the game is not already over
        # AND (it's before the 9th inning OR the score is tied OR the home team is trailing)
        runs_team2_this_inning = 0 # Initialize runs for the bottom half
        if not game_over and (current_inning < num_innings or game_state[team2.name] <= game_state[team1.name]):
             runs_team2_this_inning = play_inning(team2, team1, current_inning, game_log, "Bottom", game_state)
        team2_inning_runs.append(runs_team2_this_inning) # Record runs for the inning


        # Check for game end after the bottom of the inning
        # Game ends if 9 innings are complete AND the score is NOT tied
        # OR if a walk-off occurred in the bottom of the 9th or later (handled within play_inning)
        if current_inning >= num_innings and game_state[team1.name] != game_state[team2.name]:
             # Check if the last entry in the log was NOT a walk-off before adding the game end message
             if not game_log or not game_log[-1].startswith("Walk-Off"):
                 game_log.append(f"--- Game End: {team1.name} {game_state[team1.name]} - {team2.name} {game_state[team2.name]} ---")
             game_over = True
             break # End the game

        # If the game is still tied after the bottom of the 9th or later, continue to the next inning
        if current_inning >= num_innings and game_state[team1.name] == game_state[team2.name]:
            game_log.append(f"--- Score tied {game_state[team1.name]}-{game_state[team2.name]} after {current_inning} innings. Going to extra innings. ---")
            current_inning += 1
            continue # Continue to the next inning

        # If 9 innings are complete and the home team is winning, the game is over
        # This case should be covered by the walk-off check in play_inning for the bottom of the 9th or later.
        # However, as a safeguard, explicitly check here too.
        if current_inning >= num_innings and game_state[team2.name] > game_state[team1.name]:
             game_log.append(f"--- Game End: {team1.name} {game_state[team1.name]} - {team2.name} {game_state[team2.name]} ---")
             game_over = True
             break # End the game


        # If 9 innings haven't been reached yet, just increment the inning
        if current_inning < num_innings:
             current_inning += 1
             continue # Continue to the next inning

        # Fallback to end the game if none of the above conditions were met (shouldn't happen with correct logic)
        if not game_over:
             game_log.append(f"--- Game End (Fallback): {team1.name} {game_state[team1.name]} - {team2.name} {game_state[team2.name]} ---")
             game_over = True


    return game_state[team1.name], game_state[team2.name], game_log, team1_inning_runs, team2_inning_runs

def display_linescore(team1_name, team2_name, team1_inning_runs, team2_inning_runs, final_score1, final_score2):
    """
    Prints a formatted linescore for the game.

    Args:
        team1_name (str): Name of the first team (Away).
        team2_name (str): Name of the second team (Home).
        team1_inning_runs (list): List of runs scored by team1 in each inning.
        team2_inning_runs (list): List of runs scored by team2 in each inning.
        final_score1 (int): Final score for team1.
        final_score2 (int): Final score for team2.
    """
    print("\n--- Linescore ---")

    # Determine the maximum number of innings played
    max_innings = max(len(team1_inning_runs), len(team2_inning_runs))

    # Determine the max team name length
    max_team_length = max(len(team1_name), len(team2_name))

    # Create the header row
    header = ["Team"+" "*(max_team_length-4)] + [str(i + 1) for i in range(max_innings)] + ["R", "H"] # Add H column placeholder
    print(" | ".join(header))
    print("-" * (len(" | ".join(header)) + 2)) # Separator line

    # Print Team 1 (Away) row
    team1_row = [team1_name] + [str(runs) for runs in team1_inning_runs]
    # Pad with empty strings if fewer than max_innings
    team1_row += [""] * (max_innings - len(team1_inning_runs))
    team1_row += [str(final_score1), "?"] # Add R and H (H is placeholder for now)
    print(" | ".join(team1_row))

    # Print Team 2 (Home) row
    team2_row = [team2_name] + [str(runs) for runs in team2_inning_runs]
    # Pad with empty strings if fewer than max_innings
    team2_row += [""] * (max_innings - len(team2_inning_runs))
    team2_row += [str(final_score2), "?"] # Add R and H (H is placeholder for now)
    print(" | ".join(team2_row))
    print("-" * (len(" | ".join(header)) + 2)) # Separator line


def display_boxscore(team: Team):
    """
    Prints a formatted boxscore for a given team.

    Args:
        team (Team): The Team object to display the boxscore for.
    """
    print(f"\n--- {team.name} Boxscore ---")

    # Batting Stats Header
    # Added OPS+ column placeholder
    print("\nBatting:")
    # Adjusted spacing for batting stats
    print(f"{'Name':<20} {'Pos':<5} {'PA':<3} {'AB':<3} {'R':<3} {'H':<3} {'RBI':<3} {'BB':<3} {'SO':<3} {'AVG':<5} {'OBP':<5} {'SLG':<5} {'OPS':<5}")
    print("-" * 79) # Adjusted separator length

    # Display Batting Stats for Starters and Bench
    for player in team.batters + team.bench:
        # Calculate derived stats
        avg = player.calculate_avg()
        obp = player.calculate_obp()
        slg = player.calculate_slg()
        ops = player.calculate_ops()

        # Format and print batting stats
        print(f"{player.name:<20} {player.position:<5} {player.plate_appearances:<3} {player.at_bats:<3} {player.runs_scored:<3} {player.hits:<3} {player.rbi:<3} {player.walks:<3} {player.strikeouts:<3} {avg:<5.3f} {obp:<5.3f} {slg:<5.3f} {ops:<5.3f}")

    # Pitching Stats Header
    print("\nPitching:")
    # Adjusted spacing for pitching stats
    print(f"{'Name':<20} {'Role':<5} {'IP':<5} {'BF':<4} {'R':<3} {'ER':<3} {'H':<3} {'BB':<3} {'SO':<3} {'ERA':<5} {'WHIP':<5}")
    print("-" * 70) # Adjusted separator length

    # Display Pitching Stats for all Pitchers
    for pitcher in team.all_pitchers:
        # Calculate derived stats
        era = pitcher.calculate_era()
        whip = pitcher.calculate_whip()
        formatted_ip = pitcher.get_formatted_ip() # Use the formatted IP

        # Format and print pitching stats
        print(f"{pitcher.name:<20} {pitcher.team_role:<5} {formatted_ip:<5} {pitcher.batters_faced:<4} {pitcher.runs_allowed:<3} {pitcher.earned_runs_allowed:<3} {pitcher.hits_allowed:<3} {pitcher.walks_allowed:<3} {pitcher.strikeouts_thrown:<3} {era:<5.2f} {whip:<5.2f}")

