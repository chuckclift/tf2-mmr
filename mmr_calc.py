#!/usr/bin/env python3

import trueskill
import json
from steam.steamid import SteamID

games = []
player_ratings = {}

with open("game_logs.json") as f:
    games = [json.loads(line) for line in f]
    games.sort(key=lambda g: g["info"]["date"])

for game in games:
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



