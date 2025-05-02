# main.py
# This is the main script to run the baseball simulation.
# It handles loading player data, creating teams, running the game, and displaying results.

import os
import glob # Import glob to find team files

# Import classes and functions from other modules
from team_management import load_players_from_json, create_random_team, save_team_to_json, load_team_from_json, get_next_team_number # Import team management functions
from game_logic import play_game
from stats_display import display_linescore, display_boxscore # Import game simulation and display functions

# Define the path for player data and saved teams
PLAYER_DATA_FILE = 'all_players.json' # Assuming a single JSON file for all players
TEAMS_DIR = 'teams'

def get_team_choice(team_number, all_players):
    """
    Prompts the user to choose between generating or loading a team.

    Args:
        team_number (int): The number of the team being selected (1 for Away, 2 for Home).
        all_players (list): A list of all available Batter and Pitcher objects.

    Returns:
        Team or None: The selected or generated Team object, or None if creation/loading fails.
    """
    while True:
        choice = input(f"For Team {team_number} ({'Away' if team_number == 1 else 'Home'}), Press Enter to generate random team, L to load a team: ").strip().lower()
        if choice == '':
            team_name = input(f"Enter name for Team {team_number}: ").strip()
            if not team_name:
                team_name = f"Random Team {get_next_team_number(TEAMS_DIR)}" # Generate a default name if none provided
            team = create_random_team(all_players, team_name)
            if team:
                # Save the generated team
                next_team_num = get_next_team_number(TEAMS_DIR)
                team_save_filename = f"Team_{next_team_num}_{team.total_points}.json"
                team_save_filepath = os.path.join(TEAMS_DIR, team_save_filename)
                save_team_to_json(team, team_save_filepath)
                return team
            else:
                print("Failed to generate a team. Please try again.")
        elif choice == 'l':
            # List available team files
            available_teams = glob.glob(os.path.join(TEAMS_DIR, 'Team_*.json'))
            if not available_teams:
                print("No saved teams found. Please generate a team instead.")
                continue

            print("\nAvailable teams to load:")
            for i, team_file in enumerate(available_teams):
                print(f"{i + 1}. {os.path.basename(team_file)}")

            while True:
                try:
                    file_index = int(input(f"Enter the number of the team file to load for Team {team_number}: ")) - 1
                    if 0 <= file_index < len(available_teams):
                        filepath = available_teams[file_index]
                        team = load_team_from_json(filepath)
                        if team:
                            # Update team name to match the generic "Away Team" or "Home Team" for the game
                            team.name = f"{'Away' if team_number == 1 else 'Home'} Team"
                            print(f"Loaded team '{os.path.basename(filepath)}' as {team.name}.")
                            return team
                        else:
                            print("Failed to load the selected team. Please try again.")
                            break # Break from inner file selection loop
                    else:
                        print("Invalid file number. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        else:
            print("Invalid choice. Please enter 'G' or 'L'.")

def load_player_json(player_json_file):
    # --- Load Player Data ---
    if not os.path.exists(player_json_file):
        print(f"Error: Player data file not found at {player_json_file}. Please ensure '{player_json_file}' is in the same directory.")
        return

    all_players = load_players_from_json(player_json_file)

    if not all_players:
        print("No player data loaded. Exiting.")
        return

    print(f"Successfully loaded {len(all_players)} players.")
    return all_players

def main():
    """
    Main function to load players, create/load teams, and simulate a game.
    """
    print("Starting Baseball Simulation...")

    all_players = load_player_json(PLAYER_DATA_FILE)

    # --- Team Creation or Loading ---
    print("\nSetting up teams...")

    # Get Away Team (Team 1)
    team1 = get_team_choice(1, all_players)
    if team1 is None:
        print("Team 1 setup failed. Exiting.")
        return

    # Get Home Team (Team 2)
    team2 = get_team_choice(2, all_players)
    if team2 is None:
        print("Team 2 setup failed. Exiting.")
        return

    # --- Simulate Game ---
    print("\nStarting game simulation...")

    # Play the game (team1 is away, team2 is home)
    # play_game now returns score1, score2, game_log, team1_inning_runs, team2_inning_runs
    away_score, home_score, game_log, team1_inning_runs, team2_inning_runs = play_game(team1, team2) # team1 is away, team2 is home

    # --- Display Game Results ---
    print("\n--- Game Over ---")
    print(f"Final Score: {team1.name} {away_score} - {team2.name} {home_score}")

    print("\n--- Game Log ---")
    for entry in game_log:
        print(entry)

    # Display the linescore
    display_linescore(team1.name, team2.name, team1_inning_runs, team2_inning_runs, away_score, home_score)

    # Display the box-score for each team
    display_boxscore(team1)
    display_boxscore(team2)


if __name__ == "__main__":
    main()
