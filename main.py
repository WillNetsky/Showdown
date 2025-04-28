# main.py
# The main script to load players, create teams, and run the game simulation.

import os
import glob # Import glob to find CSV files

# Import classes and functions from the other modules
from entities import Batter, Pitcher # Import Batter and Pitcher if needed elsewhere in main
from team import Team
from game_logic import play_game, load_players_from_csv, create_random_team # Import specific functions
from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS # Import necessary constants


def find_csv_files(directory="."):
    """
    Finds all CSV files in the specified directory.

    Args:
        directory (str): The directory to search in. Defaults to the current directory.

    Returns:
        list: A list of paths to CSV files found.
    """
    # Use glob to find all files ending with .csv in the directory
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    return csv_files

def main():
    """
    Main function to run the baseball simulation.
    """
    print("Starting Baseball Game Simulation...")

    # Find available CSV files in the current directory
    available_csv_files = find_csv_files()

    if not available_csv_files:
        print("Error: No CSV files found in the current directory.")
        return

    print("Available CSV files:")
    for i, file in enumerate(available_csv_files):
        print(f"{i + 1}: {file}")

    # Load all players from all found CSVs
    all_players = []
    for csv_file in available_csv_files:
        print(f"\nLoading player data from: {csv_file}")
        loaded_players = load_players_from_csv(csv_file)
        if loaded_players:
            all_players.extend(loaded_players)
        else:
            print(f"Warning: Could not load players from {csv_file}. Skipping.")


    if not all_players:
        print("Failed to load any player data from available CSVs. Exiting.")
        return

    print(f"\nSuccessfully loaded a total of {len(all_players)} players from all CSVs.")

    # Create two random teams
    team1 = create_random_team(all_players, "Random_Team_1", MIN_TEAM_POINTS, MAX_TEAM_POINTS)
    team2 = create_random_team(all_players, "Random_Team_2", MIN_TEAM_POINTS, MAX_TEAM_POINTS)

    if team1 is None or team2 is None:
        print("Failed to create valid teams within the specified point range. Exiting.")
        return

    print(f"\nTeam 1: {team1.name} ({team1.total_points} points)")
    print(f"Team 2: {team2.name} ({team2.total_points} points)")

    # Run the game simulation
    final_score1, final_score2, game_log = play_game(team1, team2)

    # Print the game log
    print("\n--- Game Log ---")
    for entry in game_log:
        print(entry)

    # Print the final score
    print("\n--- Final Score ---")
    print(f"{team1.name}: {final_score1}")
    print(f"{team2.name}: {final_score2}")

    # Print player stats (optional)
    print("\n--- Player Stats ---")
    print(f"\n{team1.name} Batting Stats:")
    for batter in team1.batters:
        print(batter)
    print(f"\n{team1.name} Pitching Stats:")
    for pitcher in team1.all_pitchers:
        print(pitcher)

    print(f"\n{team2.name} Batting Stats:")
    for batter in team2.batters:
        print(batter)
    print(f"\n{team2.name} Pitching Stats:")
    for pitcher in team2.all_pitchers:
        print(pitcher)


if __name__ == "__main__":
    main()
