# optimizer_ga.py
import random
import copy
import os  # For os.path.exists and os.path.join

# Assuming these modules are in the parent directory or accessible via PYTHONPATH
from entities import Team, Batter, Pitcher
from stats import Stats, TeamStats
from team_management import create_random_team, load_team_from_json  # load_team_from_json is crucial
from game_logic import play_game


class GACandidate:
    """Wraps a Team object with its fitness score (now Run Differential)."""

    def __init__(self, team_object: Team, is_newly_created=True):
        self.team = team_object
        self.fitness = 0.0  # Represents total Run Differential from evaluation games

        if not hasattr(self.team, 'team_stats') or self.team.team_stats is None:
            self.team.team_stats = TeamStats()

        # Preserve original ELO (if any) from the team_object before resetting stats for GA evaluation
        original_elo = self.team.team_stats.elo_rating
        self.team.team_stats.reset_for_new_season(maintain_elo=True)  # Resets W/L, RS/RA etc.
        self.team.team_stats.elo_rating = original_elo  # Restore the ELO it came in with

        # Ensure players have fresh season_stats for GA evaluation accumulation
        for p in (self.team.batters + self.team.bench + self.team.all_pitchers):
            if not hasattr(p, 'season_stats') or p.season_stats is None or is_newly_created:
                p.season_stats = Stats()  # Full reset for brand new or fully re-evaluated individuals
            else:
                p.season_stats.reset()  # Partial reset for elites (clears counts, keeps structure)

            # Ensure career_stats object exists (it accumulates across GA runs if team persists)
            if not hasattr(p, 'career_stats') or p.career_stats is None:
                p.career_stats = Stats()

    def __lt__(self, other):
        # For sorting: higher fitness (run differential) is better.
        # So, for max(), it will pick the one with higher fitness.
        # For sort(reverse=True), it will put higher fitness first.
        return self.fitness < other.fitness

    def __repr__(self):
        return f"GACandidate({self.team.name}, Fitness(RD): {self.fitness:.0f}, Pts: {self.team.total_points})"


class GeneticTeamOptimizer:
    def __init__(self, all_players_list,
                 population_size=30,
                 num_generations=20,
                 mutation_rate=0.8,
                 num_mutation_swaps=1,
                 elitism_count=3,
                 num_benchmark_teams=5,  # Total number of benchmark teams to use
                 games_vs_each_benchmark=100,  # Games to play against EACH benchmark team
                 immigration_rate=0.1,
                 min_team_points=4500,
                 max_team_points=5000,
                 benchmark_archetype_files=None,  # List of filepaths for custom benchmarks
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
        self.games_vs_each_benchmark = games_vs_each_benchmark
        self.immigration_rate = immigration_rate
        self.min_points = min_team_points
        self.max_points = max_team_points

        self.log_callback = log_callback if callable(log_callback) else print
        if benchmark_archetype_files is None:
            self._log("[Optimizer.__init__] 'benchmark_archetype_files' argument was None.")
        elif not benchmark_archetype_files:  # Check if it's an empty list/sequence
            self._log("[Optimizer.__init__] 'benchmark_archetype_files' argument was empty.")
        else:
            self._log(
                f"[Optimizer.__init__] 'benchmark_archetype_files' argument received: {benchmark_archetype_files}")
        # Ensure benchmark_archetype_files is a list, even if None is passed
        self.benchmark_archetype_files = benchmark_archetype_files if benchmark_archetype_files else []
        self.stop_event = stop_event


        self.update_progress_callback = update_progress_callback if callable(update_progress_callback) else lambda p, m, gn=None, bf=None, af=None: None

        self.population = []
        self.benchmark_teams = []  # This will hold the actual Team objects for benchmarks
        self.best_individual_overall = None
        self.generation_count = 0

        self.best_fitness_history = []  # For plotting
        self.avg_fitness_history = []  # For plotting
        self.generation_count_history = []  # For plotting

        self.batters_pool = [p for p in self.all_players if isinstance(p, Batter)]
        self.pitchers_pool = [p for p in self.all_players if isinstance(p, Pitcher)]

        # Log initial parameters
        self._log(
            f"[Optimizer.__init__] Pop: {self.population_size}, Gens: {self.num_generations}, MutRate: {self.mutation_rate}")
        self._log(
            f"[Optimizer.__init__] NumBenchmarkTeams: {self.num_benchmark_teams}, GamesVsEach: {self.games_vs_each_benchmark}")
        self._log(f"[Optimizer.__init__] CustomBenchmarkFiles received: {self.benchmark_archetype_files}")

    def _log(self, message):
        self.log_callback(f"[GA] {message}")

    def _initialize_population(self):
        self._log(f"Initializing population of {self.population_size} teams...")
        self.population = []
        attempts = 0
        max_attempts_per_team = self.population_size * 20

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
            if not self.population:
                self._log(
                    "CRITICAL ERROR: Failed to initialize ANY teams for the GA population. Check player data and point ranges.")
                return False
        self._log(f"Population initialized with {len(self.population)} teams.")
        return True

    def _generate_benchmark_teams(self):
        self._log(f"Attempting to generate/load up to {self.num_benchmark_teams} benchmark teams.")
        self.benchmark_teams = []
        num_loaded_successfully = 0

        if self.benchmark_archetype_files:
            self._log(
                f"Found {len(self.benchmark_archetype_files)} custom benchmark file(s) specified: {self.benchmark_archetype_files}")
            for filepath_to_load in self.benchmark_archetype_files:
                if len(self.benchmark_teams) >= self.num_benchmark_teams:
                    self._log(
                        "Reached desired number of benchmark teams from custom files. Skipping remaining custom files.")
                    break

                actual_filepath = filepath_to_load  # Assuming TeamSelectionDialog returns full/correct paths
                self._log(f"  Attempting to load custom benchmark from: '{actual_filepath}'")

                if not os.path.exists(actual_filepath):  # Check if file exists
                    self._log(f"    ERROR: File not found at '{actual_filepath}'. Skipping.")
                    continue

                try:
                    team_obj = load_team_from_json(actual_filepath)
                    if team_obj:
                        # Ensure a unique name for logging, potentially prefix it
                        original_name = team_obj.name
                        team_obj.name = f"CUSTOM_BENCH_{num_loaded_successfully + 1}_{original_name[:20]}"  # Truncate if too long

                        if not hasattr(team_obj, 'team_stats') or team_obj.team_stats is None:
                            team_obj.team_stats = TeamStats()
                        team_obj.team_stats.reset_for_new_season(maintain_elo=False)

                        # Try to get ELO from loaded data, otherwise default
                        # This part assumes load_team_from_json might attach original data or you parse it again.
                        # For simplicity, let's assume load_team_from_json populates team_stats.elo_rating
                        # If not, we need to re-open the JSON here, which is inefficient.
                        # Let's assume the ELO on team_obj.team_stats is what was loaded.
                        # If not, default it:
                        if not hasattr(team_obj.team_stats,
                                       'elo_rating') or team_obj.team_stats.elo_rating < 100:  # Basic check
                            team_obj.team_stats.elo_rating = 1500.0  # Default ELO for benchmarks if not loaded

                        for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                            if not hasattr(p, 'season_stats') or p.season_stats is None:
                                p.season_stats = Stats()
                            else:
                                p.season_stats.reset()
                            if not hasattr(p, 'career_stats') or p.career_stats is None: p.career_stats = Stats()

                        self.benchmark_teams.append(team_obj)
                        num_loaded_successfully += 1
                        self._log(
                            f"    SUCCESS: Loaded '{team_obj.name}' (ELO: {team_obj.team_stats.elo_rating:.0f}) from '{actual_filepath}'.")
                    else:
                        self._log(f"    WARNING: load_team_from_json returned None for '{actual_filepath}'. Skipping.")
                except Exception as e:
                    self._log(f"    ERROR: Exception while loading/processing '{actual_filepath}': {e}. Skipping.")
        else:
            self._log("No custom benchmark archetype files were specified to load (list was empty).")

        self._log(f"Successfully loaded {num_loaded_successfully} custom benchmark team(s).")

        num_random_to_generate = self.num_benchmark_teams - len(self.benchmark_teams)
        if num_random_to_generate > 0:
            self._log(f"Need to generate {num_random_to_generate} additional random benchmark team(s).")
            attempts = 0
            max_attempts_for_random = num_random_to_generate * 10
            generated_count = 0
            while generated_count < num_random_to_generate and attempts < max_attempts_for_random:
                if self.stop_event and self.stop_event.is_set(): break
                team_name = f"Benchmark_Random_{generated_count + 1}"
                team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                if team_obj:
                    if not hasattr(team_obj,
                                   'team_stats') or team_obj.team_stats is None: team_obj.team_stats = TeamStats()
                    team_obj.team_stats.reset_for_new_season(maintain_elo=False)
                    team_obj.team_stats.elo_rating = 1500
                    for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                        if not hasattr(p, 'season_stats') or p.season_stats is None:
                            p.season_stats = Stats()
                        else:
                            p.season_stats.reset()
                        if not hasattr(p, 'career_stats') or p.career_stats is None: p.career_stats = Stats()
                    self.benchmark_teams.append(team_obj)
                    generated_count += 1
                attempts += 1
            if generated_count < num_random_to_generate:
                self._log(
                    f"  Warning: Could only generate {generated_count} of {num_random_to_generate} needed random benchmark teams.")

        if not self.benchmark_teams:
            self._log("CRITICAL ERROR: No benchmark teams were loaded or generated. GA cannot proceed.")
            return False

        self._log(f"Final benchmark team pool size: {len(self.benchmark_teams)}.")
        for i, team in enumerate(self.benchmark_teams):
            self._log(
                f"  Benchmark {i + 1}: {team.name} (ELO: {team.team_stats.elo_rating:.0f}, Points: {team.total_points})")
        return True

    def _calculate_fitness(self, candidate: GACandidate):
        candidate_team = candidate.team
        total_run_differential_for_candidate = 0
        total_games_played_by_candidate_in_eval = 0

        for p in (candidate_team.batters + candidate_team.bench + candidate_team.all_pitchers):
            if not hasattr(p, 'season_stats') or p.season_stats is None:
                p.season_stats = Stats()
            p.season_stats.reset()  # Clean slate for accumulating this evaluation's game stats

        for benchmark_idx, benchmark_team in enumerate(self.benchmark_teams):
            if self.stop_event and self.stop_event.is_set():
                self._log(f"Stop requested during fitness calculation for {candidate_team.name}.")
                candidate.fitness = total_run_differential_for_candidate
                return

            for i in range(self.games_vs_each_benchmark):
                if self.stop_event and self.stop_event.is_set():
                    self._log(f"Stop requested during game simulation for {candidate_team.name}.")
                    candidate.fitness = total_run_differential_for_candidate
                    return

                for p_list in [candidate_team.batters, candidate_team.bench, candidate_team.all_pitchers,
                               benchmark_team.batters, benchmark_team.bench, benchmark_team.all_pitchers]:
                    for p_obj in p_list:
                        if hasattr(p_obj, 'game_stats'):
                            p_obj.game_stats.reset()
                        else:
                            p_obj.game_stats = Stats()

                is_home_game_for_candidate = (i % 2 == 0)

                if is_home_game_for_candidate:
                    away_res, home_res, _, _, _ = play_game(benchmark_team, candidate_team, is_ga_evaluation=True)
                    total_run_differential_for_candidate += (
                                home_res.get('runs_scored', 0) - home_res.get('runs_allowed', 0))
                else:
                    away_res, home_res, _, _, _ = play_game(candidate_team, benchmark_team, is_ga_evaluation=True)
                    total_run_differential_for_candidate += (
                                away_res.get('runs_scored', 0) - away_res.get('runs_allowed', 0))

                total_games_played_by_candidate_in_eval += 1
                candidate_team.post_game_team_cleanup()
                # benchmark_team.post_game_team_cleanup() # Not strictly needed for candidate fitness

        candidate.fitness = total_run_differential_for_candidate

    def _select_parents_tournament(self, k=3):
        parents = []
        for _ in range(2):
            actual_k = min(k, len(self.population))
            if actual_k == 0: return None, None
            if actual_k == 1 and len(self.population) == 1:
                parents.append(self.population[0])
                continue
            if not self.population: return None, None
            tournament_participants = random.sample(self.population, actual_k)
            winner = max(tournament_participants, key=lambda ind: ind.fitness)
            parents.append(winner)

        if len(parents) == 1:
            return parents[0], parents[0]
        elif len(parents) == 2:
            return parents[0], parents[1]
        return None, None

    def _mutate(self, parent_candidate: GACandidate):
        mutated_team_obj = copy.deepcopy(parent_candidate.team)
        base_name_parts = parent_candidate.team.name.split('_')
        original_id = base_name_parts[-1] if base_name_parts[-1].isdigit() else str(random.randint(1000, 9999))
        mutated_team_obj.name = f"GA_Mut_G{self.generation_count}_{original_id}"

        if hasattr(parent_candidate.team, 'team_stats') and parent_candidate.team.team_stats is not None:
            mutated_team_obj.team_stats.elo_rating = parent_candidate.team.team_stats.elo_rating

        for _ in range(self.num_mutation_swaps):
            roster_list_options_mut = [
                (mutated_team_obj.batters, "batter", "Starter"),
                (mutated_team_obj.bench, "batter", "Bench"),
                (mutated_team_obj.starters, "pitcher", "SP"),
                (mutated_team_obj.relievers, "pitcher", "RP"),
                (mutated_team_obj.closers, "pitcher", "CL")]
            eligible_roster_lists_with_type = [(lst, p_type, r_role) for lst, p_type, r_role in roster_list_options_mut
                                               if lst]
            if not eligible_roster_lists_with_type: continue

            list_to_mutate_from, player_type_str, original_role_category = random.choice(
                eligible_roster_lists_with_type)
            player_to_remove_idx = random.randrange(len(list_to_mutate_from))
            player_to_remove = list_to_mutate_from.pop(player_to_remove_idx)
            actual_original_role = player_to_remove.team_role
            original_position_slot = player_to_remove.position

            replacement_found = False
            potential_replacements_pool = self.batters_pool if player_type_str == "batter" else self.pitchers_pool
            current_team_player_ids = set()
            for r_list_key in ["batters", "bench", "starters", "relievers", "closers"]:
                for p_in_team in getattr(mutated_team_obj, r_list_key, []):
                    current_team_player_ids.add((p_in_team.name, p_in_team.year, p_in_team.set))

            potential_replacements = [p for p in potential_replacements_pool
                                      if (p.name, p.year, p.set) != (player_to_remove.name, player_to_remove.year,
                                                                     player_to_remove.set) and \
                                      (p.name, p.year, p.set) not in current_team_player_ids]
            random.shuffle(potential_replacements)

            for new_player_from_pool in potential_replacements:
                new_player = copy.deepcopy(new_player_from_pool)
                can_play_role_and_pos = False
                if isinstance(new_player, Batter):
                    can_play_role_and_pos = new_player.can_play(
                        original_position_slot) if original_role_category == "Starter" else True
                elif isinstance(new_player, Pitcher):
                    if actual_original_role == 'SP' and new_player.position in ['Starter', 'SP', 'P']:
                        can_play_role_and_pos = True
                    elif actual_original_role == 'RP' and new_player.position in ['Reliever', 'RP', 'P']:
                        can_play_role_and_pos = True
                    elif actual_original_role == 'CL' and new_player.position in ['Closer', 'CL', 'P']:
                        can_play_role_and_pos = True

                if not can_play_role_and_pos: continue
                current_points_without_removed = mutated_team_obj.total_points - player_to_remove.pts
                if self.min_points <= (current_points_without_removed + new_player.pts) <= self.max_points:
                    list_to_mutate_from.insert(player_to_remove_idx, new_player)
                    new_player.team_role = actual_original_role
                    if isinstance(new_player,
                                  Batter) and original_role_category == "Starter": new_player.position = original_position_slot
                    new_player.team_name = mutated_team_obj.name
                    mutated_team_obj.total_points = current_points_without_removed + new_player.pts
                    mutated_team_obj.all_pitchers = mutated_team_obj.starters + mutated_team_obj.relievers + mutated_team_obj.closers
                    mutated_team_obj.bullpen = sorted(mutated_team_obj.relievers + mutated_team_obj.closers,
                                                      key=lambda x: x.pts, reverse=True)
                    replacement_found = True;
                    break
            if not replacement_found: list_to_mutate_from.insert(player_to_remove_idx, player_to_remove)
        return GACandidate(mutated_team_obj, is_newly_created=True)

    def request_stop(self):
        if self.stop_event: self.stop_event.set()
        self._log("GA stop requested by external signal.")

    def run(self):
        self._log("Genetic Algorithm Started.")
        if not self._initialize_population():
            self.update_progress_callback(0, "GA Failed: Population Init Error", 0, 0, 0);
            return None
        if not self._generate_benchmark_teams():
            self.update_progress_callback(0, "GA Failed: Benchmark Gen Error", 0, 0, 0);
            return None
        if not self.benchmark_teams:
            self._log("Error: No benchmark teams available. GA cannot run.")
            self.update_progress_callback(0, "GA Failed: No benchmark teams", 0, 0, 0);
            return None

        self.generation_count = 0;
        self.best_fitness_history.clear();
        self.avg_fitness_history.clear();
        self.generation_count_history.clear()
        self._log("Evaluating initial population...")
        total_initial_eval_steps = len(self.population)
        for i in range(total_initial_eval_steps):
            if self.stop_event and self.stop_event.is_set():
                self._log("Stop requested during initial fitness calculation.")
                bf = self.best_individual_overall.fitness if self.best_individual_overall else 0
                self.update_progress_callback(100, "GA Stopped (init eval)", self.generation_count, bf, 0);
                return self.best_individual_overall
            self._calculate_fitness(self.population[i])
            progress_percentage = ((i + 1) / total_initial_eval_steps) * (100 / (self.num_generations + 1))
            self.update_progress_callback(progress_percentage,
                                          f"Gen 0: Evaluating initial pop ({i + 1}/{total_initial_eval_steps})")

        if not self.population:
            self._log("Error: Population empty after initial evaluation.");
            self.update_progress_callback(100, "GA Failed: Pop empty", 0, 0, 0);
            return None

        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        best_initial_fitness = self.population[0].fitness
        avg_initial_fitness = sum(ind.fitness for ind in self.population) / len(
            self.population) if self.population else 0.0
        self.best_individual_overall = copy.deepcopy(self.population[0])
        self.generation_count_history.append(0);
        self.best_fitness_history.append(best_initial_fitness);
        self.avg_fitness_history.append(avg_initial_fitness)
        self._log(
            f"Initial Best: {self.best_individual_overall.team.name}, Fitness(RD): {best_initial_fitness:.0f}, Avg Fitness: {avg_initial_fitness:.0f}")
        self.update_progress_callback((100 / (self.num_generations + 1)),
                                      f"Initial eval complete. Best: {best_initial_fitness:.0f}", 0,
                                      best_initial_fitness, avg_initial_fitness)

        for gen_idx in range(self.num_generations):
            self.generation_count = gen_idx + 1
            if self.stop_event and self.stop_event.is_set(): self._log(
                f"Stop requested at Gen {self.generation_count}."); break
            self._log(f"\n--- Generation {self.generation_count}/{self.num_generations} ---")
            base_gen_progress = (self.generation_count / (self.num_generations + 1)) * 100
            self.update_progress_callback(base_gen_progress, f"Generation {self.generation_count} starting...")
            new_population = []
            if self.elitism_count > 0 and self.elitism_count <= len(self.population):
                elites = sorted(self.population, key=lambda ind: ind.fitness, reverse=True)[:self.elitism_count]
                for elite_cand in elites: new_population.append(
                    GACandidate(copy.deepcopy(elite_cand.team), is_newly_created=False))
            num_immigrants = int(self.population_size * self.immigration_rate)
            for _ in range(num_immigrants):
                if len(new_population) >= self.population_size or (self.stop_event and self.stop_event.is_set()): break
                team_obj = create_random_team(self.all_players,
                                              f"GA_Imm_G{self.generation_count}_{len(new_population)}", self.min_points,
                                              self.max_points)
                if team_obj: new_population.append(GACandidate(team_obj, is_newly_created=True))
            if self.stop_event and self.stop_event.is_set(): self._log("Stop during immigration."); break

            num_offspring_needed = self.population_size - len(new_population)
            for i in range(num_offspring_needed):
                if len(new_population) >= self.population_size or (self.stop_event and self.stop_event.is_set()): break
                parent1, parent2 = self._select_parents_tournament()
                if parent1 is None:
                    self._log("Warn: No parents selected. Filling with random.");
                    team_obj = create_random_team(self.all_players,
                                                  f"GA_Fill_G{self.generation_count}_{len(new_population)}",
                                                  self.min_points, self.max_points)
                    if team_obj: new_population.append(GACandidate(team_obj, is_newly_created=True)); continue
                child_candidate = self._mutate(parent1) if random.random() < self.mutation_rate else GACandidate(
                    copy.deepcopy(parent1.team), is_newly_created=False)
                new_population.append(child_candidate)
            if self.stop_event and self.stop_event.is_set(): self._log("Stop during offspring gen."); break

            self.population = new_population[:self.population_size]
            if not self.population: self._log(f"Warn: Pop empty before eval Gen {self.generation_count}."); break

            total_current_gen_eval_steps = len(self.population)
            for i in range(total_current_gen_eval_steps):
                if self.stop_event and self.stop_event.is_set(): self._log("Stop during new pop fitness calc."); break
                self._calculate_fitness(self.population[i])
                current_eval_progress_in_gen = (
                                                           i + 1) / total_current_gen_eval_steps if total_current_gen_eval_steps > 0 else 1
                total_progress = base_gen_progress + (current_eval_progress_in_gen * (100 / (self.num_generations + 1)))
                self.update_progress_callback(total_progress,
                                              f"Gen {self.generation_count}: Evaluating ({i + 1}/{total_current_gen_eval_steps})")
            if self.stop_event and self.stop_event.is_set(): break
            if not self.population: self._log(f"Warn: Pop empty after eval Gen {self.generation_count}."); break

            self.population.sort(key=lambda ind: ind.fitness, reverse=True)
            current_best_in_gen_obj = self.population[0]
            best_gen_fitness = current_best_in_gen_obj.fitness
            avg_gen_fitness = sum(ind.fitness for ind in self.population) / len(
                self.population) if self.population else 0.0
            self.generation_count_history.append(self.generation_count);
            self.best_fitness_history.append(best_gen_fitness);
            self.avg_fitness_history.append(avg_gen_fitness)
            if best_gen_fitness > self.best_individual_overall.fitness:
                self.best_individual_overall = copy.deepcopy(current_best_in_gen_obj)
                self._log(
                    f"  NEW OVERALL BEST! Gen {self.generation_count}: {self.best_individual_overall.team.name}, Fitness(RD): {best_gen_fitness:.0f}, AvgFit: {avg_gen_fitness:.0f}")
            else:
                self._log(
                    f"  Best this Gen: {current_best_in_gen_obj.team.name}, Fitness(RD): {best_gen_fitness:.0f}, AvgFit: {avg_gen_fitness:.0f} (Overall Best: {self.best_individual_overall.fitness:.0f})")
            self.update_progress_callback(((self.generation_count + 1) / (self.num_generations + 1)) * 100,
                                          f"Gen {self.generation_count} complete. Best: {best_gen_fitness:.0f}",
                                          self.generation_count, best_gen_fitness, avg_gen_fitness)

        final_msg_str = "GA Finished"
        if self.stop_event and self.stop_event.is_set(): final_msg_str = "GA Stopped by user"
        bf = self.best_fitness_history[-1] if self.best_fitness_history else (
            self.best_individual_overall.fitness if self.best_individual_overall else 0)
        af = self.avg_fitness_history[-1] if self.avg_fitness_history else 0
        gn = self.generation_count_history[-1] if self.generation_count_history else self.generation_count
        self.update_progress_callback(100.0, final_msg_str, gn, bf, af)
        self._log(f"\nGenetic Algorithm {final_msg_str}.")

        if self.best_individual_overall:
            self._log(f"Overall Best Team Found: {self.best_individual_overall.team.name}")
            self._log(f"  Fitness (Total Run Differential): {self.best_individual_overall.fitness:.0f}")
            self._log(f"  Total Points: {self.best_individual_overall.team.total_points}")
            for p_list in [self.best_individual_overall.team.batters, self.best_individual_overall.team.bench]:
                for p_obj_final in p_list:
                    if hasattr(p_obj_final,
                               'season_stats') and p_obj_final.season_stats: p_obj_final.season_stats.update_hits()
            if self.best_individual_overall.team.batters:
                b_player = self.best_individual_overall.team.batters[0]
                if hasattr(b_player, 'season_stats') and b_player.season_stats:
                    self._log(
                        f"  FINAL BEST - First batter ({b_player.name}) PA: {b_player.season_stats.plate_appearances}, H: {b_player.season_stats.hits}, R: {b_player.season_stats.runs_scored}, OPS: {b_player.season_stats.calculate_ops()}")
        else:
            self._log("No best individual determined.")
        return self.best_individual_overall