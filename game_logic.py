# game_logic.py
# Contains the functions for simulating gameplay.

import random

# Import necessary classes and constants from other modules
from entities import Batter, Pitcher
from team import Team # Team class is still needed here for type hinting and object creation
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
        good_pitch (bool): True if the pitch was "good" (pitch_roll + pitcher.control > batter.on_base), False if "bad).

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
            # Corrected cumulative range calculations - should add the range value, not the cumulative range itself
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
            # Corrected cumulative range calculations - should add the range value, not the cumulative range itself
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


# Define play_ball before play_inning
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
    pitch_roll = roll_dice(1, 20)

    # Calculate pitch + control sum
    pitch_control_sum = pitch_roll + pitcher.control

    # Determine if it's a "good" or "bad" pitch based on the pitch_control_sum and the batter's On-Base number
    good_pitch = pitch_control_sum > batter.on_base
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
    inning_log.append(f"{concise_batter_info} vs. {concise_pitcher_info} ({runners_display}) [Pitch Roll: {pitch_roll:2d}, Pitcher Control: {pitcher.control}, Pitch+Control: {pitch_control_sum}, Swing Roll: {swing_roll:2d} -> {pitch_quality_text}]: {result}")

    # Update stats and runners based on the result
    if result == "Out":
        batter.at_bats += 1 # An out counts as an at-bat
        batter.outs += 1 # Total outs recorded by this batter (for game flow)
        pitcher.outs_recorded += 1
        # Check if the out was a strikeout
        # This is a simplification; in real baseball, SO is a type of out.
        # Here, we'll assume if the swing roll was <= batter.so (or pitcher.so if good pitch), it's a K.
        # Need to refine this based on the chart logic. For now, let's just check the roll against the SO range end.
        # This is a bit simplified and might not perfectly match actual chart outcomes if SO range overlaps with other outs.
        # A more accurate way would be to have get_chart_result return the *type* of out (SO, GB, FB, PU).
        # For now, let's use a simple check:
        if good_pitch:
             # If the swing roll is within the pitcher's SO range (1 to pitcher.so)
             if swing_roll >= 1 and swing_roll <= pitcher.so:
                  batter.strikeouts += 1
                  pitcher.strikeouts_thrown += 1
        else: # Bad pitch, use batter's chart
             # If the swing roll is within the batter's SO range (1 to batter.so)
             if swing_roll >= 1 and swing_roll <= batter.so:
                  batter.strikeouts += 1
                  pitcher.strikeouts_thrown += 1


        # IP is updated at the end of the inning in play_inning
    elif result == "BB":
        batter.plate_appearances += 1 # Walks are plate appearances, not at-bats
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
            batter.home_runs += 1 # Increment batter's HR count
            pitcher.home_runs_allowed += 1 # Increment pitcher's HR allowed count
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
        batter.at_bats += 1 # Treat as an at-bat ending in an out
        batter.outs += 1
        pitcher.outs_recorded += 1
        # IP is updated at the end of the inning in play_inning


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
    current_pitcher = pitching_team.current_pitcher

    # Check for pitching change at the START of the inning if the current pitcher
    # is None (e.g., first inning and no initial SP found) or if they finished
    # the *previous* inning having exceeded their IP limit.
    if current_pitcher is None or (current_pitcher.ip_limit is not None and current_pitcher.innings_pitched >= current_pitcher.ip_limit):
        if current_pitcher is not None: # Only log if a pitcher is being replaced due to limit
             inning_log.append(f"Pitching Change: {current_pitcher.name} ({current_pitcher.innings_pitched:.1f} IP) reached IP limit and is replaced at the start of the inning.")
        # Call handle_pitching_change to get the next eligible pitcher
        new_pitcher = handle_pitching_change(pitching_team, inning_number, inning_log)
        # If handle_pitching_change returns None, the inning cannot continue
        if new_pitcher is None:
             inning_log.append("Error: No pitcher available to start inning.")
             game_log.extend(inning_log)
             return 0 # No runs scored if no pitcher
        else:
             pitching_team.current_pitcher = new_pitcher # Set the new pitcher


    # Ensure we have a pitcher before starting the at-bats loop
    pitcher = pitching_team.current_pitcher
    if pitcher is None:
         inning_log.append("Error: No pitcher available to continue inning after attempted change.")
         game_log.extend(inning_log)
         return 0 # No runs scored if no pitcher


    while outs < 3:
        # Get the next batter from the batting team
        current_batter = batting_team.get_next_batter()

        # --- Removed the mid-inning pitching change check ---
        # Pitchers will now only be changed at the start of an inning if they
        # finished the previous inning over their IP limit, or if there was no
        # pitcher to start the inning.

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
                # Store the runs scored on this final play before updating game_state and resetting
                walk_off_runs = runs_scored_this_inning
                # Update the game state with the runs scored *before* ending the inning
                game_state[batting_team.name] += runs_scored_this_inning
                runs_scored_this_inning = 0 # Reset runs for the inning as they've been added to game_state
                # Use the stored walk_off_runs for the end-of-inning log message
                inning_log.append(f"End of {half_inning} {inning_number}, {walk_off_runs} run(s) scored.")
                # Add current score after the walk-off message
                inning_log.append(f"Current Score: {list(game_state.keys())[0]} {list(game_state.values())[0]} - {list(game_state.keys())[1]} {list(game_state.values())[1]}")
                game_log.extend(inning_log) # Add inning log to game log
                return walk_off_runs # Return the runs scored on the walk-off play


        # Outs are incremented here
        if result == "Out":
            outs += 1
        elif result == "Error": # Handle errors from play_ball
             outs += 1 # Treat unknown results as outs for now


    # --- Increment Pitcher IP at the END of the inning ---
    # The pitcher who finished the inning gets +1 IP
    # Only increment if the inning completed (3 outs) or ended due to walk-off
    if pitching_team.current_pitcher is not None and (outs == 3 or (half_inning == "Bottom" and inning_number >= 9 and game_state[batting_team.name] > game_state[pitching_team.name])):
        # Calculate innings pitched: outs_recorded / 3.0
        # This is a more accurate way to track fractional innings.
        # 1 out = 0.1 IP, 2 outs = 0.2 IP, 3 outs = 1.0 IP
        # Need to add the outs recorded in this half-inning to the pitcher's total outs.
        # The pitcher's outs_recorded is already incremented in play_ball.
        # So, at the end of the inning, calculate IP based on total outs recorded.
        # This logic needs to be applied carefully to avoid double-counting outs across innings.
        # A simpler approach for now is to just add 1.0 IP if 3 outs were recorded in this half-inning.
        # Let's stick to adding 1.0 IP for a completed inning for simplicity with the current IP limit logic.
        pitching_team.current_pitcher.innings_pitched += 1.0
        # Round to one decimal place for display
        pitching_team.current_pitcher.innings_pitched = round(pitching_team.current_pitcher.innings_pitched, 1)


    # Add the standard end-of-inning log message (only if not a walk-off)
    # The walk-off case is handled above and returns early after logging its specific message.
    if not (half_inning == "Bottom" and inning_number >= 9 and game_state[batting_team.name] > game_state[pitching_team.name]):
        inning_log.append(f"End of {half_inning} {inning_number}, {runs_scored_this_inning} run(s) scored.")
        # Only add runs_scored_this_inning to game_state here if it wasn't a walk-off
        # In a walk-off, runs were added to game_state within the walk-off check
        game_state[batting_team.name] += runs_scored_this_inning

    # Add the current score at the end of each half-inning
    # Assuming game_state keys are always in the order [away_team_name, home_team_name]
    inning_log.append(f"Current Score: {list(game_state.keys())[0]} {list(game_state.values())[0]} - {list(game_state.keys())[1]} {list(game_state.values())[1]}")


    game_log.extend(inning_log) #add inning log to game log
    return runs_scored_this_inning # Return the runs scored in this segment of the inning

def handle_pitching_change(pitching_team: Team, inning_number, inning_log):
    """
    Handles the logic for a pitching change, selecting the next available pitcher
    based on the SP -> RP -> CL hierarchy and inning number rules.

    Args:
        pitching_team (Team): The team needing a pitching change.
        inning_number (int): The current inning number (1-based).
        inning_log (list): The log for the current inning.

    Returns:
        Pitcher or None: The new current pitcher, or None if no available pitchers.
    """
    next_pitcher = None

    # Before changing pitchers, update the IP for the pitcher who just finished.
    # This is crucial for respecting IP limits for pitchers removed mid-inning.
    # The pitcher who was pitching before the change gets credit for the partial inning.
    # This logic needs to be added here.

    # --- IP Update for Pitcher Being Replaced (Mid-Inning) ---
    # If a pitcher is being replaced *mid-inning* (i.e., outs < 3 when this function is called)
    # they should get credit for the outs they recorded in this inning segment.
    # This is complex with the current play_inning structure where outs are tracked locally.
    # For simplicity with the current IP limit logic (which seems to be based on full innings),
    # let's defer the IP update to the end of play_inning for the pitcher who finishes the inning.
    # The pitcher replaced mid-inning doesn't get IP credit here with the current simple model.
    # This is a known simplification.

    if inning_number == 1:
        # In the first inning, only a starter can enter (if the initial one was replaced)
        next_pitcher = pitching_team.get_available_starter()
        if next_pitcher:
             # Mark the starter as used if they are indeed a starter
             if next_pitcher not in pitching_team.used_starters:
                  pitching_team.used_starters.append(next_pitcher)
             inning_log.append(f"Pitching Change: {next_pitcher.name} enters the game (Starter).")
        else:
             # If no starters available even in the 1st, try a reliever/closer
             next_pitcher = pitching_team.get_available_relief_pitcher()
             if next_pitcher:
                  if next_pitcher.position == 'CL':
                       if next_pitcher not in pitching_team.used_closers:
                            pitching_team.used_closers.append(next_pitcher)
                       inning_log.append(f"Pitching Change: {next_pitcher.name} enters the game (Closer) - No starters available.")
                  else: # Assumes 'RP' or 'P'
                       if next_pitcher not in pitching_team.used_relievers:
                            pitching_team.used_relievers.append(next_pitcher)
                       inning_log.append(f"Pitching Change: {next_pitcher.name} enters the game (Reliever) - No starters available.")


    else:
        # After the first inning, only relievers or closers can enter
        next_pitcher = pitching_team.get_available_relief_pitcher()
        if next_pitcher:
             if next_pitcher.position == 'CL':
                  if next_pitcher not in pitching_team.used_closers:
                       pitching_team.used_closers.append(next_pitcher)
                  inning_log.append(f"Pitching Change: {next_pitcher.name} enters the game (Closer).")
             else: # Assumes 'RP' or 'P'
                  if next_pitcher not in pitching_team.used_relievers:
                       pitching_team.used_relievers.append(next_pitcher)
                  inning_log.append(f"Pitching Change: {next_pitcher.name} enters the game (Reliever).")


    if next_pitcher is None:
        inning_log.append("Error: No available pitchers for pitching change.")


    return next_pitcher


def play_game(away_team: Team, home_team: Team, num_innings=9):
    """
    Simulates a complete game between two teams.

    Args:
        away_team (Team): The away team object.
        home_team (Team): The home team object.
        num_innings (int, optional): The number of innings to play. Defaults to 9.

    Returns:
        tuple: (away_score, home_score, game_log, away_inning_runs, home_inning_runs, away_total_hits, home_total_hits, away_total_errors, home_total_errors)
               - The final scores, game log, runs scored per inning for each team, total hits, and total errors.
    """
    game_state = {
        away_team.name: 0,
        home_team.name: 0
    }
    game_log = []
    current_inning = 1
    game_over = False

    # Lists to store runs scored per inning for the linescore
    away_inning_runs = []
    home_inning_runs = []

    # Initialize total errors (errors are not implemented in play-by-play yet)
    away_total_errors = 0 # Placeholder for now
    home_total_errors = 0 # Placeholder for now


    game_log.append(f"--- Game Start: {away_team.name} vs. {home_team.name} ---")

    # Set the initial starting pitchers for each team
    initial_sp_away = away_team.get_available_starter()
    if initial_sp_away:
         away_team.current_pitcher = initial_sp_away
         game_log.append(f"{away_team.name}'s starting pitcher: {initial_sp_away.name}")
    else:
        game_log.append(f"Warning: {away_team.name} has no available starting pitcher. Attempting to use a reliever/closer.")
        initial_rp_cl_away = away_team.get_available_relief_pitcher()
        if initial_rp_cl_away:
             away_team.current_pitcher = initial_rp_cl_away
             if initial_rp_cl_away.position == 'CL':
                 if initial_rp_cl_away not in away_team.used_closers:
                      away_team.used_closers.append(initial_rp_cl_away)
             else: # Assumes 'RP' or 'P'
                 if initial_rp_cl_away not in away_team.used_relievers:
                      away_team.used_relievers.append(initial_rp_cl_away)
             game_log.append(f"{away_team.name}'s starting pitcher (relief): {initial_rp_cl_away.name}")
        else:
             game_log.append(f"Error: {away_team.name} has no available pitchers to start the game.")
             away_team.current_pitcher = None


    initial_sp_home = home_team.get_available_starter()
    if initial_sp_home:
         home_team.current_pitcher = initial_sp_home
         game_log.append(f"{home_team.name}'s starting pitcher: {initial_sp_home.name}")
    else:
         game_log.append(f"Warning: {home_team.name} has no available starting pitcher. Attempting to use a reliever/closer.")
         initial_rp_cl_home = home_team.get_available_relief_pitcher()
         if initial_rp_cl_home:
              home_team.current_pitcher = initial_rp_cl_home
              if initial_rp_cl_home.position == 'CL':
                  if initial_rp_cl_home not in home_team.used_closers:
                       home_team.used_closers.append(initial_rp_cl_home)
              else: # Assumes 'RP' or 'P'
                  if initial_rp_cl_home not in home_team.used_relievers:
                       home_team.used_relievers.append(initial_rp_cl_home)
              game_log.append(f"{home_team.name}'s starting pitcher (relief): {initial_rp_cl_home.name}")
         else:
              game_log.append(f"Error: {home_team.name} has no available pitchers to start the game.")
              home_team.current_pitcher = None


    # Use a while loop for innings to handle extra innings
    while not game_over:
        # Top of the inning: Away Team bats, Home Team pitches
        runs_away_this_inning = play_inning(away_team, home_team, current_inning, game_log, "Top", game_state)
        away_inning_runs.append(runs_away_this_inning) # Store runs for the linescore

        # Check if the game is over after the top of the 9th or later
        # The game ends if it's the 9th inning or later AND the home team is leading.
        if current_inning >= num_innings and game_state[home_team.name] > game_state[away_team.name]:
             game_log.append(f"--- Game End: {away_team.name} {game_state[away_team.name]} - {home_team.name} {game_state[home_team.name]} ---\n") # Added newline for clarity
             game_over = True
             # Since the game ended in the top of an extra inning, the home team didn't bat in the bottom.
             # Add a placeholder (0 runs) for the home team in this inning for the linescore.
             home_inning_runs.append(0)
             break # End the game

        # Bottom of the inning: Home Team bats, Away Team pitches
        # Only play bottom of the inning if the game is not over after the top half
        # AND (it's before the 9th OR (it's the 9th or later AND the home team is NOT winning))
        # The condition `not game_over` is crucial here.
        if not game_over and (current_inning < num_innings or (current_inning >= num_innings and game_state[home_team.name] <= game_state[away_team.name])):
             runs_home_this_inning = play_inning(home_team, away_team, current_inning, game_log, "Bottom", game_state)
             home_inning_runs.append(runs_home_this_inning) # Store runs for the linescore

        # Check for game over after the bottom of the inning
        # Game is over if 9+ innings are complete AND the scores are NOT tied.
        # This check is still needed for games that go into extra innings and the home team wins in the bottom half.
        if current_inning >= num_innings and game_state[away_team.name] != game_state[home_team.name]:
             # Check if the last entry in the log was NOT a walk-off before adding the game end message
             if not game_log or not game_log[-1].startswith("Walk-Off"):
                 game_log.append(f"--- Game End: {away_team.name} {game_state[away_team.name]} - {home_team.name} {game_state[home_team.name]} ---\n") # Added newline for clarity
             game_over = True # Set game_over flag to True
             break # End the game loop

        # If the game is not over, increment the inning
        if not game_over:
             current_inning += 1


    # Calculate total hits for each team by summing hits from all batters
    away_total_hits = sum(b.singles + b.doubles + b.triples + b.home_runs for b in away_team.batters + away_team.bench)
    home_total_hits = sum(b.singles + b.doubles + b.triples + b.home_runs for b in home_team.batters + home_team.bench)

    # Total errors are placeholders for now as error logic is not implemented
    away_total_errors = 0
    home_total_errors = 0


    # The loop finishes when game_over is True. The final score is already in game_state.
    # The game end message is added either by a walk-off or the check after the bottom of the inning.
    # No need for a fallback game end message here.

    return game_state[away_team.name], game_state[home_team.name], game_log, away_inning_runs, home_inning_runs, away_total_hits, home_total_hits, away_total_errors, home_total_errors
