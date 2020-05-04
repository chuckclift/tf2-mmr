#!/usr/bin/env python3

import json
from steam.steamid import SteamID
from pprint import pprint
from typing import Dict

player_stats = {} # type: Dict[int, Dict]
player_names = {} # type: Dict[int, str]
fields = ["assists", "deaths", "dmg", "drops", "dt", "heal", "kills"]

with open("game_logs.json") as game_logs:
    for line in game_logs:
        g = json.loads(line)

        for id3, name in g["names"].items():
            id64 = SteamID(id3).as_64
            normalized_name = " ".join( name.split())
            cleaned_name = normalized_name.replace("<", "&lt;").replace(">", "&gt;")
            player_names[id64] = cleaned_name

        game_time = g["info"]["total_length"]
        rounds = len(g["rounds"])
        # print(game_time / 60, "minutes long", rounds, "rounds played")
        for id3, d in g["players"].items():
            id64 = SteamID(id3).as_64
            if id64 not in player_stats:
                player_stats[id64] = {f:0 for f in fields}
                player_stats[id64]["rounds"] = 0
                player_stats[id64]["time"] = 0

            for f in fields:
                player_stats[id64][f] += d[f]
            player_stats[id64]["rounds"] += rounds
            player_stats[id64]["time"] += game_time



print("<html><head><title>Player Stats</title></head>")
print("<body style='background-color:#4d4d4d;'>")

for id64, stats in player_stats.items():
    minutes = stats["time"] / 60
    print("<div style='background-color:white; margin:20px; padding:10px; width: 80%;'>")
    print("<h1>", player_names[id64], id64, "</h1>")

    if stats["deaths"] == 0:
        print("<p>KA/D : No deaths. God tier player  </p>")
    else: 
        kills_assists_per_death = round( (stats["kills"] + stats["assists"]) / stats["deaths"], 2)
        print("<p>KA/D :", kills_assists_per_death , "</p>")


    dpm = round(stats["dmg"] / minutes,2)
    print("<p>DA/M :", dpm, "</p>")

    dtpm = round(stats["dt"] / minutes, 2)
    print("<p>DT/M :", dtpm, "</p>")
    print("<p>(DA/M) - (DT/M) :", round(dpm - dtpm, 2), "</p>")
    print("<p>Kills / M : ", round(stats["kills"] / minutes, 2), "</p>")
    print("<p>Heal / M : ", round(stats["heal"] / minutes, 2), "</p>")
    print("<p>Drops / M : ", round(stats["drops"] / minutes, 2), "</p>")




    print("</div>")

print("</body")
