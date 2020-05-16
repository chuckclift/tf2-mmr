#!/usr/bin/env python3
"""
This script calculates the mmr of players in the game_logs.json file using
the trueskill ranking algorithm.  It stores the results in player_scores.csv.
"""

import json
from typing import Dict, Iterator, List, Tuple, Any
import trueskill # type: ignore
from steam.steamid import SteamID # type: ignore


player_ratings = {} # type: Dict[int, Any]


def get_sorted_games():  # type: () -> Iterator[Dict]
    """
    This function yields game logs one at a time, sorted by their upload
    time
    """

    log_index = []  # type: List[Tuple[int, int]]
    with open("game_logs.json", encoding="utf-8") as game_log:
        start = 0  # pylint: disable=C0103
        while True:
            gdata = game_log.readline()

            # if the end of file has been reached, an empty string is returned
            if gdata == "":
                break

            game_data = json.loads(gdata)
            log_index.append((game_data["info"]["date"], start))
            start = game_log.tell()

        log_index.sort()
        for _, location in log_index:
            game_log.seek(location)
            yield json.loads(game_log.readline())


for game in get_sorted_games():
    # creating ratings for new players
    for player_id in game["players"]:
        if player_id not in player_ratings:
            player_ratings[player_id] = trueskill.Rating()

    red_ids = [i for i in game["players"]
               if game["players"][i]["team"] == "Red"]
    blue_ids = [i for i in game["players"]
                if game["players"][i]["team"] == "Blue"]

    red_ratings = [player_ratings[i] for i in red_ids]
    blue_ratings = [player_ratings[i] for i in blue_ids]

    if not red_ratings or not blue_ratings:
        # ignoring games without an opposing team
        continue

    if game["teams"]["Red"]["score"] > game["teams"]["Blue"]["score"]:
        # Red Victory
        ranks = [0, 1]
    elif game["teams"]["Red"]["score"] < game["teams"]["Blue"]["score"]:
        # Blue victory
        ranks = [1, 0]
    else:
        # tie
        ranks = [0, 0]

    # the "ranks" parameter specifies which place each team came in.
    # The first number, in this case refers to red, and the second to
    # blue. 0 is "first" 1 is "second"
    new_ratings = trueskill.rate([red_ratings, blue_ratings], ranks=ranks)

    [new_red_ratings, new_blue_ratings] = new_ratings

    for pid, rank in zip(red_ids, new_red_ratings):
        player_ratings[pid] = rank

    for pid, rank in zip(blue_ids, new_blue_ratings):
        player_ratings[pid] = rank

with open("player_scores.csv", "w", encoding="utf-8") as f:
    for pid, rating in player_ratings.items():
        f.write("{},{}\n".format(SteamID(pid).as_64, rating.mu))
