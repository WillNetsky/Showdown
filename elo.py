# elo.py
# Implementation of elo ratings for baseball

from entities import Team

def expected_score(rating_a, rating_b):
    """
      Calculates the expected score of player A in a match against player B.

      Args:
        rating_a: Elo rating of player A.
        rating_b: Elo rating of player B.

      Returns:
        The expected score of player A (between 0 and 1).
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_ratings(team_a: Team, team_b: Team, score_a, k=32):
    """
      Updates the Elo ratings of two players after a match.

      Args:
        rating_a: Elo rating of player A before the match.
        rating_b: Elo rating of player B before the match.
        score_a: Score of player A (1 for win, 0.5 for draw, 0 for loss).
        k: K-factor, determines the maximum rating adjustment.

      Returns:
        A tuple containing the updated Elo ratings for player A and player B.
    """
    expected_a = expected_score(team_a.elo_rating, team_b.elo_rating)
    expected_b = expected_score(team_b.elo_rating, team_a.elo_rating)
    team_a.elo_rating = team_a.elo_rating + k * (score_a - expected_a)
    team_b.elo_rating = team_b.elo_rating + k * ((1 - score_a) - expected_b)

#
# if __name__ == '__main__':
    # player_a_rating = 1500
    # player_b_rating = 1400
    #
    # # Player A wins
    # player_a_rating, player_b_rating = update_ratings(player_a_rating, player_b_rating, 1)
    # print(f"Player A rating: {player_a_rating:.2f}, Player B rating: {player_b_rating:.2f}")
    #
    # # Player B wins
    # player_a_rating, player_b_rating = update_ratings(player_a_rating, player_b_rating, 0)
    # print(f"Player A rating: {player_a_rating:.2f}, Player B rating: {player_b_rating:.2f}")
    #
    # # Match is a draw
    # player_a_rating, player_b_rating = update_ratings(player_a_rating, player_b_rating, 0.5)
    # print(f"Player A rating: {player_a_rating:.2f}, Player B rating: {player_b_rating:.2f}")