# main.py
# This is the main script to run the baseball game simulation.

import os
import glob

# Import necessary functions and classes from other modules
from team_management import load_players_from_csv, create_random_team
from game_logic import play_game
from constants import MIN_TEAM_POINTS, MAX_TEAM_POINTS # Import constants
from entities import Batter, Pitcher # Import Batter and Pitcher for type checking

def main():
    """
    Main function to load players, create teams, simulate a game, and print results.
    """
    print("Loading player data...")

    # Define the directory containing the CSV files
    # Assumes CSVs are in the same directory as the script
    data_dir = os.path.dirname(os.path.abspath(__file__))
    batters_filepath = os.path.join(data_dir, 'all_batters.csv')
    pitchers_filepath = os.path.join(data_dir, 'all_pitchers.csv')

    # Load all players from CSV files
    all_players = []
    batters = load_players_from_csv(batters_filepath)
    if batters:
        all_players.extend(batters)

    pitchers = load_players_from_csv(pitchers_filepath)
    if pitchers:
        all_players.extend(pitchers)

    if not all_players:
        print("No player data loaded. Cannot proceed with team creation.")
        return

    print("Creating teams...")

    # Create two random teams within the specified point range
    # Ensure enough players are available before attempting team creation
    min_batters_needed = 10 # 8 starters + 1 DH + 1 bench
    min_pitchers_needed = 10 # 4 SP + 6 RP/CL
    available_batters_count = len([p for p in all_players if isinstance(p, Batter)])
    available_pitchers_count = len([p for p in all_players if isinstance(p, Pitcher)])

    if available_batters_count < min_batters_needed * 2 or available_pitchers_count < min_pitchers_needed * 2:
         print(f"Not enough players loaded to create two teams with required roster size ({min_batters_needed} batters, {min_pitchers_needed} pitchers per team).")
         print(f"Available Batters: {available_batters_count}, Available Pitchers: {available_pitchers_count}")
         return


    # Create Home Team first, then Away Team
    team1 = create_random_team(all_players, "Home Team", MIN_TEAM_POINTS, MAX_TEAM_POINTS)
    team2 = create_random_team(all_players, "Away Team", MIN_TEAM_POINTS, MAX_TEAM_POINTS)


    if not team1 or not team2:
        print("Failed to create one or both teams. Cannot proceed with game simulation.")
        return

    print("\nStarting game simulation...")

    # Simulate the game and receive the new linescore data
    away_score, home_score, game_log, away_inning_runs, home_inning_runs, away_total_hits, home_total_hits, away_total_errors, home_total_errors = play_game(team2, team1)


    print("\n--- Game Log ---")
    for entry in game_log:
        print(entry)

    print("\n--- Final Score ---")
    # Print Away Team score first, then Home Team score
    print(f"{team2.name}: {away_score}")
    print(f"{team1.name}: {home_score}")

    # --- Linescore Display ---
    print("\n--- Linescore ---")

    # Determine the total number of innings played (max of the two teams' inning runs lists)
    total_innings_played = max(len(away_inning_runs), len(home_inning_runs))

    # Header row: Team Name | 1 | 2 | ... | R | H | E
    header = f"{'Team':<15} |"
    for i in range(1, total_innings_played + 1):
        header += f" {i:<2}|"
    header += " R | H | E"
    print(header)

    # Separator line
    separator = "-" * 15 + "-|" + "-".join(["---"] * total_innings_played) + "-|---|---|---"
    print(separator)

    # Away Team row
    away_row = f"{team2.name:<15} |"
    for runs in away_inning_runs:
        away_row += f" {runs:<2}|"
    # Pad with empty columns if fewer than total_innings_played
    away_row += "   |" * (total_innings_played - len(away_inning_runs))
    away_row += f" {away_score:<2}| {away_total_hits:<2}| {away_total_errors:<1}"
    print(away_row)

    # Home Team row
    home_row = f"{team1.name:<15} |"
    for runs in home_inning_runs:
        home_row += f" {runs:<2}|"
     # Pad with empty columns if fewer than total_innings_played
    home_row += "   |" * (total_innings_played - len(home_inning_runs))
    home_row += f" {home_score:<2}| {home_total_hits:<2}| {home_total_errors:<1}"
    print(home_row)

    # --- Formatted Boxscore Stats ---

    # Away Team Stats
    print(f"\n--- {team2.name} Stats ---")
    print("Batting:")
    # Batting Stats Header
    batter_header = f"{'Name':<25} | {'AB':<3} | {'R':<3} | {'H':<3} | {'RBI':<3} | {'BB':<3} | {'K':<3} | {'AVG':<5} | {'OPS':<5}"
    print(batter_header)
    print("-" * len(batter_header)) # Separator line

    # Batting Stats Rows
    for batter in team2.batters + team2.bench:
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
    pitcher_header = f"{'Name':<25} | {'IP':<4} | {'H':<3} | {'R':<3} | {'ER':<3} | {'BB':<3} | {'K':<3} | {'HR':<3} | {'ERA':<5}"
    print(pitcher_header)
    print("-" * len(pitcher_header)) # Separator line

    # Pitching Stats Rows
    for pitcher in team2.starters + team2.relievers + team2.closers:
        era = pitcher.calculate_era()
        pitcher_row = (
            f"{pitcher.name:<25} | {pitcher.innings_pitched:<4.1f} | {pitcher.hits_allowed:<3} | "
            f"{pitcher.runs_allowed:<3} | {pitcher.earned_runs_allowed:<3} | {pitcher.walks_allowed:<3} | "
            f"{pitcher.strikeouts_thrown:<3} | {pitcher.home_runs_allowed:<3} | {era:5.2f}" # Corrected attribute name for HR
        )
        print(pitcher_row)


    # Home Team Stats
    print(f"\n--- {team1.name} Stats ---")
    print("Batting:")
    # Batting Stats Header (same as Away Team)
    print(batter_header)
    print("-" * len(batter_header)) # Separator line

    # Batting Stats Rows
    for batter in team1.batters + team1.bench:
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
    # Pitching Stats Header (same as Away Team)
    print(pitcher_header)
    print("-" * len(pitcher_header)) # Separator line

    # Pitching Stats Rows
    for pitcher in team1.starters + team1.relievers + team1.closers:
        era = pitcher.calculate_era()
        pitcher_row = (
            f"{pitcher.name:<25} | {pitcher.innings_pitched:<4.1f} | {pitcher.hits_allowed:<3} | "
            f"{pitcher.runs_allowed:<3} | {pitcher.earned_runs_allowed:<3} | {pitcher.walks_allowed:<3} | "
            f"{pitcher.strikeouts_thrown:<3} | {pitcher.home_runs_allowed:<3} | {era:5.2f}" # Corrected attribute name for HR
        )
        print(pitcher_row)


if __name__ == "__main__":
    main()
