#!/usr/bin/env python3

import json
import trueskill
from steam.steamid import SteamID


player_ratings = {}
log_index = []


with open("game_logs.json", encoding="utf-8") as f:
    start = 0
    while True:
        gdata = f.readline()

        # if the end of file has been reached, an empty string is returned
        if gdata == "":
            break

        game_data = json.loads(gdata)
        log_index.append((game_data["info"]["date"], start))
        start = f.tell()

    log_index.sort()


def get_games():
    with open("game_logs.json", encoding="utf-8") as f:
        for _, l in log_index:
            f.seek(l)
            yield json.loads(f.readline())


for game in get_games():
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

    if len(red_ratings) == 0 or len(blue_ratings) == 0:
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
