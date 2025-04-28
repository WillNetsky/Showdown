# main.py
# Entry point for the baseball simulation.

import os
import glob
from team_management import load_players_from_csv, create_random_team
from game_logic import play_game
from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS

def main():
    """
    Main function to load players, create teams, and simulate a game.
    """
    print("Loading player data...")
    # Load batters and pitchers from their respective CSV files
    all_players = []
    batter_files = glob.glob('all_batters.csv') # Use glob to find the file
    pitcher_files = glob.glob('all_pitchers.csv') # Use glob to find the file

    if not batter_files:
        print("Error: 'all_batters.csv' not found.")
        return # Exit if batter file is not found
    if not pitcher_files:
        print("Error: 'all_pitchers.csv' not found.")
        return # Exit if pitcher file is not found


    # Assuming only one file each for batters and pitchers based on previous usage
    batters_list = load_players_from_csv(batter_files[0])
    pitchers_list = load_players_from_csv(pitcher_files[0])

    if batters_list is None or pitchers_list is None:
        print("Failed to load player data. Exiting.")
        return # Exit if loading failed

    all_players.extend(batters_list)
    all_players.extend(pitchers_list)

    print("Creating teams...")
    # Create two random teams within the specified point range
    team1 = create_random_team(all_players, "Home Team", MIN_TEAM_POINTS, MAX_TEAM_POINTS)
    team2 = create_random_team(all_players, "Away Team", MIN_TEAM_POINTS, MAX_TEAM_POINTS)

    if team1 and team2:
        print("\nTeams created successfully. Simulating game...")
        # Simulate a game between the two teams
        final_score1, final_score2, game_log = play_game(team1, team2)

        print("\n--- Game Log ---")
        for entry in game_log:
            print(entry)

        print(f"\n--- Final Score ---")
        print(f"{team1.name}: {final_score1}")
        print(f"{team2.name}: {final_score2}")
    else:
        print("Failed to create one or both teams. Exiting.")

if __name__ == "__main__":
    main()
