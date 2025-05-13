# optimizer_ga.py
import random
import copy  # For deep copying individuals if necessary

from entities import Team, Batter, Pitcher
from stats import Stats, TeamStats
from team_management import create_random_team  # To generate initial population and new individuals
from game_logic import play_game  # For fitness evaluation


# --- GA Configuration Constants ---
# These can be made configurable in the GUI later
# POPULATION_SIZE = 50
# NUM_GENERATIONS = 100
# MUTATION_RATE_PER_TEAM = 0.8 # Probability that a selected individual will be mutated
# MUTATION_SWAPS_PER_TEAM = 1  # Number of players to try swapping during a mutation event
# ELITISM_COUNT = 5            # Number of best individuals to carry to next generation
# NUM_BENCHMARK_TEAMS = 5      # How many random teams to test fitness against
# GAMES_PER_EVALUATION = 10    # Games to play against each benchmark team (half home/away)
# IMMIGRATION_RATE = 0.1       # Percentage of population to be new random individuals

class GACandidate:
    """Wraps a Team object with its fitness score."""

    def __init__(self, team_object: Team):
        self.team = team_object
        self.fitness = 0.0  # Win percentage

    def __lt__(self, other):  # For sorting by fitness
        return self.fitness < other.fitness

    def __repr__(self):
        return f"GACandidate({self.team.name}, Fitness: {self.fitness:.4f})"


class GeneticTeamOptimizer:
    def __init__(self, all_players_list,
                 population_size=20,  # Smaller for faster testing
                 num_generations=10,  # Fewer for faster testing
                 mutation_rate=0.7,
                 num_mutation_swaps=1,
                 elitism_count=2,
                 num_benchmark_teams=3,
                 games_per_benchmark_team=6,  # Total games = num_benchmark_teams * games_per_benchmark_team
                 immigration_rate=0.1,
                 min_team_points=4500,  # From constants
                 max_team_points=5000,  # From constants
                 log_callback=None,
                 update_progress_callback=None):  # For GUI progress bar

        self.all_players = all_players_list
        self.population_size = population_size
        self.num_generations = num_generations
        self.mutation_rate = mutation_rate
        self.num_mutation_swaps = num_mutation_swaps
        self.elitism_count = elitism_count
        self.num_benchmark_teams = num_benchmark_teams
        self.games_per_benchmark_team = games_per_benchmark_team  # Total games per candidate team
        self.immigration_rate = immigration_rate  # Percentage of new random individuals per generation
        self.min_points = min_team_points
        self.max_points = max_team_points

        self.log_callback = log_callback if callable(log_callback) else print
        self.update_progress_callback = update_progress_callback if callable(update_progress_callback) else lambda p,
                                                                                                                   m: None

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
        max_attempts_per_team = 50  # Prevent infinite loop if create_random_team struggles

        while len(self.population) < self.population_size and attempts < self.population_size * max_attempts_per_team:
            team_name = f"GA_Team_Init_{len(self.population) + 1}"
            # Ensure create_random_team is robust and uses min_points, max_points correctly
            team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
            if team_obj:
                self.population.append(GACandidate(team_obj))
            attempts += 1

        if len(self.population) < self.population_size:
            self._log(f"Warning: Could only initialize {len(self.population)}/{self.population_size} teams.")
            if not self.population:
                raise ValueError("Failed to initialize any teams for the GA population.")
        self._log("Population initialized.")

    def _generate_benchmark_teams(self):
        self._log(f"Generating {self.num_benchmark_teams} benchmark teams...")
        self.benchmark_teams = []
        attempts = 0
        max_attempts_per_team = 50

        while len(
                self.benchmark_teams) < self.num_benchmark_teams and attempts < self.num_benchmark_teams * max_attempts_per_team:
            team_name = f"Benchmark_{len(self.benchmark_teams) + 1}"
            team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
            if team_obj:
                # Reset stats for benchmark teams to ensure fair evaluation
                if hasattr(team_obj, 'team_stats') and team_obj.team_stats is not None:
                    team_obj.team_stats.reset_for_new_season(maintain_elo=False)  # Start benchmark ELO fresh
                for p in (team_obj.batters + team_obj.bench + team_obj.all_pitchers):
                    if hasattr(p, 'season_stats'): p.season_stats.reset()
                    if hasattr(p, 'career_stats'): p.career_stats.reset()  # Reset career for benchmark context
                self.benchmark_teams.append(team_obj)
            attempts += 1

        if not self.benchmark_teams:
            raise ValueError("Failed to generate any benchmark teams. GA cannot proceed.")
        self.log_callback(f"Generated {len(self.benchmark_teams)} benchmark teams.")

    def _calculate_fitness(self, candidate: GACandidate):
        """Simulates games for a candidate team against benchmark teams."""
        candidate_team = candidate.team
        total_wins = 0
        total_games_played = 0

        # Reset candidate team's season stats before evaluation for this generation
        if hasattr(candidate_team, 'team_stats') and candidate_team.team_stats is not None:
            candidate_team.team_stats.reset_for_new_season(maintain_elo=True)  # Maintain ELO for candidate
        for p in (candidate_team.batters + candidate_team.bench + candidate_team.all_pitchers):
            if hasattr(p, 'season_stats'): p.season_stats.reset()
            # Career stats are not reset here as they are cumulative across GA generations for the individual lineage

        for benchmark_team in self.benchmark_teams:
            games_this_opponent = self.games_per_benchmark_team // len(self.benchmark_teams)  # Distribute games
            if games_this_opponent == 0 and self.games_per_benchmark_team > 0: games_this_opponent = 1  # Play at least one game if total > 0

            for i in range(games_this_opponent):
                # Simulate game (e.g., candidate is home for half, away for half)
                # For simplicity, let's alternate. A more robust way might be to play fixed home/away counts.
                if i % 2 == 0:  # Candidate is home
                    _, home_result, _, _, _ = play_game(benchmark_team, candidate_team)  # benchmark is away
                    if home_result.get('win', False):
                        total_wins += 1
                else:  # Candidate is away
                    away_result, _, _, _, _ = play_game(candidate_team, benchmark_team)  # candidate is away
                    if away_result.get('win', False):
                        total_wins += 1
                total_games_played += 1

        candidate.fitness = (total_wins / total_games_played) if total_games_played > 0 else 0.0
        # self._log(f"  Fitness for {candidate_team.name}: {candidate.fitness:.4f} ({total_wins}/{total_games_played})")

    def _select_parents_tournament(self, k=3):
        """Selects two parents using tournament selection."""
        parents = []
        for _ in range(2):  # Select two parents
            tournament_participants = random.sample(self.population, k)
            winner = max(tournament_participants, key=lambda ind: ind.fitness)
            parents.append(winner)
        return parents[0], parents[1]  # parent1, parent2

    def _mutate(self, candidate: GACandidate):
        """
        Mutates a team by attempting to swap a few players.
        Ensures the team remains valid regarding roster rules and point caps.
        """
        team_to_mutate = copy.deepcopy(candidate.team)  # Work on a copy
        mutated_successfully = False

        for _ in range(self.num_mutation_swaps):  # Try to swap a few players
            roster_list_options = [team_to_mutate.batters, team_to_mutate.bench,
                                   team_to_mutate.starters, team_to_mutate.relievers, team_to_mutate.closers]

            # Choose a random roster list that is not empty
            eligible_roster_lists = [lst for lst in roster_list_options if lst]
            if not eligible_roster_lists: continue  # No players to mutate

            list_to_mutate_from = random.choice(eligible_roster_lists)
            player_to_remove_idx = random.randrange(len(list_to_mutate_from))
            player_to_remove = list_to_mutate_from.pop(player_to_remove_idx)

            # Determine the role/position needed for replacement
            original_role = player_to_remove.team_role
            original_position = player_to_remove.position  # For batters, this is their field position

            # Try to find a replacement
            replacement_found = False
            potential_replacements = []
            if isinstance(player_to_remove, Batter):
                potential_replacements = [p for p in self.batters_pool if
                                          p.name != player_to_remove.name]  # Avoid self-replacement
            elif isinstance(player_to_remove, Pitcher):
                potential_replacements = [p for p in self.pitchers_pool if p.name != player_to_remove.name]

            random.shuffle(potential_replacements)

            for new_player in potential_replacements:
                # Check if new_player is already on the team (excluding the one just removed)
                current_team_player_names = {p.name for p_list in roster_list_options for p in p_list}
                if new_player.name in current_team_player_names:
                    continue

                # Check positional eligibility for the specific slot
                # This is complex because the original player might have been placed due to general eligibility
                # For simplicity, we'll try to match the original role/position broadly.
                # A more robust check would involve re-validating the whole roster structure.

                # For batters, original_position is their specific field slot (e.g. 'CF', '1B')
                # For pitchers, original_role is 'SP', 'RP', 'CL'

                can_play_role = False
                if isinstance(player_to_remove, Batter):
                    # If it was a starter, new player must be able to play that specific position
                    # If it was bench, any batter is fine.
                    if original_role == "Starter":
                        can_play_role = new_player.can_play(original_position)
                    else:  # Bench
                        can_play_role = True
                elif isinstance(player_to_remove, Pitcher):
                    if original_role == 'SP' and new_player.position in ['Starter', 'SP', 'P']:
                        can_play_role = True
                    elif original_role == 'RP' and new_player.position in ['Reliever', 'RP', 'P']:
                        can_play_role = True
                    elif original_role == 'CL' and new_player.position in ['Closer', 'CL', 'P']:
                        can_play_role = True

                if not can_play_role:
                    continue

                # Check point cap
                new_team_points = sum(p.pts for p_list in roster_list_options for p in p_list) + new_player.pts
                if self.min_points <= new_team_points <= self.max_points:
                    list_to_mutate_from.insert(player_to_remove_idx, new_player)  # Add new player
                    new_player.team_role = original_role  # Assign role
                    if isinstance(new_player, Batter) and original_role == "Starter":
                        new_player.position = original_position  # Assign specific position
                    else:
                        new_player.position = new_player.position  # Keep their card position if not a starter batter

                    team_to_mutate.total_points = new_team_points  # Update team total points
                    mutated_successfully = True
                    replacement_found = True
                    break  # Found a replacement

            if not replacement_found:  # Could not find a valid replacement
                list_to_mutate_from.insert(player_to_remove_idx, player_to_remove)  # Add original back

        if mutated_successfully:
            # Reconstruct the Team object to ensure all internal lists are correct
            # This is a bit heavy but safer after manual roster manipulation
            final_mutated_team = Team(
                name=team_to_mutate.name,  # Keep original name or generate new
                batters=[p for p in team_to_mutate.batters],
                starters=[p for p in team_to_mutate.starters],
                relievers=[p for p in team_to_mutate.relievers],
                closers=[p for p in team_to_mutate.closers],
                bench=[p for p in team_to_mutate.bench]
            )
            final_mutated_team.team_stats = copy.deepcopy(team_to_mutate.team_stats)  # Preserve team stats object
            return GACandidate(final_mutated_team)
        else:
            return candidate  # Return original if no successful mutation

    def run(self):
        self._log("Genetic Algorithm Started.")
        self._initialize_population()
        self._generate_benchmark_teams()
        if not self.benchmark_teams: return None  # Cannot proceed

        self.generation_count = 0
        for i in range(self.population_size):
            self._calculate_fitness(self.population[i])
            progress = (i + 1) / self.population_size * 100 / (
                        self.num_generations + 1)  # Rough progress for first eval
            self.update_progress_callback(progress,
                                          f"Gen 0: Evaluating initial population ({i + 1}/{self.population_size})")

        self.population.sort(key=lambda ind: ind.fitness, reverse=True)  # Sort by fitness desc
        self.best_individual_overall = self.population[0]
        self._log(
            f"Initial Best: {self.best_individual_overall.team.name}, Fitness: {self.best_individual_overall.fitness:.4f}")

        for gen in range(self.num_generations):
            self.generation_count = gen + 1
            self._log(f"\n--- Generation {self.generation_count}/{self.num_generations} ---")
            self.update_progress_callback(
                (gen + 1) / (self.num_generations + 1) * 100,  # Add 1 to num_generations for initial eval step
                f"Generation {self.generation_count}"
            )

            new_population = []

            # Elitism
            if self.elitism_count > 0:
                elites = self.population[:self.elitism_count]
                new_population.extend(elites)
                # self._log(f"  Elites carried over: {[e.team.name for e in elites]}")

            # Immigration (new random individuals)
            num_immigrants = int(self.population_size * self.immigration_rate)
            for _ in range(num_immigrants):
                if len(new_population) >= self.population_size: break
                team_name = f"GA_Team_Gen{self.generation_count}_Imm_{len(new_population)}"
                team_obj = create_random_team(self.all_players, team_name, self.min_points, self.max_points)
                if team_obj:
                    new_population.append(GACandidate(team_obj))
            # self._log(f"  Added {num_immigrants} new immigrant teams.")

            # Offspring via Mutation from selected parents
            num_offspring_needed = self.population_size - len(new_population)
            offspring_generated_count = 0
            for i in range(num_offspring_needed):
                parent1, _ = self._select_parents_tournament()  # Only need one parent for mutation-based offspring

                child_candidate = parent1  # Start with parent
                if random.random() < self.mutation_rate:
                    child_candidate = self._mutate(parent1)

                new_population.append(child_candidate)
                offspring_generated_count += 1
            # self._log(f"  Generated {offspring_generated_count} offspring via mutation.")

            self.population = new_population[:self.population_size]  # Ensure population size is maintained

            # Evaluate new population members (immigrants and offspring)
            # Elites don't need re-evaluation unless benchmark changes or fitness is noisy
            eval_start_index = self.elitism_count if self.elitism_count > 0 else 0
            for i in range(eval_start_index, len(self.population)):
                self._calculate_fitness(self.population[i])
                # Update progress for evaluation within a generation
                current_progress_in_gen = (i + 1 - eval_start_index) / (len(self.population) - eval_start_index)
                total_progress = ((gen + 1) + current_progress_in_gen) / (self.num_generations + 1) * 100
                self.update_progress_callback(total_progress,
                                              f"Gen {self.generation_count}: Evaluating new individuals ({i + 1 - eval_start_index}/{len(self.population) - eval_start_index})")

            self.population.sort(key=lambda ind: ind.fitness, reverse=True)
            current_best_in_gen = self.population[0]

            if current_best_in_gen.fitness > self.best_individual_overall.fitness:
                self.best_individual_overall = current_best_in_gen
                self._log(
                    f"  NEW OVERALL BEST! Gen {self.generation_count}: {self.best_individual_overall.team.name}, Fitness: {self.best_individual_overall.fitness:.4f}")
            else:
                self._log(
                    f"  Best this Gen: {current_best_in_gen.team.name}, Fitness: {current_best_in_gen.fitness:.4f} (Overall: {self.best_individual_overall.fitness:.4f})")

        self._log("\nGenetic Algorithm Finished.")
        self._log(f"Overall Best Team: {self.best_individual_overall.team.name}")
        self._log(f"  Fitness (Win %): {self.best_individual_overall.fitness:.4f}")
        self._log(f"  Total Points: {self.best_individual_overall.team.total_points}")
        # self._log(f"  Roster: {self.best_individual_overall.team}") # May be too verbose

        return self.best_individual_overall

