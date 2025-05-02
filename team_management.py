# team_management.py
# Contains functions for loading players from data and creating teams,
# and saving/loading specific teams using JSON format.
# Updated to load base player data from a single JSON file and improved team creation.
# Fixed SyntaxError in pitcher loading.
# Corrected roster size validation logic.
# Added handling for both 'ip' and 'ip limit (outs)' keys for pitcher IP.
# Added setting of 'team_role' attribute on player objects.
# Added setting of specific defensive 'position' for starting batters.
# --- MODIFIED: Changed save/load format to JSON ---

import random
# Removed csv import as it's no longer used for team save/load
import os
import re # Import regex module
import json # Import json module

# Import necessary classes and constants
from entities import Batter, Pitcher, Team # Import Batter, Pitcher, and Team classes
from constants import STARTING_POSITIONS, MIN_TEAM_POINTS, MAX_TEAM_POINTS

def load_players_from_json(filepath):
    """
    Loads player data from a JSON file and creates Batter or Pitcher objects.
    The JSON file is expected to be a list of player dictionaries, each with a 'type' field.

    Args:
        filepath (str): The path to the JSON file.

    Returns:
        list: A list of Batter or Pitcher objects.
    """
    players = []
    # print(f"Loading players from {filepath}...") # Debug print removed
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            all_players_data = json.load(infile)

        if not isinstance(all_players_data, list):
            print(f"Error: JSON file {filepath} does not contain a list at the top level.")
            return []

        for player_data in all_players_data:
            if not isinstance(player_data, dict):
                print(f"Warning: Skipping non-dictionary entry in JSON file {filepath}: {player_data}")
                continue

            player_type = player_data.get('type')
            name = player_data.get('name', '').strip()
            pts_str = player_data.get('pts', '0').strip()
            year = player_data.get('year', '').strip()
            set_name = player_data.get('set', '').strip()

            if not name or not player_type:
                # print(f"Skipping player with missing Name or Type in {filepath}: {player_data}") # Reduced noise
                continue

            try:
                pts = int(pts_str)
            except ValueError:
                # print(f"Skipping player with invalid Points for {name} in {filepath}: {player_data}") # Reduced noise
                continue

            if player_type == 'batter':
                # Load as Batter
                # Use .get() with default '0' or '' for safety
                position = player_data.get('position', '').strip() # Primary position for batters (raw data)
                onbase_str = player_data.get('onbase', '0').strip()
                so_str = player_data.get('so', '0').strip()
                gb_str = player_data.get('gb', '0').strip()
                fb_str = player_data.get('fb', '0').strip()
                bb_str = player_data.get('bb', '0').strip()
                b1_str = player_data.get('b1', '0').strip()
                b1p_str = player_data.get('b1p', '0').strip()
                b2_str = player_data.get('b2', '0').strip()
                b3_str = player_data.get('b3', '0').strip()
                hr_str = player_data.get('hr', '0').strip()

                # --- Extract additional position and fielding fields ---
                pos1 = player_data.get('pos1', '').strip()
                fld1 = player_data.get('fld1', '').strip()
                pos2 = player_data.get('pos2', '').strip()
                fld2 = player_data.get('fld2', '').strip()
                pos3 = player_data.get('pos3', '').strip()
                fld3 = player_data.get('fld3', '').strip()
                pos4 = player_data.get('pos4', '').strip()
                fld4 = player_data.get('fld4', '').strip()


                try:
                    onbase = int(onbase_str)
                    so = int(so_str)
                    gb = int(gb_str)
                    fb = int(fb_str)
                    bb = int(bb_str)
                    b1 = int(b1_str)
                    b1p = int(b1p_str)
                    b2 = int(b2_str)
                    b3 = int(b3_str)
                    hr = int(hr_str)
                except ValueError:
                     # print(f"Skipping batter with invalid numeric data for {name} in {filepath}: {player_data}") # Reduced noise
                     continue

                # --- Pass additional position fields to Batter constructor ---
                # Note: The 'position' passed here is the raw position from the data source.
                batter = Batter(name, position, onbase, so, gb, fb, bb, b1, b1p, b2, b3, hr, pts, year, set_name,
                                pos1=pos1, fld1=fld1, pos2=pos2, fld2=fld2, pos3=pos3, fld3=fld3, pos4=pos4, fld4=fld4)
                players.append(batter)
                # Debug print for loaded batter position - UNCOMMENTED
                # print(f"  Loaded Batter: {name}, Raw Positions: '{position}', '{pos1}', '{pos2}', '{pos3}', '{pos4}'") # Updated debug print


            elif player_type == 'pitcher':
                # Load as Pitcher
                # --- Use the 'pos' key for pitcher position (raw data) ---
                position = player_data.get('pos', '').strip()
                # --- END CORRECTED ---

                # Use .get() with default '0' or '' for safety
                control_str = player_data.get('control', '0').strip()
                pu_str = player_data.get('pu', '0').strip()
                so_str = player_data.get('so', '0').strip() # Pitchers also have SO
                gb_str = player_data.get('gb', '0').strip() # Pitchers also have GB
                fb_str = player_data.get('fb', '0').strip() # Pitchers also have FB
                bb_str = player_data.get('bb', '0').strip() # Pitchers also have BB
                b1_str = player_data.get('b1', '0').strip() #
                b2_str = player_data.get('b2', '0').strip() #
                hr_str = player_data.get('hr', '0').strip() # Pitchers also have HR allowed


                # --- Handle both 'ip limit (outs)' and 'ip' for IP limit ---
                ip_limit_outs = None
                ip_limit_outs_str = player_data.get('ip limit (outs)', '').strip()
                if ip_limit_outs_str:
                    try:
                        ip_limit_outs = int(ip_limit_outs_str)
                    except ValueError:
                        print(f"Warning: Invalid 'ip limit (outs)' for {name} in {filepath}: {ip_limit_outs_str}. Skipping IP limit.")

                # If 'ip limit (outs)' was not found or invalid, try 'ip'
                if ip_limit_outs is None:
                    ip_str = player_data.get('ip', '').strip()
                    if ip_str:
                        try:
                            # Assume 'ip' is in innings, convert to outs (innings * 3)
                            ip_limit_innings = float(ip_str)
                            ip_limit_outs = int(ip_limit_innings * 3)
                        except ValueError:
                            print(f"Warning: Invalid 'ip' for {name} in {filepath}: {ip_str}. Skipping IP limit.")
                # --- END CORRECTED IP Handling ---


                try:
                    control = int(control_str)
                    pu = int(pu_str)
                    so = int(so_str)
                    gb = int(gb_str)
                    fb = int(fb_str)
                    bb = int(bb_str)
                    b1 = int(b1_str)
                    b2 = int(b2_str)
                    hr = int(hr_str)
                    # ip_limit_outs is now handled above
                except ValueError:
                     # print(f"Skipping pitcher with invalid numeric data for {name} in {filepath}: {player_data}") # Reduced noise
                     continue


                # Note: The 'position' passed here is the raw position from the data source.
                pitcher = Pitcher(name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_limit_outs, year, set_name)
                players.append(pitcher)
                # Debug print for loaded pitcher position - UNCOMMENTED
                # print(f"  Loaded Pitcher: {name}, Raw Position: '{position}'") # Debug print removed


            else:
                print(f"Skipping player with unknown type '{player_type}' for {name} in {filepath}: {player_data}")
                continue


    except FileNotFoundError:
        print(f"Error: Player data file not found at {filepath}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Please check the file format.")
        return []
    except Exception as e:
        print(f"Error loading players from {filepath}: {e}")
        return []

    # print(f"Finished loading {len(players)} players.") # Debug print removed
    return players


def get_next_team_number(teams_dir):
    """
    Finds the next available sequential team number based on existing team files.
    Looks for .json files.

    Args:
        teams_dir (str): The directory containing saved team JSON files.

    Returns:
        int: The next available team number (starting from 1 if no files exist).
    """
    max_number = 0
    # Pattern to match filenames like "Team_X_*.json" and capture the number X
    # --- MODIFIED: Look for .json files ---
    pattern = re.compile(r'Team_(\d+)_.*\.json', re.IGNORECASE)
    # --- END MODIFIED ---

    for filename in os.listdir(teams_dir):
        match = pattern.match(filename)
        if match:
            try:
                team_number = int(match.group(1))
                if team_number > max_number:
                    max_number = team_number
            except ValueError:
                # Ignore files with non-integer numbers in the expected position
                pass

    return max_number + 1


def create_random_team(all_players, team_name, min_points=MIN_TEAM_POINTS, max_points=MAX_TEAM_POINTS, max_attempts=1000):
    """
    Creates a random team from the list of all players, adhering to roster requirements
    and total points limits.
    Includes enhanced debugging for position eligibility and pitcher selection.
    Sets the 'team_role' attribute and the specific defensive 'position' for starting batters.

    Args:
        all_players (list): A list of all available Batter and Pitcher objects.
        team_name (str): The name for the new team (e.g., "Team 1").
        min_points (int): The minimum allowed total points for the team.
        max_points (int): The maximum allowed total points for the team.
        max_attempts (int, optional): The maximum number of attempts to create a valid team. Defaults to 1000.

    Returns:
        Team or None: A valid Team object, or None if a team could not be created within the attempts limit.
    """
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]

    if len(available_batters) < 10 or len(available_pitchers) < 10:
         print("Not enough players available to form a team.")
         return None

    for attempt in range(max_attempts):
        #print(f"\nAttempt {attempt + 1} for team {team_name}...") # Debug print restored
        # Shuffle players for randomness in each attempt
        random.shuffle(available_batters)
        random.shuffle(available_pitchers)

        selected_starters = []
        selected_bench = []
        selected_sps = []
        selected_rps = []
        selected_cls = []

        # Ensure unique players are selected across all positions and pitcher roles
        selected_players_set = set() # To track selected players by name and year/set

        # --- Improved Starting Lineup Selection Logic ---
        temp_batters = list(available_batters) # Work with a copy of available batters
        lineup_positions_to_fill = list(STARTING_POSITIONS) # Start with all required positions

        # Dictionary to store eligible players for each position
        eligible_players_by_position = {}
        #print("Finding eligible players for each starting position:") # Debug print restored
        for pos in lineup_positions_to_fill:
             eligible_players_by_position[pos] = []
             for player in temp_batters:
                  player_id = (player.name, player.year, player.set)
                  # Use the player's can_play method to check eligibility
                  if player_id not in selected_players_set and player.can_play(pos):
                       eligible_players_by_position[pos].append(player)

             #print(f"  {pos}: {len(eligible_players_by_position[pos])} eligible players") # Debug print restored

        # Sort positions by the number of eligible players (least first)
        sorted_positions = sorted(lineup_positions_to_fill, key=lambda pos: len(eligible_players_by_position[pos]))
        #print(f"Positions sorted by scarcity: {[pos for pos in sorted_positions]}") # Debug print restored


        found_all_starters = True
        #print("Selecting starters for sorted positions:") # Debug print restored
        for pos in sorted_positions:
            # Find an available player for this position
            found_player = None
            # Shuffle the eligible players for this position for randomness
            random.shuffle(eligible_players_by_position[pos])

            # Filter eligible players again to ensure they haven't been selected for a *previous* position
            current_eligible_players = [
                player for player in eligible_players_by_position[pos]
                if (player.name, player.year, player.set) not in selected_players_set
            ]
            #print(f"  Considering {len(current_eligible_players)} players for {pos}") # Debug print restored


            for player in current_eligible_players:
                 player_id = (player.name, player.year, player.set)
                 if player_id not in selected_players_set:
                      selected_starters.append(player)
                      selected_players_set.add(player_id)
                      # --- Set team_role for starters ---
                      player.team_role = 'Starter'
                      # --- Set the player's position attribute to the assigned defensive position ---
                      player.position = pos
                      # --- End set team_role and position ---
                      found_player = player
                      #print(f"    Selected {player.name} ({player.position}) for {pos}") # Debug print restored
                      break # Found a player for this position, move to the next sorted position

            if found_player is None:
                 # If no player was found for this position, this attempt fails
                 print(f"Attempt {attempt+1}: Could not find a player for position {pos}. Failing attempt.") # Debug print restored
                 found_all_starters = False
                 break # Break the position filling loop

            # No need to remove the selected player from eligible_players_by_position[pos] here,
            # as we filter using selected_players_set in the next iteration.

        if not found_all_starters or len(selected_starters) < len(STARTING_POSITIONS):
             # If we didn't find a player for every starting position, this attempt is invalid
             print(f"Attempt {attempt+1}: Failed to select a complete starting lineup ({len(selected_starters)}/{len(STARTING_POSITIONS)} selected).") # Debug print restored
             continue # Try the next attempt

        #print(f"Successfully selected {len(selected_starters)} starting batters.") # Debug print restored


        # Select Bench player (1 batter) from remaining batters
        # Filter out batters already selected for the starting lineup
        remaining_batters = [b for b in available_batters if (b.name, b.year, b.set) not in selected_players_set]

        if remaining_batters:
             # Shuffle remaining batters before selecting the bench player
             random.shuffle(remaining_batters)
             bench_player = random.choice(remaining_batters)
             selected_bench.append(bench_player)
             selected_players_set.add((bench_player.name, bench_player.year, bench_player.set))
             # --- Set team_role for bench player ---
             bench_player.team_role = 'Bench'
             # --- End set team_role ---
             #print(f"Selected bench player: {bench_player.name} ({bench_player.position})") # Debug print restored
        else:
             # If no batters left for the bench, this attempt is invalid
             print(f"Attempt {attempt+1}: Not enough batters left for bench. Failing attempt.") # Debug print restored
             continue

        # Select Pitchers (4 SP, 6 RP/CL)
        temp_pitchers = list(available_pitchers) # Work with a copy
        random.shuffle(temp_pitchers) # Shuffle pitchers before selecting

        #print("Selecting pitchers (4 SP, 6 RP/CL)...") # Debug print restored
        # Select Starters (4 SP)
        sp_count = 0
        #print("  Considering pitchers for SP role:") # Debug print restored
        # Iterate through a copy to allow removal
        for pitcher in list(temp_pitchers):
             player_id = (pitcher.name, pitcher.year, pitcher.set)
             # --- Check for 'Starter', 'SP', or 'P' positions ---
             # Added debug print to show pitcher's position and if it matches SP criteria
             is_sp_candidate = pitcher.position in ['Starter', 'SP', 'P']
             # print(f"    Pitcher: {pitcher.name}, Raw Position: '{pitcher.position}', Is SP Candidate: {is_sp_candidate}, Already Selected: {(player_id in selected_players_set)}") # Debug print restored

             if player_id not in selected_players_set and is_sp_candidate:
                  selected_sps.append(pitcher)
                  selected_players_set.add(player_id)
                  # --- Set team_role for SP ---
                  pitcher.team_role = 'SP'
                  # --- End set team_role ---
                  sp_count += 1
                  temp_pitchers.remove(pitcher) # Remove selected pitcher from the pool
                  # print(f"    Selected SP: {pitcher.name} ({pitcher.position})") # Debug print removed
                  if sp_count == 4:
                       break # Selected enough starters

        # If we didn't select enough starters, this attempt is invalid
        if len(selected_sps) < 4:
             print(f"Attempt {attempt+1}: Not enough starting pitchers selected ({len(selected_sps)}/4). Failing attempt.") # Debug print restored
             continue # Try the next attempt

        #print(f"Successfully selected {len(selected_sps)} starting pitchers.") # Debug print restored

        # Select Relievers/Closers (6 RP/CL) from remaining pitchers
        #print("  Considering pitchers for RP/CL roles:") # Debug print restored
        # Iterate through a copy to allow removal
        for pitcher in list(temp_pitchers):
             player_id = (pitcher.name, pitcher.year, pitcher.set)
             # --- Check for 'Reliever', 'Closer', 'RP', 'CL', or 'P' positions ---
             # Added debug print to show pitcher's position and if it matches RP/CL criteria
             is_rp_cl_candidate = pitcher.position in ['Reliever', 'Closer', 'RP', 'CL', 'P']
             # print(f"    Pitcher: {pitcher.name}, Raw Position: '{pitcher.position}', Is RP/CL Candidate: {is_rp_cl_candidate}, Already Selected: {(player_id in selected_players_set)}") # Debug print removed

             if player_id not in selected_players_set and is_rp_cl_candidate:
                  # Simple logic: try to get 1 closer if available, then fill with RP/P
                  if pitcher.position == 'Closer' and len(selected_cls) < 1:
                       selected_cls.append(pitcher)
                       # --- Set team_role for CL ---
                       pitcher.team_role = 'CL'
                       # --- End set team_role ---
                       # print(f"    Selected CL: {pitcher.name} ({pitcher.position})") # Debug print removed
                  elif pitcher.position in ['Reliever', 'RP', 'P']:
                       selected_rps.append(pitcher)
                       # --- Set team_role for RP ---
                       pitcher.team_role = 'RP'
                       # --- End set team_role ---
                       # print(f"    Selected RP: {pitcher.name} ({pitcher.position})") # Debug print removed
                  else:
                       # Debug print for skipping a pitcher that meets RP/CL criteria but not the specific role logic
                       # print(f"    Skipping {pitcher.name} ({pitcher.position}) - does not fit specific RP/CL selection logic for this attempt.") # Debug print removed
                       continue # Skip if it's a Closer and we already have one, or not Reliever/RP/P

                  selected_players_set.add(player_id)
                  # Recalculate rp_cl_count based on the lists
                  rp_cl_count = len(selected_rps) + len(selected_cls)

                  temp_pitchers.remove(pitcher) # Remove selected pitcher from the pool
                  if rp_cl_count == 6:
                       break # Selected enough relievers/closers

        # If we didn't select enough relievers/closers, this attempt is invalid
        if (len(selected_rps) + len(selected_cls)) < 6:
             print(f"Attempt {attempt+1}: Not enough relievers/closers selected ({len(selected_rps) + len(selected_cls)}/6). Failing attempt.") # Debug print restored
             continue # Try the next attempt

        #print(f"Successfully selected {len(selected_rps) + len(selected_cls)} relievers/closers.") # Debug print restored


        # Final check on roster sizes
        # --- CORRECTED: Check the exact number of players in each role list ---
        if len(selected_starters) == 9 and len(selected_bench) == 1 and len(selected_sps) == 4 and (len(selected_rps) + len(selected_cls)) == 6:
        # --- END CORRECTED ---
             # Calculate the total points of the selected team
             current_total_points = sum(p.pts for p in selected_starters + selected_bench + selected_sps + selected_rps + selected_cls)

             # Check if the team's total points are within the allowed range
             if min_points <= current_total_points <= max_points:
                 print(f"Successfully created team {team_name} with {current_total_points} points.") # Debug print restored
                 return Team(team_name, selected_starters, selected_sps, selected_rps, selected_cls, selected_bench)
             else:
                 #print(f"Attempt {attempt+1}: Team points {current_total_points} outside range [{min_points}, {max_points}]. Retrying...") # Debug print restored
                 continue # Points outside range, try again
        else:
             # This else block is for the case where the roster size check fails
             print(f"Attempt {attempt+1}: Roster size mismatch.") # Debug print restored
             print(f"Expected: 9 Starters, 1 Bench, 4 SP, 6 RP/CL. Found: {len(selected_starters)} Starters, {len(selected_bench)} Bench, {len(selected_sps)} SP, {len(selected_rps) + len(selected_cls)} RP/CL.") # Debug print restored
             continue


    print(f"Failed to create a valid team within the point range and roster requirements after {max_attempts} attempts.") # Debug print restored
    return None # Failed to create a team after max attempts

def save_team_to_json(team: Team, filepath: str):
    """
    Saves a Team object's roster and player data to a JSON file.

    Args:
        team (Team): The Team object to save.
        filepath (str): The path to the JSON file to save to.
    """
    try:
        team_data = {
            "name": team.name,
            "total_points": team.total_points,
            "batters": [],
            "starters": [],
            "relievers": [],
            "closers": [],
            "bench": []
        }

        # Serialize batters (Starters and Bench)
        for batter in team.batters: # Starters
            team_data["batters"].append({
                "type": "batter",
                "role": "Starter",
                "name": batter.name,
                "position": batter.position, # Save the assigned defensive position
                "onbase": batter.on_base,
                "so": batter.so,
                "gb": batter.gb,
                "fb": batter.fb,
                "bb": batter.bb,
                "b1": batter.b1,
                "b1p": batter.b1p,
                "b2": batter.b2,
                "b3": batter.b3,
                "hr": batter.hr,
                "pts": batter.pts,
                "year": batter.year,
                "set": batter.set,
                # Include additional positions if they exist on the original player object
                "pos1": getattr(batter, 'pos1', ''),
                "fld1": getattr(batter, 'fld1', ''),
                "pos2": getattr(batter, 'pos2', ''),
                "fld2": getattr(batter, 'fld2', ''),
                "pos3": getattr(batter, 'pos3', ''),
                "fld3": getattr(batter, 'fld3', ''),
                "pos4": getattr(batter, 'pos4', ''),
                "fld4": getattr(batter, 'fld4', ''),
            })
        for batter in team.bench: # Bench
             team_data["bench"].append({
                "type": "batter",
                "role": "Bench",
                "name": batter.name,
                "position": batter.position, # Save the raw position for bench
                "onbase": batter.on_base,
                "so": batter.so,
                "gb": batter.gb,
                "fb": batter.fb,
                "bb": batter.bb,
                "b1": batter.b1,
                "b1p": batter.b1p,
                "b2": batter.b2,
                "b3": batter.b3,
                "hr": batter.hr,
                "pts": batter.pts,
                "year": batter.year,
                "set": batter.set,
                 # Include additional positions if they exist on the original player object
                "pos1": getattr(batter, 'pos1', ''),
                "fld1": getattr(batter, 'fld1', ''),
                "pos2": getattr(batter, 'pos2', ''),
                "fld2": getattr(batter, 'fld2', ''),
                "pos3": getattr(batter, 'pos3', ''),
                "fld3": getattr(batter, 'fld3', ''),
                "pos4": getattr(batter, 'pos4', ''),
                "fld4": getattr(batter, 'fld4', ''),
            })


        # Serialize pitchers (Starters, Relievers, Closers)
        for pitcher in team.starters: # SP
            team_data["starters"].append({
                "type": "pitcher",
                "role": "SP",
                "name": pitcher.name,
                "position": pitcher.position, # Save the raw position
                "control": pitcher.control,
                "pu": pitcher.pu,
                "so": pitcher.so,
                "gb": pitcher.gb,
                "fb": pitcher.fb,
                "bb": pitcher.bb,
                "1b": pitcher.b1, # Use '1b' key to match load_players_from_json
                "2b": pitcher.b2, # Use '2b' key to match load_players_from_json
                "hr": pitcher.hr,
                "ip_limit_outs": pitcher.out_limit, # Save IP limit as outs
                "pts": pitcher.pts,
                "year": pitcher.year,
                "set": pitcher.set,
            })
        for pitcher in team.relievers: # RP
             team_data["relievers"].append({
                "type": "pitcher",
                "role": "RP",
                "name": pitcher.name,
                "position": pitcher.position, # Save the raw position
                "control": pitcher.control,
                "pu": pitcher.pu,
                "so": pitcher.so,
                "gb": pitcher.gb,
                "fb": pitcher.fb,
                "bb": pitcher.bb,
                "1b": pitcher.b1, # Use '1b' key to match load_players_from_json
                "2b": pitcher.b2, # Use '2b' key to match load_players_from_json
                "hr": pitcher.hr,
                "ip_limit_outs": pitcher.out_limit, # Save IP limit as outs
                "pts": pitcher.pts,
                "year": pitcher.year,
                "set": pitcher.set,
            })
        for pitcher in team.closers: # CL
             team_data["closers"].append({
                "type": "pitcher",
                "role": "CL",
                "name": pitcher.name,
                "position": pitcher.position, # Save the raw position
                "control": pitcher.control,
                "pu": pitcher.pu,
                "so": pitcher.so,
                "gb": pitcher.gb,
                "fb": pitcher.fb,
                "bb": pitcher.bb,
                "1b": pitcher.b1, # Use '1b' key to match load_players_from_json
                "2b": pitcher.b2, # Use '2b' key to match load_players_from_json
                "hr": pitcher.hr,
                "ip_limit_outs": pitcher.out_limit, # Save IP limit as outs
                "pts": pitcher.pts,
                "year": pitcher.year,
                "set": pitcher.set,
            })


        # Write the data to a JSON file
        with open(filepath, mode='w', encoding='utf-8') as outfile:
            json.dump(team_data, outfile, indent=4) # Use indent for readability

        print(f"Team '{team.name}' saved to {filepath}")

    except Exception as e:
        print(f"Error saving team '{team.name}' to {filepath}: {e}")


def load_team_from_json(filepath: str):
    """
    Loads a Team object from a JSON file saved by save_team_to_json.
    Sets the 'team_role' attribute and the specific defensive 'position' for starters.

    Args:
        filepath (str): The path to the team JSON file.

    Returns:
        Team or None: The loaded Team object, or None if loading fails.
    """
    name = os.path.splitext(os.path.basename(filepath))[0] # Use filename as team name initially
    batters = [] # Starters will go here
    starters_pitchers = [] # SPs will go here
    relievers = [] # RPs will go here
    closers = [] # CLs will go here
    bench = [] # Bench batters will go here

    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            team_data = json.load(infile)

        team_name_from_file = team_data.get("name", name) # Get name from data, fallback to filename
        loaded_total_points = team_data.get("total_points") # Get total points from data

        # Load batters (Starters and Bench)
        for batter_data in team_data.get("batters", []):
            try:
                role = batter_data.get("role")
                player_name = batter_data.get("name")
                position = batter_data.get("position") # Load the saved position
                onbase = batter_data.get("onbase")
                so = batter_data.get("so")
                gb = batter_data.get("gb")
                fb = batter_data.get("fb")
                bb = batter_data.get("bb")
                b1 = batter_data.get("b1")
                b1p = batter_data.get("b1p")
                b2 = batter_data.get("b2")
                b3 = batter_data.get("b3")
                hr = batter_data.get("hr")
                pts = batter_data.get("pts")
                year = batter_data.get("year")
                set_name = batter_data.get("set")

                 # Include additional positions if they exist in the JSON data
                pos1 = batter_data.get('pos1', '')
                fld1 = batter_data.get('fld1', '')
                pos2 = batter_data.get('pos2', '')
                fld2 = batter_data.get('fld2', '')
                pos3 = batter_data.get('pos3', '')
                fld3 = batter_data.get('fld3', '')
                pos4 = batter_data.get('pos4', '')
                fld4 = batter_data.get('fld4', '')


                if all([player_name, role, position, onbase is not None, so is not None, gb is not None, fb is not None, bb is not None, b1 is not None, b1p is not None, b2 is not None, b3 is not None, hr is not None, pts is not None]):
                    batter = Batter(player_name, position, onbase, so, gb, fb, bb, b1, b1p, b2, b3, hr, pts, year, set_name,
                                    pos1=pos1, fld1=fld1, pos2=pos2, fld2=fld2, pos3=pos3, fld3=fld3, pos4=pos4, fld4=fld4)
                    batter.team_role = role # Set the team role
                    # The batter's position attribute is already set to the saved position from the JSON

                    if role == 'Starter':
                        batters.append(batter)
                    elif role == 'Bench':
                        bench.append(batter)
                    else:
                        print(f"Warning: Unknown batter role '{role}' for {player_name} in {filepath}. Skipping.")
                else:
                    print(f"Warning: Skipping incomplete batter data for {player_name} in {filepath}: {batter_data}")
            except Exception as e:
                 print(f"Error loading batter data from {filepath}: {batter_data} - {e}")
                 continue


        # Load pitchers (Starters, Relievers, Closers)
        for pitcher_data in team_data.get("starters", []) + team_data.get("relievers", []) + team_data.get("closers", []):
            try:
                role = pitcher_data.get("role")
                player_name = pitcher_data.get("name")
                position = pitcher_data.get("position") # Load the saved position
                control = pitcher_data.get("control")
                pu = pitcher_data.get("pu")
                so = pitcher_data.get("so")
                gb = pitcher_data.get("gb")
                fb = pitcher_data.get("fb")
                bb = pitcher_data.get("bb")
                b1 = pitcher_data.get("1b") # Use '1b' key
                b2 = pitcher_data.get("2b") # Use '2b' key
                hr = pitcher_data.get("hr")
                ip_limit_outs = pitcher_data.get("ip_limit_outs") # Load IP limit as outs
                pts = pitcher_data.get("pts")
                year = pitcher_data.get("year")
                set_name = pitcher_data.get("set")


                if all([player_name, role, position, control is not None, pu is not None, so is not None, gb is not None, fb is not None, bb is not None, b1 is not None, b2 is not None, hr is not None, pts is not None]):
                     # ip_limit_outs can be None, so check separately
                     pitcher = Pitcher(player_name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_limit_outs, year, set_name)
                     pitcher.team_role = role # Set the team role

                     if role == 'SP':
                         starters_pitchers.append(pitcher)
                     elif role == 'RP':
                         relievers.append(pitcher)
                     elif role == 'CL':
                         closers.append(pitcher)
                     else:
                         print(f"Warning: Unknown pitcher role '{role}' for {player_name} in {filepath}. Skipping.")
                else:
                     print(f"Warning: Skipping incomplete pitcher data for {player_name} in {filepath}: {pitcher_data}")
            except Exception as e:
                 print(f"Error loading pitcher data from {filepath}: {pitcher_data} - {e}")
                 continue


        # Basic validation: check if we have enough players for a valid team
        if len(batters) == 9 and len(bench) == 1 and len(starters_pitchers) == 4 and (len(relievers) + len(closers)) == 6:
             loaded_team = Team(team_name_from_file, batters, starters_pitchers, relievers, closers, bench)
             # Optionally, verify loaded_total_points if it was in the JSON
             if loaded_total_points is not None and loaded_team.total_points != loaded_total_points:
                 print(f"Warning: Calculated total points ({loaded_team.total_points}) mismatch with saved points ({loaded_total_points}) for team '{team_name_from_file}'.")
             # print(f"Successfully loaded team '{team_name_from_file}' from {filepath}") # Debug print removed
             return loaded_team
        else:
             print(f"Error loading team from {filepath}: Invalid roster size.")
             print(f"Expected: 9 Starters, 1 Bench, 4 SP, 6 RP/CL. Found: {len(batters)} Starters, {len(bench)} Bench, {len(starters_pitchers)} SP, {len(relievers) + len(closers)} RP/CL.")
             return None


    except FileNotFoundError:
        print(f"Error: Team file not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Please check the file format.")
        return None
    except Exception as e:
        print(f"Error loading team from {filepath}: {e}")
        return None

