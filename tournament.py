# main.py
# This is the main script to run the baseball simulation.
# It handles loading player data, creating teams, running the game, and displaying results.

import os
import glob # Import glob to find team files
import itertools

# Import classes and functions from other modules
from team_management import load_players_from_json, create_random_team, save_team_to_json, load_team_from_json, get_next_team_number # Import team management functions
from game_logic import play_game
from stats_display import display_linescore, display_boxscore # Import game simulation and display functions

# Define the path for player data and saved teams
PLAYER_DATA_FILE = 'all_players.json' # Assuming a single JSON file for all players
TEAMS_DIR = 'teams'

def main():
    """
    Main function to load players, create/load teams, and simulate a game.
    """
    print("Starting Baseball Simulation...")
    all_teams = []
    available_teams = glob.glob(os.path.join(TEAMS_DIR, 'Team_*.json'))
    for team_file in available_teams:
        team = load_team_from_json(team_file)
        all_teams.append(team)
    print(str(len(all_teams))+" teams loaded")
    for team_1, team_2 in list(itertools.combinations(all_teams, 2)):
        #print(team_1.name + " vs " + team_2.name)
        for i in range(1,5):
            away_score, home_score, game_log, team1_inning_runs, team2_inning_runs = play_game(team_2, team_1)
            if away_score > home_score:
                team_2.wins += 1
                team_1.losses += 1
            elif home_score > away_score:
                team_2.losses += 1
                team_1.wins += 1
            team_1.post_game_team_cleanup()
            team_2.post_game_team_cleanup()
        for i in range(1,5):
            away_score, home_score, game_log, team1_inning_runs, team2_inning_runs = play_game(team_1, team_2)
            if away_score > home_score:
                team_1.wins += 1
                team_2.losses += 1
            elif home_score > away_score:
                team_1.losses += 1
                team_2.wins += 1
            team_1.post_game_team_cleanup()
            team_2.post_game_team_cleanup()

    teams = sorted(all_teams, key=lambda x: x.wins, reverse=True)
    for team in teams:
        print(team.name+": "+str(team.wins)+"-"+str(team.losses))



    # # Display the box-score for each team
    # display_boxscore(teams[0])
    # display_boxscore(teams[1])



if __name__ == "__main__":
    main()
