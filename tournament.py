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


def play_series(team_1: Team, team_2: Team, series_number: int, total_series: int, log_callback=None):
    """
    Simulates a series of games between two teams.
    Your original tournament.py play_series had a loop for 4 games.
    This version assumes play_game is called 4 times.
    Args:
        team_1 (Team): One team.
        team_2 (Team): The other team.
        series_number (int): Current series number for logging.
        total_series (int): Total number of series for logging.
        log_callback (function, optional): Function to call for logging messages.
    """
    if log_callback:
        log_callback(f"Series {series_number}/{total_series}: {team_1.name} vs {team_2.name} (4 games)")

    num_games_in_series = 4  # As per your original loop: for i in range(1, 5)

    for i in range(1, num_games_in_series + 1):
        # Determine home and away. Your original play_series had team_2, team_1 in play_game.
        # This implies team_2 was home, team_1 was away for that specific setup.
        # Let's make it explicit for clarity in this example.
        # For a balanced series, you might alternate home team or have a fixed home team for the series.
        # Here, we'll alternate for demonstration within the 4 games.
        if i <= num_games_in_series / 2:  # First half of series, team_1 is away
            away_team, home_team = team_1, team_2
        else:  # Second half of series, team_2 is away
            away_team, home_team = team_2, team_1

        if log_callback:
            log_callback(
                f"  Starting game {i} of series {series_number}: {away_team.name} (Away) vs {home_team.name} (Home)")

        # Call play_game. Ensure it's imported and works as expected.
        # The play_game function returns: away_result, home_result, game_log, away_inning_runs, home_inning_runs
        away_result, home_result, game_log_entries, _, _ = play_game(away_team, home_team)

        if log_callback:
            final_score_info = "Score N/A"
            # Attempt to get score from game results or log
            if away_result and home_result:
                final_score_info = f"Score: {away_team.name} {away_result.get('runs_scored', 0)} - {home_team.name} {home_result.get('runs_scored', 0)}"
            elif game_log_entries and isinstance(game_log_entries[-1], str) and (
                    "--- Game End" in game_log_entries[-1] or "Walk-Off" in game_log_entries[-1]):
                # Try to parse from a common game end log message format
                final_score_info = game_log_entries[-1].split("---")[1].strip() if "--- Game End" in game_log_entries[
                    -1] else game_log_entries[-1]

            log_callback(f"  Game {i} of series {series_number} End. {final_score_info}")

        # Call post_game_team_cleanup for the actual teams involved in the game
        away_team.post_game_team_cleanup()
        home_team.post_game_team_cleanup()

    if log_callback:
        log_callback(f"Completed Series {series_number} between {team_1.name} and {team_2.name}.")


def play_season(teams, log_callback=None):  # Added log_callback parameter
    """
    Simulates a full season where teams play each other.
    Args:
        teams (list): List of Team objects.
        log_callback (function, optional): Function to call for logging messages.
    """
    if log_callback:
        log_callback("Beginning of season play...")

    team_pairs = list(itertools.combinations(teams, 2))

    # Calculate total number of series sets (each pair plays "home and home" series)
    total_series_sets = len(team_pairs)
    current_series_set_count = 0

    # Each "series set" consists of team_1 hosting team_2, and team_2 hosting team_1
    # If play_series handles 4 games with fixed home/away, then two calls to play_series are needed per pair.
    # The series_number should be unique for each 4-game block.

    series_counter = 0  # Overall counter for individual 4-game series

    for team_1, team_2 in team_pairs:
        current_series_set_count += 1
        if log_callback:
            log_callback(
                f"--- Simulating Series Set {current_series_set_count}/{total_series_sets} for {team_1.name} and {team_2.name} ---")

        # First series of the pair (e.g., team_1 is "primary", team_2 is "secondary")
        series_counter += 1
        play_series(team_1, team_2,
                    series_number=series_counter,
                    total_series=total_series_sets * 2,  # Total individual 4-game series
                    log_callback=log_callback)

        # Second series of the pair (e.g., team_2 is "primary", team_1 is "secondary")
        series_counter += 1
        play_series(team_2, team_1,
                    series_number=series_counter,
                    total_series=total_series_sets * 2,  # Total individual 4-game series
                    log_callback=log_callback)

    if log_callback:
        log_callback(f"Season play complete. Total individual series played: {series_counter}.")


def preseason(teams, log_callback=None):
    if log_callback: log_callback("Executing pre-season...")
    for team in teams:
        # Ensure team_stats exists; it should be initialized with the Team object
        if not hasattr(team, 'team_stats') or team.team_stats is None:
            from stats import TeamStats  # Assuming TeamStats is in stats.py
            team.team_stats = TeamStats()
        team.team_stats.reset_for_new_season()
    if log_callback: log_callback("Pre-season complete. Team stats reset for the new season.")
    # return teams # teams are modified in-place


def postseason(teams, log_callback=None):  # 'teams' here are the survivors
    if log_callback: log_callback("Executing post-season stat reset for surviving teams...")
    for team in teams:
        if not hasattr(team, 'team_stats') or team.team_stats is None:
            from stats import TeamStats
            team.team_stats = TeamStats()
        team.team_stats.reset_for_new_season()  # Resets for the *next* season
    if log_callback: log_callback("Post-season stat reset for survivors complete.")
    # return teams # teams are modified in-place

def check_continue(teams):
    choice = input("Press enter to run it again, press N to quit: ").strip().lower()
    if choice == '':
        main(teams)
    else:
        exit(0)


def get_formatted_season_leaders(all_players_list, n=10, player_type="both"):
    """
    Generates a formatted string of the top n leaders in various statistics.
    Players in all_players_list are expected to have a `season_stats` attribute.

    Args:
        all_players_list (list): List of player objects (batters and/or pitchers).
        n (int): Number of top players to display for each category.
        player_type (str): "batting", "pitching", or "both".

    Returns:
        str: A multi-line string containing the formatted leaderboards.
    """
    output_lines = []

    # Stat Definitions: (stat_attribute_name, display_name, display_format_str, is_calculated_method, min_qualifier_value)
    # For rate stats, min_qualifier_value is the threshold (e.g., min PA or min Outs Rec).
    # For counting stats, min_qualifier_value is often 0 or not strictly used for filtering but for context.
    # The 'n' parameter here is for the number of games used to calculate typical qualifiers.
    # For example, if a season has 'N_GAMES', then MIN_PA = N_GAMES * 2.0 (or 3.1 in MLB)
    # and MIN_IP_OUTS = N_GAMES * 3 (for 1 IP per game).
    # The original tournament.py used 'n' (top N players) for this, which is a bit unusual but we'll keep it.
    # So, if n=10, min PA qualifier is 31, min IP qualifier (in outs) is 30.

    MIN_PA_QUALIFIER = 3.1 * 10  # Consistent with original display_season_leaders logic (n=10 default)
    MIN_IP_OUTS_QUALIFIER = 1.0 * 10 * 3  # Consistent with original (n=10 default for games, 3 outs/IP)

    batting_stats_definitions = [
        ("plate_appearances", "Plate Appearances (PA)", "{:.0f}", False, 0),
        ("at_bats", "At Bats (AB)", "{:.0f}", False, 0),
        ("runs_scored", "Runs (R)", "{:.0f}", False, 0),
        ("hits", "Hits (H)", "{:.0f}", False, 0),
        ("singles", "Singles (1B)", "{:.0f}", False, 0),
        ("doubles", "Doubles (2B)", "{:.0f}", False, 0),
        ("triples", "Triples (3B)", "{:.0f}", False, 0),
        ("home_runs", "Home Runs (HR)", "{:.0f}", False, 0),
        ("walks", "Walks (BB)", "{:.0f}", False, 0),
        ("strikeouts", "Strikeouts (SO Bat)", "{:.0f}", False, 0),
        ("rbi", "Runs Batted In (RBI)", "{:.0f}", False, 0),
        ("calculate_avg", "Batting Average (AVG)", "{}", True, MIN_PA_QUALIFIER),
        ("calculate_obp", "On-Base Pct (OBP)", "{}", True, MIN_PA_QUALIFIER),
        ("calculate_slg", "Slugging Pct (SLG)", "{}", True, MIN_PA_QUALIFIER),
        ("calculate_ops", "On-Base + Slugging (OPS)", "{}", True, MIN_PA_QUALIFIER)
    ]

    pitching_stats_definitions = [
        ("batters_faced", "Batters Faced (BF)", "{:.0f}", False, 0),
        ("outs_recorded", "Outs Recorded", "{:.0f}", False, 0),  # Raw outs for sorting if needed
        ("strikeouts_thrown", "Strikeouts (SO Pit)", "{:.0f}", False, 0),
        ("walks_allowed", "Walks Allowed (BB)", "{:.0f}", False, 0),
        ("hits_allowed", "Hits Allowed (H)", "{:.0f}", False, 0),
        ("home_runs_allowed", "Home Runs Allowed (HR)", "{:.0f}", False, 0),
        ("runs_allowed", "Runs Allowed (R)", "{:.0f}", False, 0),
        ("earned_runs_allowed", "Earned Runs (ER)", "{:.0f}", False, 0),
        ("outs_recorded", "Innings Pitched (IP)", "{}", False, MIN_IP_OUTS_QUALIFIER),  # Special display for IP
        ("calculate_era", "Earned Run Average (ERA)", "{:.2f}", True, MIN_IP_OUTS_QUALIFIER),
        ("calculate_whip", "Walks+Hits per IP (WHIP)", "{:.2f}", True, MIN_IP_OUTS_QUALIFIER),
        ("calculate_k_per_9", "Strikeouts per 9 Inn (K/9)", "{:.2f}", True, MIN_IP_OUTS_QUALIFIER)
    ]

    def get_stat_value_for_sorting(player, stat_name, is_calculated_method):
        """Gets stat value, converting to float for sorting where appropriate."""
        if not hasattr(player, 'season_stats') or player.season_stats is None:
            return 0.0 if is_calculated_method and stat_name in ["calculate_era", "calculate_whip",
                                                                 "calculate_k_per_9"] else (
                0.0 if is_calculated_method else 0)

        stats_obj = player.season_stats
        if is_calculated_method:
            val_str = getattr(stats_obj, stat_name)()  # e.g., ".300" or "3.45"
            try:
                return float(val_str)
            except ValueError:  # Handle non-numeric strings like ".---"
                return -1.0 if stat_name == "calculate_era" else 0.0  # Low ERA is good, so -1 better than 0 for sorting
        else:
            if stat_name == "hits": stats_obj.update_hits()  # Ensure hits are current
            return getattr(stats_obj, stat_name, 0)

    def format_stat_for_display(player, stat_name_key, raw_value_for_display, display_format_str, is_calculated_method):
        """Formats the stat for display, using specific methods for certain stats like IP or AVG."""
        if not hasattr(player, 'season_stats') or player.season_stats is None:
            return "N/A"

        stats_obj = player.season_stats
        if stat_name_key == "outs_recorded" and display_format_str == "{}":  # IP display
            return stats_obj.get_formatted_ip()
        elif is_calculated_method and stat_name_key in ["calculate_avg", "calculate_obp", "calculate_slg",
                                                        "calculate_ops"]:
            return getattr(stats_obj, stat_name_key)()  # Get the pre-formatted string like ".300"
        elif isinstance(raw_value_for_display, (float, int)):
            return display_format_str.format(raw_value_for_display)
        return str(raw_value_for_display)  # Fallback

    def generate_leaders_for_category(players, stat_definitions, category_header):
        output_lines.append(f"\n{'=' * 15} {category_header} LEADERS {'=' * 15}\n")

        for stat_key, display_name, disp_fmt, is_calc, min_qual_val in stat_definitions:
            output_lines.append(f"{display_name}:")

            # Filter qualified players
            qualified_players = []
            if stat_key in ["calculate_avg", "calculate_obp", "calculate_slg", "calculate_ops"]:
                qualified_players = [p for p in players if hasattr(p,
                                                                   'season_stats') and p.season_stats and p.season_stats.plate_appearances >= min_qual_val]
            elif stat_key in ["calculate_era", "calculate_whip", "calculate_k_per_9"] or \
                    (stat_key == "outs_recorded" and display_name == "Innings Pitched (IP)"):
                qualified_players = [p for p in players if hasattr(p,
                                                                   'season_stats') and p.season_stats and p.season_stats.outs_recorded >= min_qual_val]
            else:  # Counting stats, no specific qualifier beyond having stats
                qualified_players = [p for p in players if hasattr(p, 'season_stats') and p.season_stats]

            if not qualified_players:
                output_lines.append("  No qualified players.")
                output_lines.append("")
                continue

            # Sort players
            sort_reverse = not (stat_key == "calculate_era")  # Lower ERA is better

            sorted_leaders = sorted(
                qualified_players,
                key=lambda p_obj: get_stat_value_for_sorting(p_obj, stat_key, is_calc),
                reverse=sort_reverse
            )

            for i, player_obj in enumerate(sorted_leaders[:n]):
                # Get the value again, this time for display formatting
                # For calculated methods, we might want the original string if it's already formatted (like AVG)
                # For others, we use the value obtained for sorting.
                value_to_format = get_stat_value_for_sorting(player_obj, stat_key, is_calc)
                display_value_str = format_stat_for_display(player_obj, stat_key, value_to_format, disp_fmt, is_calc)

                year_set = f"{player_obj.year}{player_obj.set}" if (player_obj.year or player_obj.set) else ""
                team_name_str = f" ({player_obj.team_name})" if hasattr(player_obj,
                                                                        'team_name') and player_obj.team_name else ""

                output_lines.append(f"  {i + 1}. {player_obj.name} {year_set}{team_name_str}: {display_value_str}")
            output_lines.append("")

    # Separate players by type for processing
    batting_player_pool = [p for p in all_players_list if hasattr(p, 'on_base')]  # Batters have 'on_base'
    pitching_player_pool = [p for p in all_players_list if hasattr(p, 'control')]  # Pitchers have 'control'

    if player_type.lower() in ["batting", "both"] and batting_player_pool:
        generate_leaders_for_category(batting_player_pool, batting_stats_definitions, "BATTING")

    if player_type.lower() in ["pitching", "both"] and pitching_player_pool:
        generate_leaders_for_category(pitching_player_pool, pitching_stats_definitions, "PITCHING")

    if not output_lines:
        return "No leaderboard data to display."

    return "\n".join(output_lines)

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

def main(all_teams,num_teams = 20):
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
    all_teams = list(filter(lambda x: x.team_stats.wins >= x.team_stats.losses, all_teams))
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

def init(num_teams=20):
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
