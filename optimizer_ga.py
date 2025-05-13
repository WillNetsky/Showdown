# optimizer_ga.py
import random
import copy

from entities import Team, Batter, Pitcher
from stats import Stats, TeamStats
from team_management import create_random_team
from game_logic import play_game


class GACandidate:
    """Wraps a Team object with its fitness score (now Run Differential)."""

    def __init__(self, team_object: Team, is_newly_created=True):
        self.team = team_object
        self.fitness = 0.0  # Now represents total Run Differential from evaluation games

        if not hasattr(self.team, 'team_stats') or self.team.team_stats is None:
            self.team.team_stats = TeamStats()
        original_elo = self.team.team_stats.elo_rating
        self.team.team_stats.reset_for_new_season(maintain_elo=True)
        self.team.team_stats.elo_rating = original_elo

        for p in (self.team.batters + self.team.bench + self.team.all_pitchers):
            if not hasattr(p, 'season_stats') or p.season_stats is None or is_newly_created:
                p.season_stats = Stats()
            else:
                p.season_stats.reset()
            if not hasattr(p, 'career_stats') or p.career_stats is None:
                p.career_stats = Stats()

    def __lt__(self, other):
        return self.fitness < other.fitness  # Higher run differential is better

    def __repr__(self):
        return f"GACandidate({self.team.name}, Fitness (RunDiff): {self.fitness:.0f})"


class GeneticTeamOptimizer:
    def __init__(self, all_players_list,
                 population_size=30,  # Slightly increased default
                 num_generations=20,  # Slightly increased default
                 mutation_rate=0.8,  # Increased default
                 num_mutation_swaps=1,  # Can try 1-2
                 elitism_count=3,  # Increased default
                 num_benchmark_teams=5,  # Increased default
                 games_per_benchmark_team=10,  # Increased (Total eval games = 5 * 10 = 50 per candidate)
                 immigration_rate=0.1,
                 min_team_points=4500,
                 max_team_points=5000,
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
        self.games_per_benchmark_team = games_per_benchmark_team
        self.immigration_rate = immigration_rate
        self.min_points = min_team_points
        self.max_points = max_team_points
        self.stop_event = stop_event

        self.log_callback = log_callback if callable(log_callback) else print
        self.update_progress_callback = update_progress_callback if callable(update_progress_callback) else lambda p, m: None

        self.population = []
        self.benchmark_teams = []
        self.best_individual_overall = None
        self.generation_count = 0

        self.batters_pool = [p for p in self.all_players if isinstance(p, Batter)]
        self.pitchers_pool = [p for p in self.all_players if isinstance(p, Pitcher)]

    def _log(self, message):
        self.log_callback(f"[GA] {message}")

    def _initialize_population(self):
        self._log(f"Initializing population of {self.population_size} teams...")
        self.population = []
        attempts = 0
        max_attempts_per_team = self.population_size * 10

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
            self._log(f"Warning: Could only initialize {len(self.population)}/{self.population_size} teams.")
            if not self.population:
                raise ValueError("Failed to initialize any teams for the GA population.")
        self._log(f"Population initialized with {len(self.population)} teams.")
        return True

    def _generate_benchmark_teams(self):
        self._log(f"Generating {self.num_benchmark_teams} benchmark teams...")
        self.benchmark_teams = []
        attempts = 0
        max_attempts_per_team = self.num_benchmark_teams * 10

        while len(self.benchmark_teams) < self.num_benchmark_teams and attempts < max_attempts_per_team:
            if self.stop_event and self.stop_event.is_set():
                self._log("Stop requested during benchmark team generation.")
                return False
            team_name = f"Benchmark_{len(self.benchmark_teams) + 1}"
            team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
            if team_obj:
                if not hasattr(team_obj, 'team_stats') or team_obj.team_stats is None: team_obj.team_stats = TeamStats()
                team_obj.team_stats.reset_for_new_season(maintain_elo=False)
                for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                    if not hasattr(p, 'season_stats') or p.season_stats is None:
                        p.season_stats = Stats()
                    else:
                        p.season_stats.reset()
                    if not hasattr(p, 'career_stats') or p.career_stats is None:
                        p.career_stats = Stats()
                    else:
                        p.career_stats.reset()
                self.benchmark_teams.append(team_obj)
            attempts += 1

        if not self.benchmark_teams:
            raise ValueError("Failed to generate any benchmark teams. GA cannot proceed.")
        self.log_callback(f"Generated {len(self.benchmark_teams)} benchmark teams.")
        return True

    def _calculate_fitness(self, candidate: GACandidate):
        candidate_team = candidate.team
        total_run_differential_for_candidate = 0  # MODIFIED: Track run differential
        total_games_played = 0

        candidate_team.team_stats.reset_for_new_season(maintain_elo=True,
                                                       team_name_for_debug=candidate_team.name + "_GA_Eval")

        # Player season_stats are already fresh due to GACandidate constructor or _mutate logic
        # self._log(f"  Evaluating fitness for {candidate_team.name} (ELO: {candidate_team.team_stats.elo_rating:.0f})...")

        for benchmark_idx, benchmark_team in enumerate(self.benchmark_teams):
            if self.stop_event and self.stop_event.is_set():
                self._log(f"Stop requested during fitness calculation for {candidate_team.name}.")
                return

            base_games = self.games_per_benchmark_team // self.num_benchmark_teams
            extra_games = self.games_per_benchmark_team % self.num_benchmark_teams
            games_this_opponent = base_games + (1 if benchmark_idx < extra_games else 0)

            for i in range(games_this_opponent):
                if self.stop_event and self.stop_event.is_set():
                    self._log(f"Stop requested during game simulation for {candidate_team.name}.")
                    return

                for p_list in [candidate_team.batters, candidate_team.bench, candidate_team.all_pitchers,
                               benchmark_team.batters, benchmark_team.bench, benchmark_team.all_pitchers]:
                    for p in p_list:
                        if hasattr(p, 'game_stats'):
                            p.game_stats.reset()
                        else:
                            p.game_stats = Stats()

                if i % 2 == 0:
                    away_res, home_res, _, _, _ = play_game(benchmark_team, candidate_team)
                    # For candidate (home_team): RD = home_runs_scored - home_runs_allowed
                    total_run_differential_for_candidate += (
                            home_res.get('runs_scored', 0) - home_res.get('runs_allowed', 0))
                else:
                    away_res, home_res, _, _, _ = play_game(candidate_team, benchmark_team)
                    # For candidate (away_team): RD = away_runs_scored - away_runs_allowed
                    total_run_differential_for_candidate += (
                            away_res.get('runs_scored', 0) - away_res.get('runs_allowed', 0))
                total_games_played += 1

                candidate_team.post_game_team_cleanup()
                benchmark_team.post_game_team_cleanup()

        candidate.fitness = total_run_differential_for_candidate  # Fitness is now total RD
        # self._log(f"  Fitness (RunDiff) for {candidate_team.name}: {candidate.fitness:.0f} ({total_games_played} games)")

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
            winner = max(tournament_participants, key=lambda ind: ind.fitness)  # Max RD is better
            parents.append(winner)
        if len(parents) < 2 and len(parents) == 1:
            return parents[0], parents[0]
        elif not parents:
            return None, None
        return parents[0], parents[1]

    def _mutate(self, parent_candidate: GACandidate):
        mutated_team_obj = copy.deepcopy(parent_candidate.team)
        mutated_team_obj.name = f"GA_Mut_{parent_candidate.team.name.split('_')[-1]}_{self.generation_count}"  # Shorter name

        if hasattr(parent_candidate.team, 'team_stats') and parent_candidate.team.team_stats is not None:
            mutated_team_obj.team_stats.elo_rating = parent_candidate.team.team_stats.elo_rating

        mutated_successfully_at_least_once = False
        for _ in range(self.num_mutation_swaps):
            roster_list_options_mut = [
                (mutated_team_obj.batters, "batter"), (mutated_team_obj.bench, "batter"),
                (mutated_team_obj.starters, "pitcher"), (mutated_team_obj.relievers, "pitcher"),
                (mutated_team_obj.closers, "pitcher")
            ]
            eligible_roster_lists_with_type = [(lst, type_str) for lst, type_str in roster_list_options_mut if lst]
            if not eligible_roster_lists_with_type: continue

            list_to_mutate_from, player_type_str = random.choice(eligible_roster_lists_with_type)
            if not list_to_mutate_from: continue

            player_to_remove_idx = random.randrange(len(list_to_mutate_from))
            player_to_remove = list_to_mutate_from.pop(player_to_remove_idx)

            original_role = player_to_remove.team_role
            original_position_slot = player_to_remove.position

            replacement_found = False
            potential_replacements_pool = self.batters_pool if player_type_str == "batter" else self.pitchers_pool

            current_team_player_ids = set()
            for r_list_key in ["batters", "bench", "starters", "relievers", "closers"]:
                for p_in_team in getattr(mutated_team_obj, r_list_key, []):
                    current_team_player_ids.add((p_in_team.name, p_in_team.year, p_in_team.set))

            potential_replacements = [
                p for p in potential_replacements_pool
                if (p.name, p.year, p.set) != (player_to_remove.name, player_to_remove.year, player_to_remove.set) and \
                   (p.name, p.year, p.set) not in current_team_player_ids
            ]
            random.shuffle(potential_replacements)

            for new_player_from_pool in potential_replacements:
                new_player = copy.deepcopy(new_player_from_pool)
                can_play_role = False
                if isinstance(new_player, Batter):
                    if original_role == "Starter":
                        can_play_role = new_player.can_play(original_position_slot)
                    else:
                        can_play_role = True
                elif isinstance(new_player, Pitcher):
                    if original_role == 'SP' and new_player.position in ['Starter', 'SP', 'P']:
                        can_play_role = True
                    elif original_role == 'RP' and new_player.position in ['Reliever', 'RP', 'P']:
                        can_play_role = True
                    elif original_role == 'CL' and new_player.position in ['Closer', 'CL', 'P']:
                        can_play_role = True

                if not can_play_role: continue

                current_points_without_removed = mutated_team_obj.total_points - player_to_remove.pts
                new_total_points_with_new = current_points_without_removed + new_player.pts

                if self.min_points <= new_total_points_with_new <= self.max_points:
                    list_to_mutate_from.insert(player_to_remove_idx, new_player)
                    new_player.team_role = original_role
                    new_player.position = original_position_slot if isinstance(new_player,
                                                                               Batter) and original_role == "Starter" else new_player.position
                    new_player.team_name = mutated_team_obj.name

                    mutated_team_obj.total_points = new_total_points_with_new
                    mutated_team_obj.all_pitchers = mutated_team_obj.starters + mutated_team_obj.relievers + mutated_team_obj.closers
                    mutated_team_obj.bullpen = sorted(mutated_team_obj.relievers + mutated_team_obj.closers,
                                                      key=lambda x: x.pts, reverse=True)

                    mutated_successfully_at_least_once = True
                    replacement_found = True
                    break

            if not replacement_found:
                list_to_mutate_from.insert(player_to_remove_idx, player_to_remove)

        return GACandidate(mutated_team_obj, is_newly_created=True)

    def request_stop(self):
        if self.stop_event:
            self.stop_event.set()
        self._log("GA stop requested by external signal.")

    def run(self):
        self._log("Genetic Algorithm Started.")
        if not self._initialize_population(): return None
        if not self._generate_benchmark_teams(): return None
        if not self.benchmark_teams:
            self._log("Error: No benchmark teams generated. GA cannot run.")
            return None

        self.generation_count = 0
        self._log("Evaluating initial population...")
        for i in range(len(self.population)):
            if self.stop_event and self.stop_event.is_set(): self._log(
                "Stop requested before initial fitness calc."); return self.best_individual_overall
            self._calculate_fitness(self.population[i])
            progress = ((i + 1) / len(self.population)) * (100 / (self.num_generations + 1))
            self.update_progress_callback(progress,
                                          f"Gen 0: Evaluating initial population ({i + 1}/{len(self.population)})")

        if not self.population:
            self._log("Error: Population is empty after initialization.")
            return None

        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        if self.population:
            self.best_individual_overall = copy.deepcopy(self.population[0])
            self._log(
                f"Initial Best: {self.best_individual_overall.team.name}, Fitness (RunDiff): {self.best_individual_overall.fitness:.0f}, Points: {self.best_individual_overall.team.total_points}")
        else:
            self._log("Warning: Population empty after initial evaluation. Cannot determine initial best.")
            return None

        for gen in range(self.num_generations):
            if self.stop_event and self.stop_event.is_set(): self._log(
                f"Stop requested at start of Generation {gen + 1}."); break
            self.generation_count = gen + 1
            self._log(f"\n--- Generation {self.generation_count}/{self.num_generations} ---")

            base_gen_progress = ((self.generation_count) / (self.num_generations + 1)) * 100
            self.update_progress_callback(base_gen_progress, f"Generation {self.generation_count}")

            new_population = []

            if self.elitism_count > 0 and self.elitism_count <= len(self.population):
                for elite_cand in self.population[:self.elitism_count]:
                    new_population.append(GACandidate(copy.deepcopy(elite_cand.team),
                                                      is_newly_created=False))  # Elites are not "new" for stat reset

            num_immigrants = int(self.population_size * self.immigration_rate)
            immigrants_added = 0
            for _ in range(num_immigrants):
                if len(new_population) >= self.population_size: break
                if self.stop_event and self.stop_event.is_set(): break
                team_name = f"GA_Team_Gen{self.generation_count}_Imm_{immigrants_added}"
                team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                if team_obj:
                    new_population.append(GACandidate(team_obj, is_newly_created=True))
                    immigrants_added += 1
            if self.stop_event and self.stop_event.is_set(): self._log("Stop requested during immigration."); break

            num_offspring_needed = self.population_size - len(new_population)
            for i in range(num_offspring_needed):
                if len(new_population) >= self.population_size: break
                if self.stop_event and self.stop_event.is_set(): break

                parents = self._select_parents_tournament()
                if parents[0] is None:
                    self._log(
                        "Warning: Could not select parents, using random immigrant if possible or skipping offspring.")
                    if immigrants_added < self.population_size - len(new_population):
                        team_name = f"GA_Team_Gen{self.generation_count}_Fill_{i}"
                        team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                        if team_obj: new_population.append(GACandidate(team_obj, is_newly_created=True))
                    continue

                parent1 = parents[0]
                child_candidate = self._mutate(parent1)  # _mutate returns a new GACandidate
                new_population.append(child_candidate)

            if self.stop_event and self.stop_event.is_set(): self._log(
                "Stop requested during offspring generation."); break

            self.population = new_population[:self.population_size]

            # Evaluate all members of the new population (elites were re-wrapped as GACandidates with fresh season stats)
            for i in range(len(self.population)):
                if self.stop_event and self.stop_event.is_set(): self._log(
                    "Stop requested during new population fitness calc."); break
                self._calculate_fitness(self.population[i])

                if len(self.population) > 0:
                    current_eval_progress_in_gen = (i + 1) / len(self.population)
                    total_progress = base_gen_progress + (
                            current_eval_progress_in_gen * (100 / (self.num_generations + 1)))
                    self.update_progress_callback(total_progress,
                                                  f"Gen {self.generation_count}: Evaluating ({i + 1}/{len(self.population)})")
            if self.stop_event and self.stop_event.is_set(): break

            if not self.population:
                self._log(f"Warning: Population became empty during generation {self.generation_count}. Stopping.")
                break

            self.population.sort(key=lambda ind: ind.fitness, reverse=True)
            current_best_in_gen = self.population[0] if self.population else None

            if current_best_in_gen and \
                    (self.best_individual_overall is None or \
                     current_best_in_gen.fitness > self.best_individual_overall.fitness):

                self.best_individual_overall = copy.deepcopy(current_best_in_gen)
                self._log(
                    f"  NEW OVERALL BEST! Gen {self.generation_count}: {self.best_individual_overall.team.name}, Fitness (RunDiff): {self.best_individual_overall.fitness:.0f}, Points: {self.best_individual_overall.team.total_points}")
                if self.best_individual_overall.team.batters:
                    first_batter_stats = self.best_individual_overall.team.batters[0].season_stats
                    first_batter_stats.update_hits()
                    self._log(
                        f"    DEBUG (New Best): {self.best_individual_overall.team.batters[0].name} - PA: {first_batter_stats.plate_appearances}, H: {first_batter_stats.hits}, R: {first_batter_stats.runs_scored}")

            elif current_best_in_gen:
                self._log(
                    f"  Best this Gen: {current_best_in_gen.team.name}, Fitness (RunDiff): {current_best_in_gen.fitness:.0f} (Overall Best Fitness: {self.best_individual_overall.fitness if self.best_individual_overall else 'N/A':.0f})")

        self.update_progress_callback(100, "GA Finished or Stopped.")
        self._log("\nGenetic Algorithm Finished or Stopped.")
        if self.best_individual_overall:
            self._log(f"Overall Best Team Found: {self.best_individual_overall.team.name}")
            self._log(f"  Fitness (Total Run Differential): {self.best_individual_overall.fitness:.0f}")
            self._log(f"  Total Points: {self.best_individual_overall.team.total_points}")

            # Ensure hits are updated on the final best individual's player stats before returning
            for p_list in [self.best_individual_overall.team.batters, self.best_individual_overall.team.bench]:
                for p in p_list:
                    if hasattr(p, 'season_stats') and p.season_stats:
                        p.season_stats.update_hits()

            if self.best_individual_overall.team.batters:
                b_player = self.best_individual_overall.team.batters[0]
                if hasattr(b_player, 'season_stats') and b_player.season_stats:
                    self._log(
                        f"  FINAL BEST - First batter ({b_player.name}) PA: {b_player.season_stats.plate_appearances}, H: {b_player.season_stats.hits}, R: {b_player.season_stats.runs_scored}")
                else:
                    self._log(f"  FINAL BEST - First batter ({b_player.name}) has no season_stats or it's None.")
        else:
            self._log("No best individual determined (e.g., GA stopped very early or failed to initialize).")

        return self.best_individual_overall
