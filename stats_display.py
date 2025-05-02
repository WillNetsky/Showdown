# stats_display.py
# Functions to display formatted stats in the console

from entities import Team

def display_linescore(team1_name, team2_name, team1_inning_runs, team2_inning_runs, final_score1, final_score2):
    """
    Prints a formatted linescore for the game.

    Args:
        team1_name (str): Name of the first team (Away).
        team2_name (str): Name of the second team (Home).
        team1_inning_runs (list): List of runs scored by team1 in each inning.
        team2_inning_runs (list): List of runs scored by team2 in each inning.
        final_score1 (int): Final score for team1.
        final_score2 (int): Final score for team2.
    """
    print("\n--- Linescore ---")

    # Determine the maximum number of innings played
    max_innings = max(len(team1_inning_runs), len(team2_inning_runs))

    # Determine the max team name length
    max_team_length = max(len(team1_name), len(team2_name))

    # Create the header row
    header = ["Team"+" "*(max_team_length-4)] + [str(i + 1) for i in range(max_innings)] + ["R", "H"] # Add H column placeholder
    print(" | ".join(header))
    print("-" * (len(" | ".join(header)) + 2)) # Separator line

    # Print Team 1 (Away) row
    team1_row = [team1_name] + [str(runs) for runs in team1_inning_runs]
    # Pad with empty strings if fewer than max_innings
    team1_row += [""] * (max_innings - len(team1_inning_runs))
    team1_row += [str(final_score1), "?"] # Add R and H (H is placeholder for now)
    print(" | ".join(team1_row))

    # Print Team 2 (Home) row
    team2_row = [team2_name] + [str(runs) for runs in team2_inning_runs]
    # Pad with empty strings if fewer than max_innings
    team2_row += [""] * (max_innings - len(team2_inning_runs))
    team2_row += [str(final_score2), "?"] # Add R and H (H is placeholder for now)
    print(" | ".join(team2_row))
    print("-" * (len(" | ".join(header)) + 2)) # Separator line


def display_boxscore(team: Team):
    """
    Prints a formatted boxscore for a given team.

    Args:
        team (Team): The Team object to display the boxscore for.
    """
    print(f"\n--- {team.name} Boxscore ---")

    # Batting Stats Header
    # Added OPS+ column placeholder
    print("\nBatting:")
    # Adjusted spacing for batting stats
    print(f"{'Name':<20} {'Pos':<5} {'PA':<3} {'AB':<3} {'R':<3} {'H':<3} {'RBI':<3} {'BB':<3} {'SO':<4} {'AVG':<4} {'OBP':<4} {'SLG':<4} {'OPS':<4}")
    print("-" * 79) # Adjusted separator length

    # Display Batting Stats for Starters and Bench
    for player in team.batters + team.bench:
        # Calculate derived stats
        avg = player.calculate_avg()
        obp = player.calculate_obp()
        slg = player.calculate_slg()
        ops = player.calculate_ops()

        # Format and print batting stats
        print(f"{player.name:<20} {player.position:<5} {player.plate_appearances:<3} {player.at_bats:<3} {player.runs_scored:<3} {player.hits:<3} {player.rbi:<3} {player.walks:<3} {player.strikeouts:<3} {avg} {obp} {slg} {ops}")

    # Pitching Stats Header
    print("\nPitching:")
    # Adjusted spacing for pitching stats
    print(f"{'Name':<20} {'Role':<5} {'IP':<5} {'BF':<4} {'R':<3} {'ER':<3} {'H':<3} {'BB':<3} {'SO':<3} {'ERA':<5} {'WHIP':<5}")
    print("-" * 70) # Adjusted separator length

    # Display Pitching Stats for all Pitchers
    for pitcher in team.used_starters+team.used_relievers+team.used_closers:
        # Calculate derived stats
        era = pitcher.calculate_era()
        whip = pitcher.calculate_whip()
        formatted_ip = pitcher.get_formatted_ip() # Use the formatted IP

        # Format and print pitching stats
        print(f"{pitcher.name:<20} {pitcher.team_role:<5} {formatted_ip:<5} {pitcher.batters_faced:<4} {pitcher.runs_allowed:<3} {pitcher.earned_runs_allowed:<3} {pitcher.hits_allowed:<3} {pitcher.walks_allowed:<3} {pitcher.strikeouts_thrown:<3} {era:<5.2f} {whip:<5.2f}")

