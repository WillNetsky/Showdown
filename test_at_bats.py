# test_at_bats.py
# Script to test the get_chart_result function by simulating at-bats
# between a random batter and a random pitcher for ALL possible dice combinations.
# Updated to load player data from all_players.json.

import random
import os # Needed to check for file existence

# Import necessary functions and classes from your project files
# Import load_players_from_json from team_management
from team_management import load_players_from_json
from entities import Batter, Pitcher
from game_logic import get_chart_result # Only need get_chart_result, roll_dice is not used for exhaustive test

# Define the path to the JSON player data file
PLAYERS_FILE_JSON = 'all_players.json'

def main():
    """
    Loads players from JSON, selects random batter and pitcher, and simulates at-bats
    for all possible pitch and swing roll combinations.
    Prints full object information for selected players.
    """
    print("Loading player data from JSON for testing...")

    # Define the directory containing the data file
    data_dir = os.path.dirname(os.path.abspath(__file__))
    players_filepath_json = os.path.join(data_dir, PLAYERS_FILE_JSON)


    # Check if the JSON file exists
    if not os.path.exists(players_filepath_json):
        print(f"Error: Player data file not found at {players_filepath_json}")
        print("Please run convert_csv_to_json.py first to create this file.")
        return

    # Load all players from the JSON file
    all_players = load_players_from_json(players_filepath_json)

    if not all_players:
        print("No player data loaded from JSON. Cannot run test.")
        return

    # Filter for only Batter and Pitcher objects
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]

    # Ensure there are players to select
    if not available_batters:
        print("Error: No batters found in the loaded data.")
        return
    if not available_pitchers:
        print("Error: No pitchers found in the loaded data.")
        return

    # Select a random batter and pitcher
    test_batter = random.choice(available_batters)
    test_pitcher = random.choice(available_pitchers)

    # Print the full object information for the selected players
    print(f"\nSelected Batter Object:")
    print(repr(test_batter))
    print(f"\nSelected Pitcher Object:")
    print(repr(test_pitcher))


    print("\nTesting get_chart_result for all 400 pitch/swing roll combinations...")

    # Simulate all possible pitch roll (1-20) and swing roll (1-20) combinations
    at_bat_count = 0
    for pitch_roll in range(1, 21):
        # Calculate pitch + control sum
        # Ensure test_pitcher is not None before accessing control
        if test_pitcher:
            pitch_control_sum = pitch_roll + test_pitcher.control
        else:
            print("Error: Test pitcher is None.")
            return # Exit if no pitcher was selected

        # Determine if it's a "good" or "bad" pitch for this pitch_control_sum
        # Note: Using test_batter.on_base as the threshold
        # Ensure test_batter is not None before accessing on_base
        if test_batter:
            good_pitch = pitch_control_sum > test_batter.on_base
            pitch_quality_text = "Good Pitch" if good_pitch else "Bad Pitch"
        else:
             print("Error: Test batter is None.")
             return # Exit if no batter was selected


        for swing_roll in range(1, 21):
            at_bat_count += 1

            # Get the result using the get_chart_result function
            # get_chart_result only needs swing_roll, player, pitcher, good_pitch
            result = get_chart_result(swing_roll, test_batter, test_pitcher, good_pitch)

            # Print the details of the plate appearance, including On-Base, Control, rolls, and result
            print(f"Test {at_bat_count:3d}: Batter OB: {test_batter.on_base}, Pitcher Control: {test_pitcher.control}, Pitch Roll: {pitch_roll:2d}, Pitch+Control: {pitch_control_sum:2d} ({pitch_quality_text}), Swing Roll: {swing_roll:2d} -> Result: {result}")

    print("\nExhaustive chart test complete.")

if __name__ == "__main__":
    main()
