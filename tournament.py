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

# Define the path for player data and saved teams
PLAYER_DATA_FILE = 'all_players.json' # Assuming a single JSON file for all players
TEAMS_DIR = 'teams'

def load_player_json(player_json_file):
    # --- Load Player Data ---
    if not os.path.exists(player_json_file):
        print(f"Error: Player data file not found at {player_json_file}. Please ensure '{player_json_file}' is in the same directory.")
        return None

    all_players = load_players_from_json(player_json_file)

    if not all_players:
        print("No player data loaded. Exiting.")
        return None

    print(f"Successfully loaded {len(all_players)} players.")
    return all_players

def play_series(team_1: Team, team_2: Team):
    for i in range(1, 5):
        away_score, home_score, game_log, team1_inning_runs, team2_inning_runs = play_game(team_2, team_1)

        team_1.post_game_team_cleanup()
        team_2.post_game_team_cleanup()

def preseason(teams):
    # Preseason
    for team in teams:
        team.team_stats.reset_for_new_season()
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
        team.team_stats.reset_for_new_season()
    print("Postseason complete")
    return teams

def check_continue(teams):
    choice = input("Press enter to run it again, press N to quit: ").strip().lower()
    if choice == '':
        main(teams)
    else:
        exit(0)


def display_season_leaders(all_players, n=10, player_type="both"):
    """
    Display the top n leaders in various batting and/or pitching statistics.

    Args:
        all_players: List of player objects (batters and/or pitchers)
        n: Number of top players to display (default=10)
        player_type: Type of stats to display - "batting", "pitching", or "both" (default="both")
    """
    # Define batting stat categories to be displayed
    # Format: (attribute_name, display_name, format_string, is_calculated_function, minimum_qualifier)
    batting_stats = [
        # Basic stats (direct attributes)
        ("plate_appearances", "PA", "{:.0f}", False, 0),
        ("at_bats", "AB", "{:.0f}", False, 0),
        ("runs_scored", "R", "{:.0f}", False, 0),
        ("hits", "Hits", "{:.0f}", False, 0),
        ("singles", "Singles", "{:.0f}", False, 0),
        ("doubles", "Doubles", "{:.0f}", False, 0),
        ("triples", "Triples", "{:.0f}", False, 0),
        ("home_runs", "Home Runs", "{:.0f}", False, 0),
        ("walks", "Walks", "{:.0f}", False, 0),
        ("strikeouts", "Strikeouts (Batting)", "{:.0f}", False, 0),
        ("rbi", "RBI", "{:.0f}", False, 0),

        # Calculated stats (calling functions)
        ("calculate_avg", "Batting Avg", "{}", True, 3.1 * n),  # Typically 3.1 PA per team game
        ("calculate_obp", "OBP", "{}", True, 3.1 * n),
        ("calculate_slg", "SLG", "{}", True, 3.1 * n),
        ("calculate_ops", "OPS", "{}", True, 3.1 * n)
    ]

    # Define pitching stat categories to be displayed
    pitching_stats = [
        # Basic stats (direct attributes)
        ("batters_faced", "Batters Faced", "{:.0f}", False, 0),
        ("outs_recorded", "Outs", "{:.0f}", False, 0),
        ("strikeouts_thrown", "Strikeouts (Pitching)", "{:.0f}", False, 0),
        ("walks_allowed", "Walks Allowed", "{:.0f}", False, 0),
        ("hits_allowed", "Hits Allowed", "{:.0f}", False, 0),
        ("home_runs_allowed", "HR Allowed", "{:.0f}", False, 0),
        ("runs_allowed", "Runs Allowed", "{:.0f}", False, 0),
        ("earned_runs_allowed", "Earned Runs", "{:.0f}", False, 0),

        # Innings Pitched (special case - sort by outs but display formatted)
        ("outs_recorded", "Innings Pitched", "{}", False, 0),
        ("calculate_era", "ERA", "{:.2f}", True, n),  # Typically minimum 1 IP per team game
        ("calculate_whip", "WHIP", "{:.2f}", True, n),
        ("calculate_k_per_9", "K/9", "{:.2f}", True, n)
    ]

    # Function to get the value of a stat
    def get_stat_value(player, stat_name, is_calculated):
        # Ensure we're using the season_stats attribute of the player
        stats_obj = player.season_stats

        if is_calculated:
            # Call the method to get the calculated value
            return getattr(stats_obj, stat_name)()
        else:
            # Ensure hits is updated before accessing it
            if stat_name == "hits":
                stats_obj.update_hits()
            # Access the attribute directly
            return getattr(stats_obj, stat_name)

    # Function to display a single player's info
    def format_player_info(player, value, format_str, stat_name=None):
        # Special case for innings pitched - use the formatted value instead of raw outs
        if stat_name == "outs_recorded" and format_str == "{}":
            display_value = player.season_stats.get_formatted_ip()
        else:
            display_value = format_str.format(value)

        return f"{player.name} - {player.year}{player.set}: {display_value}"

    # Function to display leaders for a set of statistics
    def display_stat_leaders(players, stats_list, stat_type_header):
        print(f"\n{'=' * 20} {stat_type_header} LEADERS {'=' * 20}\n")

        for stat_name, display_name, format_str, is_calculated, min_qualifier in stats_list:
            print(display_name)

            # Get players who meet the minimum qualification
            qualified_players = []
            if stat_name in ["calculate_avg", "calculate_obp", "calculate_slg", "calculate_ops"]:
                # For rate stats, filter by plate appearances
                qualified_players = [p for p in players if p.season_stats.plate_appearances >= min_qualifier]
            elif stat_name in ["calculate_era", "calculate_whip", "calculate_k_per_9"]:
                # For pitching rate stats, filter by innings pitched
                qualified_players = [p for p in players if p.season_stats.outs_recorded >= min_qualifier * 3]
            else:
                # For counting stats, no minimum
                qualified_players = players

            if not qualified_players:
                print("No qualified players")
                print()
                continue

            # Sort the players by the current statistic
            if stat_name == "calculate_era":
                # ERA is better when lower, so reverse=False
                leaders = sorted(
                    qualified_players,
                    key=lambda p: get_stat_value(p, stat_name, is_calculated),
                    reverse=False
                )
            else:
                # All other stats are better when higher
                leaders = sorted(
                    qualified_players,
                    key=lambda p: get_stat_value(p, stat_name, is_calculated),
                    reverse=True
                )

            # Display the top n leaders
            for player in leaders[:n]:
                value = get_stat_value(player, stat_name, is_calculated)
                print(format_player_info(player, value, format_str, stat_name))

            # Add spacing between stat categories for better readability
            print()

    # Display batting leaders if requested
    if player_type.lower() in ["batting", "both"]:
        display_stat_leaders(all_players, batting_stats, "BATTING")

    # Display pitching leaders if requested
    if player_type.lower() in ["pitching", "both"]:
        display_stat_leaders(all_players, pitching_stats, "PITCHING")


def print_standings_with_elo(teams):
    """Print league standings sorted by wins, with ELO ratings"""
    sorted_teams = sorted(teams, key=lambda t: (t.team_stats.wins, t.team_stats.elo_rating), reverse=True)

    print("Team                W-L     Win%    ELO    R     RA  Run Diff")
    print("----------------------------------------------------------------")
    for team in sorted_teams:
        stats = team.team_stats
        print(
            f"{team.name:20} {stats.wins:2}-{stats.losses:<2}   .{int(stats.calculate_win_pct() * 1000):3}   {stats.elo_rating:4.0f}  {stats.runs_scored}  {stats.runs_allowed}  {stats.run_differential:+3d}")

def main(all_teams,num_teams = 2):
    preseason(all_teams)
    play_season(all_teams)


    print_standings_with_elo(all_teams)

    all_batters = []
    all_pitchers = []
    for team in all_teams:
        for batter in team.batters:
            all_batters.append(batter)
        for pitcher in team.all_pitchers:
            all_pitchers.append(pitcher)

    display_season_leaders(all_batters+all_pitchers)


    # Remove teams with a losing record
    all_teams = list(filter(lambda x: x.team_stats.wins > x.team_stats.losses, all_teams))
    postseason(all_teams)

    # Create replacement teams
    print("Loading players...")
    all_players = load_players_from_json(PLAYER_DATA_FILE)
    while len(all_teams)<num_teams:
        team_name = f"Random Team {get_next_team_number(TEAMS_DIR)}"  # Generate a default name if none provided
        team = create_random_team(all_players, team_name)
        if team:
            # Save the generated team
            next_team_num = get_next_team_number(TEAMS_DIR)
            team_save_filename = f"Team_{next_team_num}_{team.total_points}.json"
            team_save_filepath = os.path.join(TEAMS_DIR, team_save_filename)
            save_team_to_json(team, team_save_filepath)
            all_teams.append(team)
    check_continue(all_teams)

def init(num_teams=2):
    print("Starting Baseball Simulation...")
    all_teams = []
    available_teams = glob.glob(os.path.join(TEAMS_DIR, 'Team_*.json'))
    for team_file in available_teams:
        team = load_team_from_json(team_file)
        all_teams.append(team)
    print(str(len(all_teams)) + " total teams available")
    print(str(len(all_teams[:num_teams]))+" teams loaded")
    return all_teams[:num_teams]

if __name__ == "__main__":
    teams = init()
    main(teams)
