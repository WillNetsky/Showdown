# team_management.py
# Contains functions for loading players from data and creating teams.

import random
import csv
import os
import glob

# Import necessary classes and constants
from entities import Batter, Pitcher # Import Batter and Pitcher classes
from team import Team # Import Team class
from constants import POSITION_MAPPING, STARTING_POSITIONS, MIN_TEAM_POINTS, MAX_TEAM_POINTS

# Helper function to load players from a CSV file
def load_players_from_csv(filepath):
    """
    Loads player data from a CSV file and creates Batter or Pitcher objects.
    Infers player type based on the filename ("batters" or "pitchers").
    Includes flexible header matching and error handling.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        list: A list of Batter or Pitcher objects.
    """
    players = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            csv_headers = [header.strip() for header in reader.fieldnames] if reader.fieldnames else []

            # Create a mapping from lowercase CSV headers to original headers
            header_map = {header.lower(): header for header in csv_headers}

            # Determine player type based on filename
            filename = os.path.basename(filepath).lower()
            is_batter_file = 'batters' in filename
            is_pitcher_file = 'pitchers' in filename

            if not is_batter_file and not is_pitcher_file:
                 print(f"Warning: Cannot determine player type from filename '{filename}'. Skipping file.")
                 return [] # Return empty list if type cannot be determined

            row_count = 0
            for row in reader:
                row_count += 1
                # --- Start Loading Debugging (Reduced) ---
                # print(f"Processing row {row_count}: {row}") # Too verbose, uncomment if needed
                # --- End Loading Debugging ---

                try:
                    # Get common data
                    player_name = row.get(header_map.get('name', 'Name'), 'Unknown Player').strip()

                    # --- Position Loading Logic ---
                    player_position_raw = ''
                    # Define keys to try based on file type, prioritizing the most likely ones first
                    if is_batter_file:
                        pos_keys_to_try = ['pos1', 'pos2', 'pos3', 'pos4', 'pos', 'position']
                    elif is_pitcher_file:
                        pos_keys_to_try = ['pos', 'pos2', 'pos3', 'pos4', 'position'] # Keep existing for pitchers

                    # print(f"Attempting to load position for {player_name} (Row {row_count})...") # Commented out for cleaner output
                    for key in pos_keys_to_try:
                        csv_key = header_map.get(key.lower())
                        if csv_key and row.get(csv_key):
                            raw_value = row.get(csv_key).strip()
                            # Check if the raw value is 'NULL' case-insensitively
                            if raw_value.upper() != 'NULL':
                                player_position_raw = raw_value
                                # print(f"  Attempting position key '{key}', found CSV key '{csv_key}', raw value: '{raw_value}' -> Using '{player_position_raw}'") # Uncomment if needed
                                if player_position_raw:
                                    break # Found a valid position, stop checking
                            # else:
                                # print(f"  Attempting position key '{key}', found CSV key '{csv_key}', raw value: '{raw_value}' -> Skipping 'NULL'") # Uncomment if needed
                        # else:
                            # print(f"  Attempting position key '{key}', CSV key '{csv_key}' not found or value is empty.") # Uncomment if needed


                    if not player_position_raw:
                         player_position_raw = 'Unknown' # Default if no valid position found
                         # print(f"  No valid position found for {player_name}, defaulting to '{player_position_raw}'") # Uncomment if needed
                    # print(f"  Final raw position for {player_name}: '{player_position_raw}'") # Commented out for cleaner output
                    # --- End Position Loading Logic ---


                    # Get year and set from CSV, providing default empty strings
                    year_str = row.get(header_map.get('year', 'year'), '').strip()
                    set_str = row.get(header_map.get('set', 'set'), '').strip()

                    # Attempt to convert points, which should be in both files
                    pts_str = row.get(header_map.get('pts', 'Pts'), '0').strip()
                    try:
                        pts = int(pts_str)
                    except ValueError:
                        print(f"Error converting points data in row {row_count} for player {player_name}: '{pts_str}' is not a valid integer. Skipping row.")
                        continue # Skip this row if points conversion fails


                    if is_batter_file:
                        # Get and convert batter-specific stats
                        onbase_str = row.get(header_map.get('onbase', 'On Base'), '0').strip()
                        so_str = row.get(header_map.get('so', 'SO'), '0').strip()
                        gb_str = row.get(header_map.get('gb', 'GB'), '0').strip()

                        # --- Loading FB, B1, B1P using confirmed headers ---

                        # FB Loading (prioritize 'fb', fallback to 'FB') - Syntax fixed
                        fb_str = row.get(header_map.get('fb', header_map.get('FB', '0')), '0').strip()
                        # print(f"  Debug Loading for {player_name} (Row {row_count}): FB Raw value: '{fb_str}'") # Uncomment for debugging

                        # B1 Loading (prioritize 'b1', fallback to '1B') - Syntax fixed
                        b1_str = row.get(header_map.get('b1', header_map.get('1B', '0')), '0').strip()
                        # print(f"  Debug Loading for {player_name} (Row {row_count}): B1 Raw value: '{b1_str}'") # Uncomment for debugging

                        # B1P Loading (prioritize 'b1p', fallback to '1BP') - Syntax fixed
                        b1p_str = row.get(header_map.get('b1p', header_map.get('1BP', '0')), '0').strip()
                        # print(f"  Debug Loading for {player_name} (Row {row_count}): B1P Raw value: '{b1p_str}'") # Uncomment for debugging

                        # --- End Loading FB, B1, B1P ---


                        bb_str = row.get(header_map.get('bb', 'BB'), '0').strip()
                        b2_str = row.get(header_map.get('b2', '2B'), '0').strip() # Map 'b2' from CSV to '2B'
                        b3_str = row.get(header_map.get('b3', '3B'), '0').strip() # Map 'b3' from CSV to '3B')
                        hr_str = row.get(header_map.get('hr', 'HR'), '0').strip()

                        try:
                            onbase = int(onbase_str)
                            so = int(so_str)
                            gb = int(gb_str)
                            fb = int(fb_str) # Use the potentially updated fb_str
                            bb = int(bb_str)
                            b1 = int(b1_str) # Use the potentially updated b1_str
                            b1p = int(b1p_str) # Use the potentially updated b1p_str
                            b2 = int(b2_str)
                            b3 = int(b3_str)
                            hr = int(hr_str)
                        except ValueError as e:
                            print(f"Error converting batter numeric data in row {row_count} for player {player_name}: {e}. Data: {row}. Skipping row.")
                            continue # Skip this row if batter numeric conversion fails


                        player = Batter(
                            name=player_name,
                            position=player_position_raw, # Store the raw position string from CSV
                            onbase=onbase, # This is correct here for loading
                            so=so,
                            gb=gb,
                            fb=fb,
                            bb=bb,
                            b1=b1,
                            b1p=b1p,
                            b2=b2,
                            b3=b3,
                            hr=hr,
                            pts=pts,
                            year=year_str, # Pass year to Batter constructor
                            set=set_str # Pass set to Batter constructor
                        )
                        players.append(player)

                    elif is_pitcher_file:
                         # Get and convert pitcher-specific stats
                         control_str = row.get(header_map.get('control', 'Control'), '0').strip()
                         pu_str = row.get(header_map.get('pu', 'PU'), '0').strip()
                         so_str = row.get(header_map.get('so', 'SO'), '0').strip() # Pitchers also have SO
                         gb_str = row.get(header_map.get('gb', 'GB'), '0').strip() # Pitchers also have GB
                         fb_str = row.get(header_map.get('fb', 'FB'), '0').strip() # Pitchers also have FB (mapped from fo)
                         bb_str = row.get(header_map.get('bb', 'BB'), '0').strip() # Pitchers also have BB
                         b1_str = row.get(header_map.get('b1', '1B'), '0').strip() # Pitchers also have 1B (mapped from bi)
                         b2_str = row.get(header_map.get('b2', '2B'), '0').strip() # Pitchers also have 2B (mapped from b2)
                         hr_str = row.get(header_map.get('hr', 'HR'), '0').strip() # Pitchers also have HR
                         ip_limit_str = row.get(header_map.get('ip limit', 'IP Limit'), '').strip()
                         # Also check for 'ip' if 'ip limit' isn't found
                         if not ip_limit_str:
                              ip_limit_str = row.get(header_map.get('ip', 'ip'), '').strip()


                         try:
                              control = int(control_str)
                              pu = int(pu_str)
                              so = int(so_str) # Convert pitcher SO
                              gb = int(gb_str) # Convert pitcher GB
                              fb = int(fb_str) # Convert pitcher FB
                              bb = int(bb_str) # Convert pitcher BB
                              b1 = int(b1_str) # Convert pitcher 1B
                              b2 = int(b2_str) # Convert pitcher 2B
                              hr = int(hr_str) # Convert pitcher HR
                              ip_limit = float(ip_limit_str) if ip_limit_str else None

                         except ValueError as e:
                              print(f"Error converting pitcher numeric data in row {row_count} for player {player_name}: {e}. Data: {row}. Skipping row.")
                              continue # Skip this row if pitcher numeric conversion fails


                         # Determine pitcher role more specifically from the raw position string
                         pitcher_role = 'P' # Default to generic P
                         # Check for full words "Starter", "Reliever", "Closer" case-insensitively
                         if 'STARTER' in player_position_raw.upper():
                             pitcher_role = 'SP'
                         elif 'RELIEVER' in player_position_raw.upper():
                             pitcher_role = 'RP'
                         elif 'CLOSER' in player_position_raw.upper():
                             pitcher_role = 'CL'

                         player = Pitcher(
                            name=player_name,
                            position=pitcher_role, # Store the determined role (SP, RP, CL, or P)
                            control=control,
                            pu=pu,
                            so=so,
                            gb=gb,
                            fb=fb,
                            bb=bb,
                            b1=b1,
                            b2=b2,
                            hr=hr,
                            pts=pts,
                            ip_limit=ip_limit, # Pass the IP limit (from 'ip' or 'IP Limit')
                            year=year_str, # Pass year to Pitcher constructor
                            set=set_str # Pass set to Pitcher constructor
                        )
                         players.append(player)


                except Exception as e:
                    # Catch any other unexpected errors during row processing
                    print(f"An unexpected error occurred while processing row {row_count} for player {player_name}: {e}. Row data: {row}. Skipping row.")

    except FileNotFoundError:
        print(f"Error: CSV file not found at {filepath}")
        return None
    except Exception as e:
        # Catch errors related to opening or reading the file itself
        print(f"An unexpected error occurred while reading the CSV file {filepath}: {e}")
        return None

    print(f"Successfully loaded {len(players)} players from {filepath}")
    return players

# Function to create a random team based on points and position requirements
def create_random_team(all_players, team_name, min_points, max_points):
    """
    Creates a random team (8 fielding starters, 1 DH, 1 bench, 4 SP, 6 RP/CL) from a list of players,
    adhering to position requirements and total points limits.
    Creates new player instances for each team to ensure independent stats tracking.
    Generates a batting order for starters based on descending points.

    Args:
        all_players (list): A list of all available Batter and Pitcher objects.
        team_name (str): The name for the new team.
        min_points (int): The minimum total points for the team.
        max_points (int): The maximum total points for the team.

    Returns:
        Team or None: A randomly generated Team object or None if team creation fails.
    """
    # Separate players by type
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]

    # Separate pitchers by role
    available_sps = [p for p in available_pitchers if p.position == 'SP']
    available_rps_cls = [p for p in available_pitchers if p.position in ['RP', 'CL', 'P']] # Include generic P for RP/CL pool

    # Define the required fielding positions (excluding DH and P)
    FIELDING_POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']

    # Ensure enough players are available to even attempt team creation
    # Need 8 fielding batters + 1 DH + 1 bench = 10 batters total
    if len(available_batters) < 10 or len(available_sps) < 4 or len(available_rps_cls) < 6:
        print(f"Error: Not enough players available to form a team with the required roster size (10 Batters, 4 SP, 6 RP/CL).")
        print(f"Available Batters: {len(available_batters)}, Available SP: {len(available_sps)}, Available RP/CL/P: {len(available_rps_cls)}")
        return None

    print(f"Attempting to create team {team_name} within points range [{min_points}, {max_points}]...")
    print(f"Available Batters: {len(available_batters)}, Available SP: {len(available_sps)}, Available RP/CL/P: {len(available_rps_cls)}")


    # Attempt to create a valid team within the point range and roster size
    for attempt in range(100): # Reduced attempts to 100
        selected_starters = [] # This will hold the 9 starters (8 fielders + 1 DH)
        selected_bench = []
        selected_sps = []
        selected_rps = []
        selected_cls = []
        used_players_this_attempt = set() # Keep track of ORIGINAL players used in THIS attempt to prevent duplicates on the same team

        # --- Select Pitchers (exactly 4 SP and exactly 6 RP/CL) ---

        # Select Starting Pitchers (4)
        current_sps_pool = list(available_sps) # Create a mutable copy
        random.shuffle(current_sps_pool)
        # Ensure we don't try to pop more than available
        num_sps_to_select = min(4, len(current_sps_pool))
        sps_for_team = [] # Temporary list to hold selected SPs for this attempt
        for _ in range(num_sps_to_select): # Corrected loop range variable
            if not current_sps_pool: break # Stop if pool is empty
            sp = current_sps_pool.pop(0)
            # Create a new Pitcher instance with the same attributes
            new_sp = Pitcher(sp.name, sp.position, sp.control, sp.pu, sp.so, sp.gb, sp.fb, sp.bb, sp.b1, sp.b2, sp.hr, sp.pts, sp.ip_limit, sp.year, sp.set)
            sps_for_team.append(new_sp)
            used_players_this_attempt.add(sp) # Add the original player to the used set

        if len(sps_for_team) < 4:
            # Not enough dedicated SPs, team creation failed for this attempt
            # print(f"Attempt {attempt+1}: Failed to select 4 SPs. Selected {len(sps_for_team)}. Retrying...") # Commented out for cleaner output
            continue # Not enough dedicated SPs, try again
        selected_sps = sps_for_team # Assign the list of new SP instances


        # Select Relievers and Closers (6 total)
        current_rps_cls_pool = [p for p in available_rps_cls if p not in used_players_this_attempt] # Pool of available RP/CL/P not already used as SP
        random.shuffle(current_rps_cls_pool)

        # Select 6 RP/CL from the available pool
        # Ensure we don't try to pop more than available
        num_rps_cls_to_select = min(6, len(current_rps_cls_pool))
        rps_cls_for_team = [] # Temporary list to hold selected RP/CLs for this attempt
        for _ in range(num_rps_cls_to_select):
             if not current_rps_cls_pool: break # Stop if pool is empty
             rp_cl = current_rps_cls_pool.pop(0)
             # Create a new Pitcher instance
             new_rp_cl = Pitcher(rp_cl.name, rp_cl.position, rp_cl.control, rp_cl.pu, rp_cl.so, rp_cl.gb, rp_cl.fb, rp_cl.bb, rp_cl.b1, rp_cl.b2, rp_cl.hr, rp_cl.pts, rp_cl.ip_limit, rp_cl.year, rp_cl.set)
             if new_rp_cl.position == 'CL':
                  selected_cls.append(new_rp_cl)
             else: # Assumes 'RP' or 'P'
                  selected_rps.append(new_rp_cl)
             used_players_this_attempt.add(rp_cl) # Add the original player to the used set


        # Ensure exactly 6 RP/CL are selected
        if len(selected_rps) + len(selected_cls) != 6:
             # print(f"Attempt {attempt+1}: Incorrect number of RP/CL selected ({len(selected_rps) + len(selected_cls)}). Retrying...") # Commented out for cleaner output
             continue # Incorrect number of RP/CL selected, try again


        # --- Select Batters (exactly 8 fielding starters + 1 DH and exactly 1 bench) ---

        selected_fielding_starters_dict = {} # Use a dict to ensure one player per required fielding position
        available_batters_for_selection = [b for b in available_batters if b not in used_players_this_attempt] # Batters not used as pitchers

        # Prioritize players with specific single positions first for fielding
        single_position_fielders = [b for b in available_batters_for_selection if '/' not in b.position and b.position in FIELDING_POSITIONS]
        multi_position_fielders = [b for b in available_batters_for_selection if '/' in b.position or b.position not in FIELDING_POSITIONS] # Includes OF, IF, etc.

        random.shuffle(single_position_fielders)
        random.shuffle(multi_position_fielders)

        # print(f"Attempt {attempt+1}: Selecting 8 Fielding Starters...") # Commented out for cleaner output
        # Try to fill required fielding positions with single-position players first
        for required_pos in FIELDING_POSITIONS:
            if required_pos not in selected_fielding_starters_dict:
                # print(f"  Attempting to fill {required_pos}...") # Commented out for cleaner output
                found_for_pos = False
                # Try single-position players first
                for batter in single_position_fielders:
                    # print(f"    Considering single-position player {batter.name} ({batter.position})...") # Commented out for cleaner output
                    if batter not in used_players_this_attempt:
                        # print(f"      Player not used in this attempt.") # Commented out for cleaner output
                        if batter.can_play(required_pos):
                            # print(f"      Player can play {required_pos}. Selecting {batter.name}.") # Commented out for cleaner output
                            # Create a new Batter instance
                            new_batter = Batter(batter.name, batter.position, batter.on_base, batter.so, batter.gb, batter.fb, batter.bb, batter.b1, batter.b1p, batter.b2, batter.b3, batter.hr, batter.pts, batter.year, batter.set)
                            selected_fielding_starters_dict[required_pos] = new_batter
                            used_players_this_attempt.add(batter) # Add the original player to the used set
                            found_for_pos = True
                            break # Move to the next required position
                        # else:
                            # print(f"      Player cannot play {required_pos}.") # Commented out for cleaner output
                    # else:
                        # print(f"      Player already used in this attempt.") # Commented out for cleaner output

                if found_for_pos:
                    continue # Move to the next required position if found

                # If not found among single-position players, try multi-position players
                for batter in multi_position_fielders:
                     # print(f"    Considering multi-position player {batter.name} ({batter.position})...") # Commented out for cleaner output
                     if batter not in used_players_this_attempt:
                          # print(f"      Player not used in this attempt.") # Commented out for cleaner output
                          if batter.can_play(required_pos):
                               # print(f"      Player can play {required_pos}. Selecting {batter.name}.") # Commented out for cleaner output
                               # Create a new Batter instance
                               new_batter = Batter(batter.name, batter.position, batter.on_base, batter.so, batter.gb, batter.fb, batter.bb, batter.b1, batter.b1p, batter.b2, batter.b3, batter.hr, batter.pts, batter.year, batter.set)
                               selected_fielding_starters_dict[required_pos] = new_batter
                               used_players_this_attempt.add(batter) # Add the original player to the used set
                               found_for_pos = True
                               break # Move to the next required position
                          # else:
                               # print(f"      Player cannot play {required_pos}.") # Commented out for cleaner output
                     # else:
                          # print(f"      Player already used in this attempt.") # Commented out for cleaner output

                if not found_for_pos:
                    print(f"Attempt {attempt+1}: Failed to find a player for {required_pos} in this attempt.")


        # If we don't have exactly 8 fielding starters, team creation failed
        if len(selected_fielding_starters_dict) != 8:
            print(f"Attempt {attempt+1}: Failed to select 8 fielding starters. Selected {len(selected_fielding_starters_dict)}. Retrying...")
            continue # Not enough fielding starters selected, try again

        # print(f"Attempt {attempt+1}: Successfully selected 8 fielding starters.") # Commented out for cleaner output
        # Convert the dictionary back to a list for the Team object, maintaining a consistent order (e.g., based on FIELDING_POSITIONS)
        selected_starters = [selected_fielding_starters_dict[pos] for pos in FIELDING_POSITIONS]


        # Select Bench Player (1) - any remaining batter not already used for fielding
        available_batters_after_fielding = [b for b in available_batters_for_selection if b not in used_players_this_attempt]
        # print(f"Attempt {attempt+1}: Selecting 1 Bench Player from {len(available_batters_after_fielding)} available batters...") # Commented out for cleaner output
        if available_batters_after_fielding:
            # Ensure we only select one bench player
            bench_player = random.choice(available_batters_after_fielding)
            # Create a new Batter instance for the bench
            new_bench_player = Batter(bench_player.name, bench_player.position, bench_player.on_base, bench_player.so, bench_player.gb, bench_player.fb, bench_player.bb, bench_player.b1, bench_player.b1p, bench_player.b2, bench_player.b3, bench_player.hr, bench_player.pts, bench_player.year, bench_player.set)
            selected_bench.append(new_bench_player)
            used_players_this_attempt.add(bench_player) # Add the original player to the used set
            # print(f"Attempt {attempt+1}: Selected bench player {bench_player.name}.") # Commented out for cleaner output
        else:
             # Not enough batters for bench, team creation failed
             print(f"Attempt {attempt+1}: Failed to select 1 bench player. Selected {len(selected_bench)}. Retrying...")
             continue # No bench player selected, try again

        # Ensure exactly 1 bench player is selected
        if len(selected_bench) != 1:
             print(f"Attempt {attempt+1}: Incorrect number of bench players ({len(selected_bench)}). Retrying...")
             continue # Incorrect number of bench players, try again

        # --- Select Designated Hitter (1) - any remaining available batter ---
        available_batters_after_bench = [b for b in available_batters_for_selection if b not in used_players_this_attempt]
        # print(f"Attempt {attempt+1}: Selecting 1 DH Player from {len(available_batters_after_bench)} available batters...") # Commented out for cleaner output
        if available_batters_after_bench:
            dh_player = random.choice(available_batters_after_bench)
            # Create a new Batter instance for the DH, explicitly setting position to 'DH' for lineup representation
            new_dh_player = Batter(dh_player.name, 'DH', dh_player.on_base, dh_player.so, dh_player.gb, dh_player.fb, dh_player.bb, dh_player.b1, dh_player.b1p, dh_player.b2, dh_player.b3, dh_player.hr, dh_player.pts, dh_player.year, dh_player.set)
            selected_starters.append(new_dh_player) # Add the DH to the starters list
            used_players_this_attempt.add(dh_player) # Add the original player to the used set
            # print(f"Attempt {attempt+1}: Selected DH player {dh_player.name}.") # Commented out for cleaner output
        else:
            # Not enough batters for DH, team creation failed
            print(f"Attempt {attempt+1}: Failed to select 1 DH player. Retrying...")
            continue # No DH player selected, try again


        # --- Sort selected_starters by points in descending order to create the batting order ---
        # This list now contains 8 fielders and 1 DH
        selected_starters.sort(key=lambda batter: batter.pts, reverse=True)
        # print(f"Attempt {attempt+1}: Batting order sorted by points.") # Commented out for cleaner output


        # --- Final Roster Size Check ---
        # Now checking for 8 fielding starters + 1 DH + 1 bench = 10 batters total
        total_batters_selected = len(selected_starters) + len(selected_bench)
        total_pitchers_selected = len(selected_sps) + len(selected_rps) + len(selected_cls)

        if total_batters_selected != 10 or total_pitchers_selected != 10: # Expected 10 batters and 10 pitchers
             # This check should ideally not be needed if the selection logic above is correct,
             # but it's a good safeguard.
             print(f"Attempt {attempt+1}: Roster size mismatch. Batters: {total_batters_selected}, Pitchers: {total_pitchers_selected}. Expected 10 batters and 10 pitchers. Retrying...")
             continue # Roster size incorrect, try again

        # Calculate the total points of the selected team
        current_total_points = sum(p.pts for p in selected_starters + selected_bench + selected_sps + selected_rps + selected_cls)

        # Check if the team's total points are within the allowed range
        if min_points <= current_total_points <= max_points:
            print(f"Successfully created team {team_name} with {current_total_points} points.")
            return Team(team_name, selected_starters, selected_sps, selected_rps, selected_cls, selected_bench)
        else:
            print(f"Attempt {attempt+1}: Team points {current_total_points} outside range [{min_points}, {max_points}]. Retrying...")
            continue # Points outside range, try again

    print(f"Failed to create a valid team within the point range and roster requirements after {attempt+1} attempts.")
    return None # Return None if team creation failed after all attempts
