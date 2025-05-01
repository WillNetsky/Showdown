# test_at_bats.py
# Script to test the get_chart_result function by simulating at-bats
# between a random batter and a random pitcher for ALL possible dice combinations.

import random
import os # Needed to check for CSV file existence

# Import necessary functions and classes from your project files
from team_management import load_players_from_csv
from entities import Batter, Pitcher
from game_logic import get_chart_result # Only need get_chart_result, roll_dice is not used for exhaustive test

# Assume CSV files are in the same directory or a known path
BATTERS_FILE = '../all_batters.csv'
PITCHERS_FILE = '../all_pitchers.csv'

def main():
    """
    Loads players, selects random batter and pitcher, and simulates at-bats
    for all possible pitch and swing roll combinations.
    Prints full object information for selected players.
    """
    print("Loading player data for testing...")

    # Check if CSV files exist
    if not os.path.exists(BATTERS_FILE):
        print(f"Error: Batter data file not found at {BATTERS_FILE}")
        return
    if not os.path.exists(PITCHERS_FILE):
        print(f"Error: Pitcher data file not found at {PITCHERS_FILE}")
        return

    # Load all players
    all_players = []
    batters_list = load_players_from_csv(BATTERS_FILE)
    pitchers_list = load_players_from_csv(PITCHERS_FILE)

    if batters_list is None or pitchers_list is None:
        print("Failed to load player data. Cannot run test.")
        return

    all_players.extend(batters_list)
    all_players.extend(pitchers_list)

    # Filter for only Batter and Pitcher objects
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]

    # Ensure there are players to select
    if not available_batters:
        print("Error: No batters found in the data.")
        return
    if not available_pitchers:
        print("Error: No pitchers found in the data.")
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
        pitch_control_sum = pitch_roll + test_pitcher.control

        # Determine if it's a "good" or "bad" pitch for this pitch_control_sum
        # Note: Using test_batter.on_base as the threshold
        good_pitch = pitch_control_sum > test_batter.on_base
        pitch_quality_text = "Good Pitch" if good_pitch else "Bad Pitch"

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
