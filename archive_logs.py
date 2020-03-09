#!/usr/bin/env python3

from urllib import request
from urllib.error import URLError 
from pathlib import Path
from datetime import datetime, timedelta
import time
import json
import re
from steam.steamid import SteamID

details_url = "http://logs.tf/json/"
SLEEP_TIME = 10
SEASON = datetime.now() - timedelta(days=60)

comp_maps = set()
with open("comp_maps.txt", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        comp_maps.add(line.strip())

player_ids = set()
with open("player_links.txt") as f:
    for line in f:
        m = re.search(r"\d{10,}", line)
        player_ids.add(int(m.group(0)))


player_count = {}
with open("game_logs.json", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        for player in d["players"]:
            id64 = SteamID(player).as_64
            if id64 not in player_ids:
                pass
            elif id64 in player_count:
                player_count[id64] += 1
            else:
                player_count[id64] = 1

# the list is sorted so players with fewer games are searched for first.
# That way, the get_game_ids function looks for their games first.
players = sorted([(count, player) for player, count in player_count.items()])
sorted_ids = [pid64 for _, pid64 in players]


def get_game_ids():
    for i, pid in enumerate(sorted_ids):
        id_url = "http://logs.tf/api/v1/log?limit=200&player=" + str(pid)
        print(i, "/", len(player_ids), "getting game ids from", id_url)
        try:
            id_request = request.urlopen(id_url, timeout=10)
            game_search = json.loads(id_request.read().decode("utf-8"))
            for game in game_search["logs"]:
                if game["map"] in comp_maps and game["date"] >= SEASON.timestamp():
                    yield game["id"]
            time.sleep(SLEEP_TIME)
        except URLError as e:
            print(e)
            print("error processing", id_url, "sleeping 5 mins.")
            time.sleep(60 * 5)


downloaded_games = set()
if not Path("game_logs.json").is_file():
    with open("game_logs.json", "w+") as f:
        print("created game_logs.json")
else:
    with open("game_logs.json", "r", encoding="utf-8") as f:
        for line in f:
            game_id = json.loads(line)["id"]
            downloaded_games.add(game_id)
        print("found", len(downloaded_games), "in game_logs.json")

for gid in get_game_ids():
    if gid in downloaded_games:
        print(gid, "already downloaded")
        continue
    request_url = details_url + str(gid)
    print( request_url)
    try:
        details_request = request.urlopen(request_url, timeout=10)
        game_details = json.loads(details_request.read().decode("utf-8"))
        del game_details["chat"]
        game_details["id"] = gid
        with open("game_logs.json", "a", encoding="utf-8") as games_file:
            games_file.write(json.dumps(game_details) + "\n")

    except URLError as e:
        print(e)
        print("error processing", request_url, "sleeping 5 mins.")
        time.sleep(60 * 5)

    time.sleep(SLEEP_TIME)
