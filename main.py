# main.py
# This is the main script to run the baseball game simulation.
# Updated to load base player data from a single JSON file and show detailed load count.

import os
import glob

# Import necessary functions and classes from other modules
# Import the new load_players_from_json function
from team_management import load_players_from_json, create_random_team, save_team_to_csv, load_team_from_csv, get_next_team_number
from game_logic import play_game
from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS # Import constants
from entities import Batter, Pitcher # Import Batter and Pitcher for type checking
from team import Team # Import Team for type hinting

def display_linescore(away_team_name: str, home_team_name: str, away_score: int, home_score: int,
                      away_inning_runs: list[int], home_inning_runs: list[int],
                      away_total_hits: int, home_total_hits: int,
                      away_total_errors: int, home_total_errors: int):
    """
    Displays the game linescore in a formatted table.

    Args:
        away_team_name (str): The name of the away team (will be "Team 2").
        home_team_name (str): The name of the home team (will be "Team 1").
        away_score (int): The final score of the away team.
        home_score (int): The final score of the home team.
        away_inning_runs (list[int]): List of runs scored by the away team per inning.
        home_inning_runs (list[int]): List of runs scored by the home team per inning.
        away_total_hits (int): Total hits for the away team.
        home_total_hits (int): Total hits for the home team.
        away_total_errors (int): Total errors for the away team.
        home_total_errors (int): Total errors for the home team.
    """
    print("\n--- Linescore ---")

    # Determine the total number of innings played (max of the two teams' inning runs lists)
    total_innings_played = max(len(away_inning_runs), len(home_inning_runs))

    # Header row: Team Name | 1 | 2 | ... | R | H | E
    # Adjust spacing for inning numbers based on max innings
    inning_col_width = 3 # Default width for inning columns
    if total_innings_played >= 10:
        inning_col_width = 4 # Increase width if innings go into double digits

    header = f"{'Team':<15} |"
    for i in range(1, total_innings_played + 1):
        header += f" {i:<{inning_col_width-1}}|" # Adjust spacing based on calculated width
    header += " R | H | E"
    print(header)

    # Separator line
    separator = "-" * 15 + "-|" + "-".join(["-" * (inning_col_width)] * total_innings_played) + "-|---|---|---"
    print(separator)

    # Away Team row
    away_row = f"{away_team_name:<15} |"
    for runs in away_inning_runs:
        away_row += f" {runs:<{inning_col_width-1}}|" # Adjust spacing
    # Pad with empty columns if fewer than total_innings_played
    away_row += " " * (inning_col_width) * (total_innings_played - len(away_inning_runs)) + "|" * (total_innings_played - len(away_inning_runs))
    away_row += f" {away_score:<2}| {away_total_hits:<2}| {away_total_errors:<1}"
    print(away_row)

    # Home Team row
    home_row = f"{home_team_name:<15} |"
    for runs in home_inning_runs:
        home_row += f" {runs:<{inning_col_width-1}}|" # Adjust spacing
     # Pad with empty columns if fewer than total_innings_played
    home_row += " " * (inning_col_width) * (total_innings_played - len(home_inning_runs)) + "|" * (total_innings_played - len(home_inning_runs))
    home_row += f" {home_score:<2}| {home_total_hits:<2}| {home_total_errors:<1}"
    print(home_row)


def display_boxscore_stats(team: Team, team_type: str):
    """
    Displays the batting and pitching stats for a given team in a formatted boxscore table.

    Args:
        team (Team): The Team object whose stats is to be displayed.
        team_type (str): A string indicating if the team is "Away" or "Home".
    """
    print(f"\n--- {team.name} Stats ({team_type}) ---")

    # Batting Stats
    print("Batting:")
    # Batting Stats Header
    batter_header = f"{'Name':<25} | {'AB':<3} | {'R':<3} | {'H':<3} | {'RBI':<3} | {'BB':<3} | {'K':<3} | {'AVG':<5} | {'OPS':<5}"
    print(batter_header)
    print("-" * len(batter_header)) # Separator line

    # Batting Stats Rows (Starters)
    for batter in team.batters: # Iterate through the starters list
        avg = batter.calculate_avg()
        ops = batter.calculate_ops()
        batter_row = (
            f"{batter.name:<25} | {batter.at_bats:<3} | {batter.runs_scored:<3} | "
            f"{batter.singles + batter.doubles + batter.triples + batter.home_runs:<3} | " # Total Hits
            f"{batter.rbi:<3} | {batter.walks:<3} | {batter.strikeouts:<3} | "
            f"{avg:5.3f} | {ops:5.3f}" # Corrected format specifier for AVG and OPS
        )
        print(batter_row)

    # Bench Separator and Bench Player
    if team.bench: # Only print the bench section if there are bench players
        # Create a separator line matching the header length
        bench_separator = "-" * len(batter_header)
        print(bench_separator)
        print("---Bench------") # Keep the "---Bench------" label for clarity
        print(bench_separator) # Add another separator line after the label

        for batter in team.bench: # Iterate through the bench list (should be just one player)
            avg = batter.calculate_avg()
            ops = batter.calculate_ops()
            batter_row = (
                f"{batter.name:<25} | {batter.at_bats:<3} | {batter.runs_scored:<3} | "
                f"{batter.singles + batter.doubles + batter.triples + batter.home_runs:<3} | " # Total Hits
                f"{batter.rbi:<3} | {batter.walks:<3} | {batter.strikeouts:<3} | "
                f"{avg:5.3f} | {ops:5.3f}" # Corrected format specifier for AVG and OPS
            )
            print(batter_row)


    print("\nPitching:")
    # Pitching Stats Header
    # Updated IP column width and format specifier
    pitcher_header = f"{'Name':<25} | {'IP':<5} | {'H':<3} | {'R':<3} | {'ER':<3} | {'BB':<3} | {'K':<3} | {'HR':<3} | {'ERA':<5}"
    print(pitcher_header)
    print("-" * len(pitcher_header)) # Separator line

    # Pitching Stats Rows
    for pitcher in team.starters + team.relievers + team.closers:
        era = pitcher.calculate_era()
        pitcher_row = (
            # Use get_formatted_ip() for display
            f"{pitcher.name:<25} | {pitcher.get_formatted_ip():<5} | {pitcher.hits_allowed:<3} | "
            f"{pitcher.runs_allowed:<3} | {pitcher.earned_runs_allowed:<3} | {pitcher.walks_allowed:<3} | "
            f"{pitcher.strikeouts_thrown:<3} | {pitcher.home_runs_allowed:<3} | {era:5.2f}" # Corrected attribute name for HR
        )
        print(pitcher_row)


def main():
    """
    Main function to load players, create or load teams, simulate a game, and print results.
    """
    print("Loading player data...")

    # Define the directory containing the data files
    data_dir = os.path.dirname(os.path.abspath(__file__))
    # Use the JSON file path
    players_filepath = os.path.join(data_dir, 'all_players.json')

    # Load all players from the JSON file
    # Use the new load_players_from_json function
    all_players = load_players_from_json(players_filepath)

    if not all_players:
        print("No player data loaded. Cannot proceed.")
        return

    # Calculate the number of batters and pitchers
    num_batters = sum(1 for player in all_players if isinstance(player, Batter))
    num_pitchers = sum(1 for player in all_players if isinstance(player, Pitcher))

    # Updated print statement to show counts
    print(f"Loaded {len(all_players)} players from {players_filepath} ({num_batters} batters, {num_pitchers} pitchers)")


    # Create the 'teams' directory if it doesn't exist
    teams_dir = os.path.join(data_dir, 'teams')
    if not os.path.exists(teams_dir):
        os.makedirs(teams_dir)


    team1 = None
    team2 = None

    while team1 is None or team2 is None:
        print("\nChoose an option:")
        print("1. Generate two random teams")
        print("2. Load two teams from files")

        choice = input("Enter your choice (1 or 2): ").strip()

        if choice == '1':
            print("\nCreating two random teams...")
            # Get the next available team number
            next_team_number = get_next_team_number(teams_dir)

            # Create two random teams with sequential numerical names
            team1_name = f"Team {next_team_number}"
            team1 = create_random_team(all_players, team1_name, MIN_TEAM_POINTS, MAX_TEAM_POINTS)
            if team1:
                 # Save the generated Team 1 with sequential numbering and points
                 # Use consistent filename format "Team_X_totalpts.csv"
                 team1_filename = f"Team_{next_team_number}_{team1.total_points}.csv"
                 save_team_to_csv(team1, os.path.join(teams_dir, team1_filename))

            # Increment the team number for the second team
            next_team_number += 1
            team2_name = f"Team {next_team_number}"
            team2 = create_random_team(all_players, team2_name, MIN_TEAM_POINTS, MAX_TEAM_POINTS)
            if team2:
                 # Save the generated Team 2 with sequential numbering and points
                 team2_filename = f"Team_{next_team_number}_{team2.total_points}.csv"
                 save_team_to_csv(team2, os.path.join(teams_dir, team2_filename))


            if not team1 or not team2:
                print("Failed to create one or both random teams. Please try again.")
                team1 = None # Reset teams to None to re-enter the loop
                team2 = None

        elif choice == '2':
            print("\nLoading teams from files...")
            available_team_files = glob.glob(os.path.join(teams_dir, '*.csv'))

            if not available_team_files:
                print("No team files found in the 'teams' directory.")
                continue # Go back to the menu

            print("Available team files:")
            for i, filepath in enumerate(available_team_files):
                print(f"{i + 1}. {os.path.basename(filepath)}")

            try:
                # Get user input for the two teams
                team1_index = int(input("Enter the number for the first team (will be Team 1): ")) - 1
                team2_index = int(input("Enter the number for the second team (will be Team 2): ")) - 1

                if not (0 <= team1_index < len(available_team_files) and 0 <= team2_index < len(available_team_files)):
                    print("Invalid team selection.")
                    continue # Go back to the menu

                if team1_index == team2_index:
                    print("Please select two different teams.")
                    continue # Go back to the menu


                team1_filepath = available_team_files[team1_index]
                team2_filepath = available_team_files[team2_index]

                # Load the selected teams
                loaded_team1 = load_team_from_csv(team1_filepath)
                loaded_team2 = load_team_from_csv(team2_filepath)

                if loaded_team1 and loaded_team2:
                    # Assign numerical names after loading for the game simulation
                    team1 = loaded_team1
                    team1.name = "Team 1"
                    team2 = loaded_team2
                    team2.name = "Team 2"
                else:
                    print("Failed to load one or both teams. Please check the file format.")
                    team1 = None # Reset teams to None to re-enter the loop
                    team2 = None


            except ValueError:
                print("Invalid input. Please enter the number of the team.")
            except Exception as e:
                print(f"An error occurred during team loading: {e}")
                team1 = None # Reset teams to None to re-enter the loop
                team2 = None


        else:
            print("Invalid choice. Please enter 1 or 2.")


    print("\nStarting game simulation...")

    # Simulate the game
    # Pass team2 (Away Team) as the first argument, team1 (Home Team) as the second
    # The display functions expect Away then Home, so pass team2 then team1
    away_score, home_score, game_log, away_inning_runs, home_inning_runs, away_total_hits, home_total_hits, away_total_errors, home_total_errors = play_game(team2, team1)


    print("\n--- Game Log ---")
    for entry in game_log:
        print(entry)

    # Display Linescore - Pass team2 (Away) and team1 (Home)
    display_linescore(team2.name, team1.name, away_score, home_score,
                      away_inning_runs, home_inning_runs,
                      away_total_hits, home_total_hits,
                      away_total_errors, home_total_errors)


    # Display Boxscore Stats - Display Away Team (team2) first, then Home Team (team1)
    display_boxscore_stats(team2, "Away")
    display_boxscore_stats(team1, "Home")


if __name__ == "__main__":
    main()
