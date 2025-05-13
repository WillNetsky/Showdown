# team_management.py
import random
import os
import re
import json

from entities import Batter, Pitcher, Team
from constants import STARTING_POSITIONS, MIN_TEAM_POINTS, MAX_TEAM_POINTS
from stats import Stats, TeamStats  # Import Stats and TeamStats


def _serialize_stats_to_dict(stats_obj):
    """Converts a Stats or TeamStats object to a dictionary for JSON serialization."""
    if stats_obj is None:
        return None
    return vars(stats_obj).copy()


def _deserialize_stats_from_dict(stats_data_dict, stats_instance):
    """Populates a Stats or TeamStats instance from a dictionary."""
    if stats_data_dict is None or stats_instance is None:
        return stats_instance
    for key, value in stats_data_dict.items():
        if hasattr(stats_instance, key):
            setattr(stats_instance, key, value)
    return stats_instance


def load_players_from_json(filepath):
    """Loads player data from the main all_players.json file."""
    players = []
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            all_players_data = json.load(infile)
        if not isinstance(all_players_data, list): return []

        for player_data in all_players_data:
            if not isinstance(player_data, dict): continue
            player_type = player_data.get('type')
            name = player_data.get('name', '').strip()
            pts_str = player_data.get('pts', '0').strip()
            year = player_data.get('year', '').strip()
            set_name = player_data.get('set', '').strip()

            if not name or not player_type: continue
            try:
                pts = int(pts_str)
            except ValueError:
                continue

            # Helper to safely convert to int, defaulting to 0
            def safe_int(val_str, default=0):
                try:
                    return int(val_str)
                except (ValueError, TypeError):
                    return default

            if player_type == 'batter':
                position = player_data.get('position', '').strip()
                onbase = safe_int(player_data.get('onbase', '0').strip())
                so = safe_int(player_data.get('so', '0').strip())
                gb = safe_int(player_data.get('gb', '0').strip())
                fb = safe_int(player_data.get('fb', '0').strip())
                bb = safe_int(player_data.get('bb', '0').strip())
                b1 = safe_int(player_data.get('b1', '0').strip())
                b1p = safe_int(player_data.get('b1p', '0').strip())
                b2 = safe_int(player_data.get('b2', '0').strip())
                b3 = safe_int(player_data.get('b3', '0').strip())
                hr = safe_int(player_data.get('hr', '0').strip())
                pos1 = player_data.get('pos1', '').strip();
                fld1 = player_data.get('fld1', '').strip()
                pos2 = player_data.get('pos2', '').strip();
                fld2 = player_data.get('fld2', '').strip()
                pos3 = player_data.get('pos3', '').strip();
                fld3 = player_data.get('fld3', '').strip()
                pos4 = player_data.get('pos4', '').strip();
                fld4 = player_data.get('fld4', '').strip()

                batter = Batter(name, position, onbase, so, gb, fb, bb, b1, b1p, b2, b3, hr, pts, year, set_name,
                                pos1, fld1, pos2, fld2, pos3, fld3, pos4, fld4)
                players.append(batter)

            elif player_type == 'pitcher':
                position = player_data.get('pos', '').strip()
                control = safe_int(player_data.get('control', '0').strip())
                pu = safe_int(player_data.get('pu', '0').strip())
                so = safe_int(player_data.get('so', '0').strip())
                gb = safe_int(player_data.get('gb', '0').strip())
                fb = safe_int(player_data.get('fb', '0').strip())
                bb = safe_int(player_data.get('bb', '0').strip())
                b1 = safe_int(player_data.get('b1', '0').strip())
                b2 = safe_int(player_data.get('b2', '0').strip())
                hr = safe_int(player_data.get('hr', '0').strip())

                ip_limit_outs = None
                ip_limit_outs_str = player_data.get('ip limit (outs)', '').strip()
                if ip_limit_outs_str:
                    try:
                        ip_limit_outs = int(ip_limit_outs_str)
                    except ValueError:
                        pass  # Keep None if conversion fails
                if ip_limit_outs is None:  # Fallback to 'ip' if 'ip limit (outs)' not found/valid
                    ip_str = player_data.get('ip', '').strip()
                    if ip_str:
                        try:
                            ip_limit_outs = int(float(ip_str) * 3)
                        except ValueError:
                            pass

                pitcher = Pitcher(name, position, control, pu, so, gb, fb, bb, b1, b2, hr, pts, ip_limit_outs, year,
                                  set_name)
                players.append(pitcher)
    except FileNotFoundError:
        print(f"Error: Player data file not found at {filepath}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}. Please check the file format.")
        return []
    except Exception as e:
        print(f"Error loading players from {filepath}: {e}")
        return []
    return players


def get_next_team_number(teams_dir):
    max_number = 0
    pattern = re.compile(r'Team_(\d+)_.*\.json', re.IGNORECASE)
    if not os.path.exists(teams_dir):
        os.makedirs(teams_dir)
        return 1
    for filename in os.listdir(teams_dir):
        match = pattern.match(filename)
        if match:
            try:
                team_number = int(match.group(1))
                if team_number > max_number: max_number = team_number
            except ValueError:
                pass
    return max_number + 1


def create_random_team(all_players, team_name, min_points=MIN_TEAM_POINTS, max_points=MAX_TEAM_POINTS,
                       max_attempts=1000):
    available_batters = [p for p in all_players if isinstance(p, Batter)]
    available_pitchers = [p for p in all_players if isinstance(p, Pitcher)]
    if len(available_batters) < 10 or len(available_pitchers) < 10: return None

    for attempt in range(max_attempts):
        random.shuffle(available_batters);
        random.shuffle(available_pitchers)
        selected_starters, selected_bench, selected_sps, selected_rps, selected_cls = [], [], [], [], []
        selected_players_set = set()
        temp_batters = list(available_batters)
        lineup_positions_to_fill = list(STARTING_POSITIONS)
        eligible_players_by_position = {
            pos: [p for p in temp_batters if (p.name, p.year, p.set) not in selected_players_set and p.can_play(pos)]
            for pos in lineup_positions_to_fill
        }
        sorted_positions = sorted(lineup_positions_to_fill, key=lambda pos: len(eligible_players_by_position[pos]))
        found_all_starters = True
        for pos in sorted_positions:
            current_eligible_players = [p for p in eligible_players_by_position[pos] if
                                        (p.name, p.year, p.set) not in selected_players_set]
            if not current_eligible_players: found_all_starters = False; break
            player = random.choice(current_eligible_players)
            selected_starters.append(player)
            selected_players_set.add((player.name, player.year, player.set))
            player.team_role = 'Starter';
            player.position = pos
        if not found_all_starters or len(selected_starters) < len(STARTING_POSITIONS): continue

        remaining_batters = [b for b in available_batters if (b.name, b.year, b.set) not in selected_players_set]
        if not remaining_batters: continue
        bench_player = random.choice(remaining_batters)
        selected_bench.append(bench_player)
        selected_players_set.add((bench_player.name, bench_player.year, bench_player.set))
        bench_player.team_role = 'Bench'

        temp_pitchers = [p for p in available_pitchers if (p.name, p.year, p.set) not in selected_players_set]
        random.shuffle(temp_pitchers)
        sp_candidates = [p for p in temp_pitchers if p.position in ['Starter', 'SP', 'P']]
        if len(sp_candidates) < 4: continue
        selected_sps = random.sample(sp_candidates, 4)
        for p in selected_sps: selected_players_set.add((p.name, p.year, p.set)); p.team_role = 'SP'

        remaining_rp_cl_pool = [p for p in temp_pitchers if
                                (p.name, p.year, p.set) not in selected_players_set]  # Re-filter after SPs
        closers_pool = [p for p in remaining_rp_cl_pool if p.position == 'CL']
        relievers_pool = [p for p in remaining_rp_cl_pool if
                          p.position in ['Reliever', 'RP', 'P'] and p not in closers_pool]
        if closers_pool:
            cl = random.choice(closers_pool)
            selected_cls.append(cl)
            selected_players_set.add((cl.name, cl.year, cl.set));
            cl.team_role = 'CL'
            relievers_pool = [p for p in relievers_pool if p != cl]

        num_rps_needed = 6 - len(selected_cls)
        if len(relievers_pool) < num_rps_needed: continue
        selected_rps.extend(random.sample(relievers_pool, num_rps_needed))  # Use extend
        for p in selected_rps: selected_players_set.add((p.name, p.year, p.set)); p.team_role = 'RP'

        if len(selected_starters) == 9 and len(selected_bench) == 1 and \
                len(selected_sps) == 4 and (len(selected_rps) + len(selected_cls)) == 6:
            current_total_points = sum(
                p.pts for p_list in [selected_starters, selected_bench, selected_sps, selected_rps, selected_cls] for p
                in p_list)
            if min_points <= current_total_points <= max_points:
                for p_list in [selected_starters, selected_bench, selected_sps, selected_rps, selected_cls]:
                    for p in p_list: p.team_name = team_name
                return Team(team_name, selected_starters, selected_sps, selected_rps, selected_cls, selected_bench)
    return None


def _player_to_dict(player):
    """Helper to convert a Batter or Pitcher object to a dict for JSON, including stats."""
    player_dict = {
        "type": "batter" if isinstance(player, Batter) else "pitcher",
        "role": getattr(player, 'team_role', None),
        "name": player.name,
        "position": player.position,
        "pts": player.pts,
        "year": player.year,
        "set": player.set,
        "season_stats_data": _serialize_stats_to_dict(getattr(player, 'season_stats', None)),
        "career_stats_data": _serialize_stats_to_dict(getattr(player, 'career_stats', None))
    }
    if isinstance(player, Batter):
        player_dict.update({
            "onbase": player.on_base, "so": player.so, "gb": player.gb, "fb": player.fb,
            "bb": player.bb, "b1": player.b1, "b1p": player.b1p, "b2": player.b2,
            "b3": player.b3, "hr": player.hr,
            "pos1": player.pos1, "fld1": player.fld1, "pos2": player.pos2, "fld2": player.fld2,
            "pos3": player.pos3, "fld3": player.fld3, "pos4": player.pos4, "fld4": player.fld4
        })
    elif isinstance(player, Pitcher):
        player_dict.update({
            "control": player.control, "pu": player.pu, "so": player.so, "gb": player.gb,
            "fb": player.fb, "bb": player.bb, "b1": player.b1,
            "b2": player.b2, "hr": player.hr,
            "ip_limit_outs": player.out_limit
        })
    return player_dict


def save_team_to_json(team: Team, filepath: str):
    """Saves a Team object's roster and player data (including stats) to a JSON file."""
    try:
        team_data = {
            "name": team.name,
            "total_points": team.total_points,
            "team_stats_data": _serialize_stats_to_dict(team.team_stats),
            "batters": [_player_to_dict(p) for p in team.batters],
            "starters": [_player_to_dict(p) for p in team.starters],
            "relievers": [_player_to_dict(p) for p in team.relievers],
            "closers": [_player_to_dict(p) for p in team.closers],
            "bench": [_player_to_dict(p) for p in team.bench]
        }
        with open(filepath, mode='w', encoding='utf-8') as outfile:
            json.dump(team_data, outfile, indent=4)
    except Exception as e:
        print(f"Error saving team '{team.name}' to {filepath}: {e}")


def _create_player_from_dict(player_data):
    """Helper to create a Batter or Pitcher object from a dict, including stats."""
    name = player_data.get("name")
    player_type = player_data.get("type")
    # position from JSON is the assigned position for starters, or raw for others/bench
    position = player_data.get("position")
    pts = player_data.get("pts", 0)  # Default pts to 0 if missing
    year = player_data.get("year", "")
    set_name = player_data.get("set", "")

    player_obj = None

    # Helper to safely get int from player_data, defaulting to 0
    def get_int_stat(key, default=0):
        val = player_data.get(key)
        if val is None: return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    if player_type == "batter":
        player_obj = Batter(name, position,
                            get_int_stat("onbase"), get_int_stat("so"),
                            get_int_stat("gb"), get_int_stat("fb"), get_int_stat("bb"),
                            get_int_stat("b1"), get_int_stat("b1p"), get_int_stat("b2"),
                            get_int_stat("b3"), get_int_stat("hr"), pts, year, set_name,
                            player_data.get("pos1", ""), player_data.get("fld1", ""),
                            player_data.get("pos2", ""), player_data.get("fld2", ""),
                            player_data.get("pos3", ""), player_data.get("fld3", ""),
                            player_data.get("pos4", ""), player_data.get("fld4", ""))
    elif player_type == "pitcher":
        # For pitchers, ip_limit_outs can legitimately be None if not specified
        ip_limit_outs_val = player_data.get("ip_limit_outs")
        ip_limit_outs = None
        if ip_limit_outs_val is not None:
            try:
                ip_limit_outs = int(ip_limit_outs_val)
            except (ValueError, TypeError):
                ip_limit_outs = None  # Keep None if not a valid int

        player_obj = Pitcher(name, position,
                             get_int_stat("control"), get_int_stat("pu"),
                             get_int_stat("so"), get_int_stat("gb"), get_int_stat("fb"),
                             get_int_stat("bb"), get_int_stat("b1"), get_int_stat("b2"),
                             get_int_stat("hr"), pts, ip_limit_outs, year, set_name)

    if player_obj:
        player_obj.team_role = player_data.get("role")
        # Ensure stats objects exist before trying to deserialize into them
        if not hasattr(player_obj, 'season_stats') or player_obj.season_stats is None:
            player_obj.season_stats = Stats()
        if not hasattr(player_obj, 'career_stats') or player_obj.career_stats is None:
            player_obj.career_stats = Stats()

        if "season_stats_data" in player_data and player_data["season_stats_data"] is not None:
            _deserialize_stats_from_dict(player_data["season_stats_data"], player_obj.season_stats)
        if "career_stats_data" in player_data and player_data["career_stats_data"] is not None:
            _deserialize_stats_from_dict(player_data["career_stats_data"], player_obj.career_stats)
    return player_obj


def load_team_from_json(filepath: str):
    """Loads a Team object from a JSON file, including player and team stats."""
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            team_data = json.load(infile)

        team_name_from_file = team_data.get("name", os.path.splitext(os.path.basename(filepath))[0])

        loaded_batters = [_create_player_from_dict(pd) for pd in team_data.get("batters", []) if pd]
        loaded_starters_pitchers = [_create_player_from_dict(pd) for pd in team_data.get("starters", []) if pd]
        loaded_relievers = [_create_player_from_dict(pd) for pd in team_data.get("relievers", []) if pd]
        loaded_closers = [_create_player_from_dict(pd) for pd in team_data.get("closers", []) if pd]
        loaded_bench = [_create_player_from_dict(pd) for pd in team_data.get("bench", []) if pd]

        # Filter out any None players that might result from _create_player_from_dict failing
        loaded_batters = [p for p in loaded_batters if p]
        loaded_starters_pitchers = [p for p in loaded_starters_pitchers if p]
        loaded_relievers = [p for p in loaded_relievers if p]
        loaded_closers = [p for p in loaded_closers if p]
        loaded_bench = [p for p in loaded_bench if p]

        if not (len(loaded_batters) == 9 and len(loaded_bench) == 1 and \
                len(loaded_starters_pitchers) == 4 and (len(loaded_relievers) + len(loaded_closers)) == 6):
            print(
                f"Warning: Roster size mismatch loading team from {filepath}. Loaded counts - Batters: {len(loaded_batters)}, Bench: {len(loaded_bench)}, SPs: {len(loaded_starters_pitchers)}, Bullpen: {len(loaded_relievers) + len(loaded_closers)}")
            # Depending on strictness, you might return None here or try to proceed.
            # For now, allowing it to proceed if some players loaded.

        loaded_team = Team(team_name_from_file, loaded_batters, loaded_starters_pitchers,
                           loaded_relievers, loaded_closers, loaded_bench)

        if "team_stats_data" in team_data and team_data["team_stats_data"] is not None:
            if not hasattr(loaded_team, 'team_stats') or loaded_team.team_stats is None:  # Ensure team_stats exists
                loaded_team.team_stats = TeamStats()
            _deserialize_stats_from_dict(team_data["team_stats_data"], loaded_team.team_stats)

        for player_list in [loaded_batters, loaded_bench, loaded_starters_pitchers, loaded_relievers, loaded_closers]:
            for player in player_list:
                if player: player.team_name = loaded_team.name
        return loaded_team

    except FileNotFoundError:
        print(f"Error: Team file not found at {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {filepath}. Please check the file format. Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error loading team from {filepath}: {e}")
        # import traceback
        # traceback.print_exc()
        return None
