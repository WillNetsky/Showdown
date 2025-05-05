# main.py
# This is the main script to run the baseball simulation.
# It handles loading player data, creating teams, running the game, and displaying results.

import os
import glob # Import glob to find team files
import itertools

# Import classes and functions from other modules
from team_management import load_players_from_json, create_random_team, save_team_to_json, load_team_from_json, get_next_team_number # Import team management functions
from game_logic import play_game
from entities import Team
from elo import update_ratings
from stats_display import display_linescore, display_boxscore # Import game simulation and display functions

# Define the path for player data and saved teams
PLAYER_DATA_FILE = 'all_players.json' # Assuming a single JSON file for all players
TEAMS_DIR = 'teams'

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

def play_series(team_1: Team, team_2: Team):
    for i in range(1, 5):
        away_score, home_score, game_log, team1_inning_runs, team2_inning_runs = play_game(team_2, team_1)
        if away_score > home_score:
            team_2.wins += 1
            team_1.losses += 1
            update_ratings(team_2, team_1, 1)
        elif home_score > away_score:
            team_2.losses += 1
            team_1.wins += 1
            update_ratings(team_1, team_2, 1)
        team_1.post_game_team_cleanup()
        team_2.post_game_team_cleanup()

def preseason(teams):
    # Preseason
    for team in teams:
        team.preseason_stats_update()
    print("Pre-season complete")
    return teams

def play_season(teams):
    print("Beginning of season")
    # Season
    for team_1, team_2 in list(itertools.combinations(teams, 2)):
        play_series(team_1, team_2)
        play_series(team_2, team_1)
    print("Season complete")

def postseason(teams):
    for team in teams:
        team.post_season_stats_update()
    print("Postseason complete")
    return teams

def check_continue(teams):
    choice = input("Press enter to run it again").strip().lower()
    if choice == '':
        main(teams)
    else:
        exit(0)

def display_season_batting_leaders(all_batters, n=10):
    pa_leaders = sorted(all_batters, key=lambda batter: batter.plate_appearances, reverse=True)
    print("PA")
    for batter in pa_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.plate_appearances))

    ab_leaders = sorted(all_batters, key=lambda batter: batter.at_bats, reverse=True)
    print("AB")
    for batter in ab_leaders[:n-1]:
        print(batter.name+" ("+batter.team_name+"): "+str(batter.at_bats))

    r_leaders = sorted(all_batters, key=lambda batter: batter.runs_scored, reverse=True)
    print("R")
    for batter in r_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.runs_scored))

    singles_leaders = sorted(all_batters, key=lambda batter: batter.singles, reverse=True)
    print("Singles")
    for batter in singles_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.singles))

    doubles_leaders = sorted(all_batters, key=lambda batter: batter.doubles, reverse=True)
    print("Doubles")
    for batter in doubles_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.doubles))

    triples_leaders = sorted(all_batters, key=lambda batter: batter.triples, reverse=True)
    print("Triples")
    for batter in triples_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.triples))

    home_run_leaders = sorted(all_batters, key=lambda batter: batter.home_runs, reverse=True)
    print("Home Runs")
    for batter in home_run_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.home_runs))

    walks_leaders = sorted(all_batters, key=lambda batter: batter.walks, reverse=True)
    print("Walks")
    for batter in walks_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.walks))

    strikeouts_leaders = sorted(all_batters, key=lambda batter: batter.strikeouts, reverse=True)
    print("Strikeouts (Batting)")
    for batter in strikeouts_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.strikeouts))

    avg_leaders = sorted(all_batters, key=lambda batter: batter.hits, reverse=True)
    print("Batting Avg")
    for batter in avg_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.calculate_avg()))

    obp_leaders = sorted(all_batters, key=lambda batter: batter.hits, reverse=True)
    print("OBP")
    for batter in obp_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.calculate_obp()))

    slg_leaders = sorted(all_batters, key=lambda batter: batter.hits, reverse=True)
    print("SLG")
    for batter in slg_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.calculate_slg()))

    ops_leaders = sorted(all_batters, key=lambda batter: batter.hits, reverse=True)
    print("OPS")
    for batter in ops_leaders[:n - 1]:
        print(batter.name + " (" + batter.team_name + "): " + str(batter.calculate_ops()))


def display_season_pitching_leaders(all_pitchers, n=10):
    strikeout_leaders = sorted(all_pitchers, key=lambda pitcher: pitcher.strikeouts_thrown, reverse=True)
    print("Strikeouts")
    for pitcher in strikeout_leaders[:n-1]:
        print(pitcher.name+" ("+pitcher.team_name+"): "+str(pitcher.strikeouts_thrown))

def main(all_teams):
    preseason(all_teams)
    play_season(all_teams)
    postseason(all_teams)

    # Sort teams by wins
    teams = sorted(all_teams, key=lambda x: x.wins, reverse=True)
    for team in teams:
        print(team.name + ": " + str(team.wins) + "-" + str(team.losses) + "(" + str(team.wins_all_time) + "-" + str(team.losses_all_time) + ")" +
               "  " + str(team.win_pct_all_time) + "    ELO: " + str(team.elo_rating))

    all_batters = []
    all_pitchers = []
    for team in teams:
        for batter in team.batters:
            all_batters.append(batter)
        for pitcher in team.all_pitchers:
            all_pitchers.append(pitcher)

    display_season_batting_leaders(all_batters)
    display_season_pitching_leaders(all_pitchers)

    # Remove teams with a losing record
    teams = list(filter(lambda x: x.wins > x.losses, teams))

    # Create replacement teams
    print("Loading players...")
    all_players = load_players_from_json(PLAYER_DATA_FILE)
    while len(teams)<100:
        team_name = f"Random Team {get_next_team_number(TEAMS_DIR)}"  # Generate a default name if none provided
        team = create_random_team(all_players, team_name)
        if team:
            # Save the generated team
            next_team_num = get_next_team_number(TEAMS_DIR)
            team_save_filename = f"Team_{next_team_num}_{team.total_points}.json"
            team_save_filepath = os.path.join(TEAMS_DIR, team_save_filename)
            save_team_to_json(team, team_save_filepath)
            teams.append(team)
    check_continue(teams)

def init():
    print("Starting Baseball Simulation...")
    all_teams = []
    available_teams = glob.glob(os.path.join(TEAMS_DIR, 'Team_*.json'))
    for team_file in available_teams:
        team = load_team_from_json(team_file)
        all_teams.append(team)
    print(str(len(all_teams)) + " total teams available")
    print(str(len(all_teams[:101]))+" teams loaded")
    return all_teams[:101]

if __name__ == "__main__":
    teams = init()
    main(teams)
