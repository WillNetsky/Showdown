# optimizer_ga.py
import random
import copy
import os  # Added for potential benchmark file loading

from entities import Team, Batter, Pitcher
from stats import Stats, TeamStats
# Assuming load_team_from_json is in team_management and TEAMS_DIR is accessible or passed
from team_management import create_random_team, load_team_from_json
from game_logic import play_game

# If TEAMS_DIR is used for loading benchmark archetypes, ensure it's defined or accessible.
# For simplicity, let's assume it might be a subdirectory like 'teams/benchmarks/'
# Or you could pass a specific path for benchmark archetypes.
BENCHMARK_ARCHETYPES_DIR = os.path.join('teams', 'benchmark_archetypes')


class GACandidate:
    """Wraps a Team object with its fitness score (now Run Differential)."""

    def __init__(self, team_object: Team, is_newly_created=True):
        self.team = team_object
        self.fitness = 0.0  # Now represents total Run Differential from evaluation games

        if not hasattr(self.team, 'team_stats') or self.team.team_stats is None:
            self.team.team_stats = TeamStats()
        original_elo = self.team.team_stats.elo_rating  # Preserve original ELO if any
        self.team.team_stats.reset_for_new_season(maintain_elo=True)
        self.team.team_stats.elo_rating = original_elo

        for p in (self.team.batters + self.team.bench + self.team.all_pitchers):
            if not hasattr(p, 'season_stats') or p.season_stats is None or is_newly_created:
                p.season_stats = Stats()
            else:
                p.season_stats.reset()  # Reset for elites/mutated, will be repopulated by eval
            if not hasattr(p, 'career_stats') or p.career_stats is None:
                p.career_stats = Stats()

    def __lt__(self, other):
        return self.fitness < other.fitness

    def __repr__(self):
        return f"GACandidate({self.team.name}, Fitness (RunDiff): {self.fitness:.0f})"


class GeneticTeamOptimizer:
    def __init__(self, all_players_list,
                 population_size=30,
                 num_generations=20,
                 mutation_rate=0.8,
                 num_mutation_swaps=1,
                 elitism_count=3,
                 num_benchmark_teams=5,
                 games_vs_each_benchmark=100,  # MODIFIED PARAMETER NAME AND DEFAULT
                 immigration_rate=0.1,
                 min_team_points=4500,
                 max_team_points=5000,
                 benchmark_archetype_files=None,  # New: List of specific benchmark team files
                 log_callback=None,
                 update_progress_callback=None,
                 stop_event=None):

        self.all_players = all_players_list
        self.population_size = population_size
        self.num_generations = num_generations
        self.mutation_rate = mutation_rate
        self.num_mutation_swaps = num_mutation_swaps
        self.elitism_count = elitism_count
        self.num_benchmark_teams = num_benchmark_teams
        self.games_vs_each_benchmark = games_vs_each_benchmark  # MODIFIED
        self.immigration_rate = immigration_rate
        self.min_points = min_team_points
        self.max_points = max_team_points
        self.benchmark_archetype_files = benchmark_archetype_files if benchmark_archetype_files else []
        self.stop_event = stop_event

        self.log_callback = log_callback if callable(log_callback) else print
        self.update_progress_callback = update_progress_callback if callable(update_progress_callback) else lambda p, m, gn=None, bf=None, af=None: None

        self.population = []
        self.benchmark_teams = []
        self.best_individual_overall = None
        self.generation_count = 0

        self.best_fitness_history = []
        self.avg_fitness_history = []
        self.generation_count_history = []

        self.batters_pool = [p for p in self.all_players if isinstance(p, Batter)]
        self.pitchers_pool = [p for p in self.all_players if isinstance(p, Pitcher)]

    def _log(self, message):
        self.log_callback(f"[GA] {message}")

    def _initialize_population(self):
        self._log(f"Initializing population of {self.population_size} teams...")
        self.population = []
        attempts = 0
        max_attempts_per_team = self.population_size * 20  # Increased attempts margin

        while len(self.population) < self.population_size and attempts < max_attempts_per_team:
            if self.stop_event and self.stop_event.is_set():
                self._log("Stop requested during population initialization.")
                return False
            team_name = f"GA_Team_Init_{len(self.population) + 1}"
            team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
            if team_obj:
                self.population.append(GACandidate(team_obj, is_newly_created=True))
            attempts += 1

        if len(self.population) < self.population_size:
            self._log(
                f"Warning: Could only initialize {len(self.population)}/{self.population_size} teams after {attempts} attempts.")
            if not self.population:  # Critical if no teams could be made
                self._log(
                    "ERROR: Failed to initialize any teams for the GA population. Check player data and point ranges.")
                return False  # Indicate failure
        self._log(f"Population initialized with {len(self.population)} teams.")
        return True

    def _generate_benchmark_teams(self):
        self._log(f"Generating up to {self.num_benchmark_teams} benchmark teams...")
        self.benchmark_teams = []

        # 1. Load from specified archetype files
        loaded_archetype_names = set()
        if self.benchmark_archetype_files:
            self._log(f"Attempting to load benchmark archetypes from: {self.benchmark_archetype_files}")
            for filepath in self.benchmark_archetype_files:
                if len(self.benchmark_teams) >= self.num_benchmark_teams:
                    break
                try:
                    # Construct full path if relative paths are given for archetypes
                    # This assumes benchmark_archetype_files contains paths relative to a known location or absolute paths
                    # For now, let's assume they might be in BENCHMARK_ARCHETYPES_DIR if not absolute
                    if not os.path.isabs(filepath) and BENCHMARK_ARCHETYPES_DIR:
                        actual_filepath = os.path.join(BENCHMARK_ARCHETYPES_DIR, filepath)
                    else:
                        actual_filepath = filepath

                    if not os.path.exists(actual_filepath):
                        self._log(f"  Benchmark archetype file not found: {actual_filepath}")
                        continue

                    team_obj = load_team_from_json(actual_filepath)
                    if team_obj:
                        team_obj.name = f"BenchArchetype_{os.path.splitext(os.path.basename(filepath))[0]}"  # Ensure unique name
                        # Reset stats for benchmark role
                        if not hasattr(team_obj,
                                       'team_stats') or team_obj.team_stats is None: team_obj.team_stats = TeamStats()
                        team_obj.team_stats.reset_for_new_season(
                            maintain_elo=False)  # Benchmarks get fresh ELO unless specified
                        team_obj.team_stats.elo_rating = 1500  # Default ELO for benchmarks

                        for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                            if not hasattr(p, 'season_stats') or p.season_stats is None:
                                p.season_stats = Stats()
                            else:
                                p.season_stats.reset()
                            if not hasattr(p, 'career_stats') or p.career_stats is None: p.career_stats = Stats()
                            # else: p.career_stats.reset() # Typically don't reset career for benchmarks

                        self.benchmark_teams.append(team_obj)
                        loaded_archetype_names.add(team_obj.name)
                        self._log(f"  Loaded benchmark archetype: {team_obj.name} from {actual_filepath}")
                    else:
                        self._log(f"  Failed to load team from benchmark archetype file: {actual_filepath}")
                except Exception as e:
                    self._log(f"  Error loading benchmark team from {filepath}: {e}")

        # 2. Fill remaining slots with random teams
        num_random_to_generate = self.num_benchmark_teams - len(self.benchmark_teams)
        if num_random_to_generate > 0:
            self._log(f"Generating {num_random_to_generate} additional random benchmark teams...")
            attempts = 0
            max_attempts_for_random = num_random_to_generate * 10

            for i in range(num_random_to_generate):
                if self.stop_event and self.stop_event.is_set(): break
                team_name = f"Benchmark_Random_{i + 1}"
                team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                if team_obj:
                    if not hasattr(team_obj,
                                   'team_stats') or team_obj.team_stats is None: team_obj.team_stats = TeamStats()
                    team_obj.team_stats.reset_for_new_season(maintain_elo=False)
                    team_obj.team_stats.elo_rating = 1500  # Default ELO for random benchmarks
                    for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                        if not hasattr(p, 'season_stats') or p.season_stats is None:
                            p.season_stats = Stats()
                        else:
                            p.season_stats.reset()
                        if not hasattr(p, 'career_stats') or p.career_stats is None: p.career_stats = Stats()
                    self.benchmark_teams.append(team_obj)
                attempts += 1
                if attempts >= max_attempts_for_random and len(self.benchmark_teams) < self.num_benchmark_teams:
                    self._log(
                        f"  Warning: Could only generate {len(self.benchmark_teams) - len(loaded_archetype_names)} random benchmark teams.")
                    break

        if not self.benchmark_teams:
            self._log("ERROR: Failed to generate or load any benchmark teams. GA cannot proceed.")
            return False  # Indicate failure

        self._log(f"Final benchmark team count: {len(self.benchmark_teams)}")
        for i, team in enumerate(self.benchmark_teams):
            self._log(
                f"  Benchmark {i + 1}: {team.name} (ELO: {team.team_stats.elo_rating:.0f}, Points: {team.total_points})")
        return True

    def _calculate_fitness(self, candidate: GACandidate):
        candidate_team = candidate.team
        total_run_differential_for_candidate = 0
        total_games_played_by_candidate_in_eval = 0

        # Reset candidate's season stats for this specific evaluation round
        # The GACandidate constructor already resets season_stats (full or partial based on is_newly_created)
        # We need to ensure it's pristine for this eval run accumulation.
        for p in (candidate_team.batters + candidate_team.bench + candidate_team.all_pitchers):
            if not hasattr(p, 'season_stats') or p.season_stats is None:  # Should be there from GACandidate
                p.season_stats = Stats()
            p.season_stats.reset()  # Clean slate for accumulating this evaluation's game stats

        # Candidate team's ELO is maintained from its GACandidate creation, not reset per evaluation here
        # self._log(f"  Evaluating fitness for {candidate_team.name} (ELO: {candidate_team.team_stats.elo_rating:.0f})...")

        for benchmark_idx, benchmark_team in enumerate(self.benchmark_teams):
            if self.stop_event and self.stop_event.is_set():
                self._log(f"Stop requested during fitness calculation for {candidate_team.name}.")
                candidate.fitness = total_run_differential_for_candidate
                return

            # self._log(f"    vs Benchmark {benchmark_team.name} for {self.games_vs_each_benchmark} games")
            for i in range(self.games_vs_each_benchmark):  # Play N games vs EACH benchmark
                if self.stop_event and self.stop_event.is_set():
                    self._log(f"Stop requested during game simulation for {candidate_team.name}.")
                    candidate.fitness = total_run_differential_for_candidate
                    return

                # Reset game_stats for all players involved in *this specific game*
                for p_list in [candidate_team.batters, candidate_team.bench, candidate_team.all_pitchers,
                               benchmark_team.batters, benchmark_team.bench, benchmark_team.all_pitchers]:
                    for p_obj in p_list:  # Renamed to p_obj to avoid conflict with outer 'p'
                        if hasattr(p_obj, 'game_stats'):
                            p_obj.game_stats.reset()
                        else:
                            p_obj.game_stats = Stats()

                is_home_game_for_candidate = (i % 2 == 0)  # Alternate home/away against each benchmark

                # Pass is_ga_evaluation to play_game if it uses it (e.g. for different logging, no ELO updates for benchmarks)
                if is_home_game_for_candidate:  # Candidate is Home
                    away_res, home_res, _, _, _ = play_game(benchmark_team, candidate_team, is_ga_evaluation=True)
                    total_run_differential_for_candidate += (
                                home_res.get('runs_scored', 0) - home_res.get('runs_allowed', 0))
                else:  # Candidate is Away
                    away_res, home_res, _, _, _ = play_game(candidate_team, benchmark_team, is_ga_evaluation=True)
                    total_run_differential_for_candidate += (
                                away_res.get('runs_scored', 0) - away_res.get('runs_allowed', 0))

                total_games_played_by_candidate_in_eval += 1

                # After each game, aggregate game stats to the *candidate's current evaluation season_stats*
                candidate_team.post_game_team_cleanup()
                # Benchmark team's post_game_team_cleanup would also run if play_game calls it,
                # but their accumulated season_stats are not used for the candidate's fitness.
                # Their game_stats are reset in the next iteration of this inner loop.

        candidate.fitness = total_run_differential_for_candidate
        # self._log(f"  Fitness (RunDiff) for {candidate_team.name}: {candidate.fitness:.0f} ({total_games_played_by_candidate_in_eval} games)")

    def _select_parents_tournament(self, k=3):
        parents = []
        for _ in range(2):  # Select two parents
            actual_k = min(k, len(self.population))
            if actual_k == 0: return None, None  # No population to select from
            if actual_k == 1 and len(self.population) == 1:  # Population of one
                parents.append(self.population[0])
                continue
            if not self.population: return None, None

            tournament_participants = random.sample(self.population, actual_k)
            winner = max(tournament_participants, key=lambda ind: ind.fitness)
            parents.append(winner)

        if len(parents) == 1:  # If population was 1, duplicate for parent1, parent2
            return parents[0], parents[0]
        elif len(parents) == 2:
            return parents[0], parents[1]
        return None, None  # Should not happen if population exists

    def _mutate(self, parent_candidate: GACandidate):
        mutated_team_obj = copy.deepcopy(parent_candidate.team)
        # Ensure the name indicates its generation and that it's a mutation product
        # Extract original base name if it was an Init or another Mut/Child
        base_name_parts = parent_candidate.team.name.split('_')
        if len(base_name_parts) > 2 and base_name_parts[0] == "GA" and base_name_parts[1] in ["Team", "Mut", "Child"]:
            original_id = base_name_parts[-1] if base_name_parts[-1].isdigit() else str(random.randint(1000, 9999))
        else:  # Fallback for other names or if no clear ID part
            original_id = str(random.randint(1000, 9999))  # Ensure some uniqueness marker

        mutated_team_obj.name = f"GA_Mut_G{self.generation_count}_{original_id}"

        if hasattr(parent_candidate.team, 'team_stats') and parent_candidate.team.team_stats is not None:
            mutated_team_obj.team_stats.elo_rating = parent_candidate.team.team_stats.elo_rating

        mutated_successfully_at_least_once = False
        for _ in range(self.num_mutation_swaps):  # Perform N swaps
            roster_list_options_mut = [
                (mutated_team_obj.batters, "batter", "Starter"),
                (mutated_team_obj.bench, "batter", "Bench"),
                (mutated_team_obj.starters, "pitcher", "SP"),
                (mutated_team_obj.relievers, "pitcher", "RP"),
                (mutated_team_obj.closers, "pitcher", "CL")
            ]
            # Filter for lists that are not empty
            eligible_roster_lists_with_type = [(lst, p_type, r_role) for lst, p_type, r_role in roster_list_options_mut
                                               if lst]
            if not eligible_roster_lists_with_type: continue  # No players to mutate

            list_to_mutate_from, player_type_str, original_role_category = random.choice(
                eligible_roster_lists_with_type)

            player_to_remove_idx = random.randrange(len(list_to_mutate_from))
            player_to_remove = list_to_mutate_from.pop(player_to_remove_idx)

            # Get the specific role and position slot from the player being removed
            actual_original_role = player_to_remove.team_role
            original_position_slot = player_to_remove.position  # For batters, this is their field position

            replacement_found = False
            potential_replacements_pool = self.batters_pool if player_type_str == "batter" else self.pitchers_pool

            # Get all player IDs (name, year, set) currently on the mutated team to avoid duplicates
            current_team_player_ids = set()
            for r_list_key in ["batters", "bench", "starters", "relievers", "closers"]:
                for p_in_team in getattr(mutated_team_obj, r_list_key, []):
                    current_team_player_ids.add((p_in_team.name, p_in_team.year, p_in_team.set))

            # Filter pool for players not already on the team and not the one being removed
            potential_replacements = [
                p for p in potential_replacements_pool
                if (p.name, p.year, p.set) != (player_to_remove.name, player_to_remove.year, player_to_remove.set) and \
                   (p.name, p.year, p.set) not in current_team_player_ids
            ]
            random.shuffle(potential_replacements)

            for new_player_from_pool in potential_replacements:
                new_player = copy.deepcopy(new_player_from_pool)
                can_play_role_and_pos = False

                if isinstance(new_player, Batter):
                    if original_role_category == "Starter":  # If removing a starting batter
                        # New player must be able to play the specific position slot
                        can_play_role_and_pos = new_player.can_play(original_position_slot)
                    else:  # If removing a bench batter, any batter can replace
                        can_play_role_and_pos = True
                elif isinstance(new_player, Pitcher):
                    # New pitcher must match the role category (SP, RP, CL)
                    if actual_original_role == 'SP' and new_player.position in ['Starter', 'SP', 'P']:
                        can_play_role_and_pos = True
                    elif actual_original_role == 'RP' and new_player.position in ['Reliever', 'RP', 'P']:
                        can_play_role_and_pos = True
                    elif actual_original_role == 'CL' and new_player.position in ['Closer', 'CL', 'P']:
                        can_play_role_and_pos = True

                if not can_play_role_and_pos: continue

                current_points_without_removed = mutated_team_obj.total_points - player_to_remove.pts
                new_total_points_with_new = current_points_without_removed + new_player.pts

                if self.min_points <= new_total_points_with_new <= self.max_points:
                    list_to_mutate_from.insert(player_to_remove_idx, new_player)

                    new_player.team_role = actual_original_role  # Assign the role of the player being replaced
                    if isinstance(new_player, Batter) and original_role_category == "Starter":
                        new_player.position = original_position_slot  # Assign the specific field position
                    # For pitchers, their inherent 'position' (SP/RP/CL) is usually fine, role matches.

                    new_player.team_name = mutated_team_obj.name

                    mutated_team_obj.total_points = new_total_points_with_new
                    # Reconstruct player lists like all_pitchers, bullpen
                    mutated_team_obj.all_pitchers = mutated_team_obj.starters + mutated_team_obj.relievers + mutated_team_obj.closers
                    mutated_team_obj.bullpen = sorted(mutated_team_obj.relievers + mutated_team_obj.closers,
                                                      key=lambda x: x.pts, reverse=True)

                    mutated_successfully_at_least_once = True
                    replacement_found = True
                    break  # Found a replacement for this swap

            if not replacement_found:  # If no valid replacement found, add the original player back
                list_to_mutate_from.insert(player_to_remove_idx, player_to_remove)

        # Return as a new GACandidate, which will ensure its season_stats are reset for evaluation
        return GACandidate(mutated_team_obj, is_newly_created=True)

    def request_stop(self):
        if self.stop_event:
            self.stop_event.set()
        self._log("GA stop requested by external signal.")

    def run(self):
        self._log("Genetic Algorithm Started.")
        if not self._initialize_population():  # Handles its own logging for critical failure
            self.update_progress_callback(0, "GA Failed: Population Initialization Error", 0, 0, 0)
            return None
        if not self._generate_benchmark_teams():  # Handles its own logging
            self.update_progress_callback(0, "GA Failed: Benchmark Generation Error", 0, 0, 0)
            return None

        if not self.benchmark_teams:  # Double check, though _generate_benchmark_teams should return False
            self._log("Error: No benchmark teams available. GA cannot run.")
            self.update_progress_callback(0, "GA Failed: No benchmark teams", 0, 0, 0)
            return None

        self.generation_count = 0
        self.best_fitness_history.clear()
        self.avg_fitness_history.clear()
        self.generation_count_history.clear()

        self._log("Evaluating initial population...")
        total_initial_eval_steps = len(self.population)
        for i in range(total_initial_eval_steps):
            if self.stop_event and self.stop_event.is_set():
                self._log("Stop requested during initial fitness calculation.")
                self.update_progress_callback(100, "GA Stopped during initial eval", self.generation_count,
                                              self.best_individual_overall.fitness if self.best_individual_overall else 0,
                                              0)
                return self.best_individual_overall  # Return whatever best was found, if any

            self._calculate_fitness(self.population[i])
            progress_percentage = ((i + 1) / total_initial_eval_steps) * (100 / (self.num_generations + 1))
            self.update_progress_callback(progress_percentage,
                                          f"Gen 0: Evaluating initial pop ({i + 1}/{total_initial_eval_steps})")

        if not self.population:  # Check if population somehow became empty (e.g. all failed fitness)
            self._log("Error: Population is empty after initial evaluation attempts.")
            self.update_progress_callback(100, "GA Failed: Population empty post-initial eval", 0, 0, 0)
            return None

        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        best_initial_fitness = self.population[0].fitness
        avg_initial_fitness = sum(ind.fitness for ind in self.population) / len(
            self.population) if self.population else 0.0

        self.best_individual_overall = copy.deepcopy(self.population[0])

        self.generation_count_history.append(0)
        self.best_fitness_history.append(best_initial_fitness)
        self.avg_fitness_history.append(avg_initial_fitness)

        self._log(
            f"Initial Best: {self.best_individual_overall.team.name}, Fitness (RunDiff): {best_initial_fitness:.0f}, Avg Fitness: {avg_initial_fitness:.0f}")
        self.update_progress_callback(
            (100 / (self.num_generations + 1)),
            f"Initial evaluation complete. Best: {best_initial_fitness:.0f}",
            generation_num=0, best_fitness=best_initial_fitness, avg_fitness=avg_initial_fitness
        )

        for gen_idx in range(self.num_generations):
            self.generation_count = gen_idx + 1  # Current generation number (1-indexed)
            if self.stop_event and self.stop_event.is_set():
                self._log(f"Stop requested at start of Generation {self.generation_count}.")
                break
            self._log(f"\n--- Generation {self.generation_count}/{self.num_generations} ---")

            base_gen_progress = ((self.generation_count) / (self.num_generations + 1)) * 100
            self.update_progress_callback(base_gen_progress, f"Generation {self.generation_count} starting...")

            new_population = []

            # Elitism
            if self.elitism_count > 0 and self.elitism_count <= len(self.population):
                elites = sorted(self.population, key=lambda ind: ind.fitness, reverse=True)[:self.elitism_count]
                for elite_cand in elites:
                    # Elites are carried over; their fitness is known but they will be re-wrapped as GACandidates
                    # which resets their season_stats for the new generation's evaluation round.
                    new_population.append(GACandidate(copy.deepcopy(elite_cand.team), is_newly_created=False))

            # Immigration
            num_immigrants = int(self.population_size * self.immigration_rate)
            for _ in range(num_immigrants):
                if len(new_population) >= self.population_size: break
                if self.stop_event and self.stop_event.is_set(): break
                team_name = f"GA_Imm_G{self.generation_count}_{len(new_population)}"
                team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                if team_obj:
                    new_population.append(GACandidate(team_obj, is_newly_created=True))
            if self.stop_event and self.stop_event.is_set(): self._log("Stop requested during immigration."); break

            # Offspring (Selection, Crossover - TODO, Mutation)
            num_offspring_needed = self.population_size - len(new_population)
            for i in range(num_offspring_needed):
                if len(new_population) >= self.population_size: break
                if self.stop_event and self.stop_event.is_set(): break

                parent1, parent2 = self._select_parents_tournament()  # Parent2 for future crossover
                if parent1 is None:  # Should only happen if population becomes critically small/empty
                    self._log("Warning: Could not select parents. Attempting to fill with immigrant.")
                    team_name = f"GA_Fill_G{self.generation_count}_{len(new_population)}"
                    team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                    if team_obj: new_population.append(GACandidate(team_obj, is_newly_created=True))
                    continue

                # TODO: Implement Crossover here using parent1 and parent2 with a crossover_rate
                # For now, just mutate parent1
                if random.random() < self.mutation_rate:
                    child_candidate = self._mutate(parent1)
                else:  # Pass parent1 through if no mutation
                    child_candidate = GACandidate(copy.deepcopy(parent1.team),
                                                  is_newly_created=False)  # Treat as elite if not mutated

                new_population.append(child_candidate)

            if self.stop_event and self.stop_event.is_set(): self._log(
                "Stop requested during offspring generation."); break

            self.population = new_population[:self.population_size]  # Trim if overpopulated

            if not self.population:  # Safety check if new_population ended up empty
                self._log(
                    f"Warning: Population became empty before evaluation in Gen {self.generation_count}. Stopping.")
                break

            # Evaluate all members of the new population
            total_current_gen_eval_steps = len(self.population)
            for i in range(total_current_gen_eval_steps):
                if self.stop_event and self.stop_event.is_set():
                    self._log("Stop requested during new population fitness calculation.");
                    break

                self._calculate_fitness(self.population[i])  # This populates fitness in GACandidate objects

                current_eval_progress_in_gen = (
                                                           i + 1) / total_current_gen_eval_steps if total_current_gen_eval_steps > 0 else 1
                total_progress = base_gen_progress + (current_eval_progress_in_gen * (100 / (self.num_generations + 1)))
                self.update_progress_callback(total_progress,
                                              f"Gen {self.generation_count}: Evaluating ({i + 1}/{total_current_gen_eval_steps})")
            if self.stop_event and self.stop_event.is_set(): break

            if not self.population:  # Should not happen if loop above ran, but as a safeguard
                self._log(
                    f"Warning: Population became empty after evaluation in Gen {self.generation_count}. Stopping.")
                break

            self.population.sort(key=lambda ind: ind.fitness, reverse=True)
            current_best_in_gen_obj = self.population[0]

            best_gen_fitness = current_best_in_gen_obj.fitness
            avg_gen_fitness = sum(ind.fitness for ind in self.population) / len(
                self.population) if self.population else 0.0

            self.generation_count_history.append(self.generation_count)
            self.best_fitness_history.append(best_gen_fitness)
            self.avg_fitness_history.append(avg_gen_fitness)

            if best_gen_fitness > self.best_individual_overall.fitness:
                self.best_individual_overall = copy.deepcopy(current_best_in_gen_obj)
                self._log(
                    f"  NEW OVERALL BEST! Gen {self.generation_count}: {self.best_individual_overall.team.name}, Fitness (RunDiff): {best_gen_fitness:.0f}, Avg Fitness: {avg_gen_fitness:.0f}")
            else:
                self._log(
                    f"  Best this Gen: {current_best_in_gen_obj.team.name}, Fitness (RunDiff): {best_gen_fitness:.0f}, Avg Fitness: {avg_gen_fitness:.0f} (Overall Best: {self.best_individual_overall.fitness:.0f})")

            self.update_progress_callback(
                ((self.generation_count + 1) / (self.num_generations + 1)) * 100,
                f"Gen {self.generation_count} complete. Best: {best_gen_fitness:.0f}",
                generation_num=self.generation_count, best_fitness=best_gen_fitness, avg_fitness=avg_gen_fitness
            )

        final_progress_val = 100.0
        final_message_str = "GA Finished"
        if self.stop_event and self.stop_event.is_set():
            final_message_str = "GA Stopped by user"

        final_best_fit = self.best_fitness_history[-1] if self.best_fitness_history else 0
        final_avg_fit = self.avg_fitness_history[-1] if self.avg_fitness_history else 0
        final_gen_num = self.generation_count_history[-1] if self.generation_count_history else self.generation_count

        self.update_progress_callback(final_progress_val, final_message_str, final_gen_num, final_best_fit,
                                      final_avg_fit)
        self._log(f"\nGenetic Algorithm {final_message_str}.")

        if self.best_individual_overall:
            self._log(f"Overall Best Team Found: {self.best_individual_overall.team.name}")
            self._log(f"  Fitness (Total Run Differential): {self.best_individual_overall.fitness:.0f}")
            self._log(f"  Total Points: {self.best_individual_overall.team.total_points}")

            # Ensure hits are updated on the final best individual's player season_stats before returning
            # These season_stats are from its last evaluation round.
            for p_list in [self.best_individual_overall.team.batters, self.best_individual_overall.team.bench]:
                for p_obj_final in p_list:
                    if hasattr(p_obj_final, 'season_stats') and p_obj_final.season_stats:
                        p_obj_final.season_stats.update_hits()  # Ensure AVG/OBP/SLG/OPS are current if displayed

            if self.best_individual_overall.team.batters:
                b_player = self.best_individual_overall.team.batters[0]
                if hasattr(b_player, 'season_stats') and b_player.season_stats:
                    self._log(
                        f"  FINAL BEST - First batter ({b_player.name}) PA: {b_player.season_stats.plate_appearances}, H: {b_player.season_stats.hits}, R: {b_player.season_stats.runs_scored}, OPS: {b_player.season_stats.calculate_ops()}")
        else:
            self._log("No best individual determined (e.g., GA stopped very early or failed to initialize).")

        return self.best_individual_overall