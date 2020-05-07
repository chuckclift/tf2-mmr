#!/usr/bin/env python3
"""
This script downloads the most recent game logs from logs.tf and stores them
in game_logs.json.  It avoids archiving "casual" maps, only downloading
logs for competive maps.
"""

from urllib import request
from urllib.error import URLError
from pathlib import Path
from datetime import datetime, timedelta
import time
import json
import html
from typing import Set
from steam.steamid import SteamID # type: ignore

SLEEP_TIME = 3
SEASON = datetime.now() - timedelta(days=60)

comp_maps = set()
with open("comp_maps.txt", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        comp_maps.add(line.strip())


def get_game_ids():
    """
    lazily yields game ids of the most recent logs.tf games.
    This function filters out games with casual maps, using
    a competitive map whitelist.
    """
    id_url = "https://logs.tf/api/v1/log?limit=2000"
    try:
        id_request = request.urlopen(id_url, timeout=10)
        game_search = json.loads(id_request.read().decode("utf-8"))
        for game_log in game_search["logs"]:
            if game_log["map"] in comp_maps and game_log["date"] >= SEASON.timestamp():
                yield game_log["id"]
        time.sleep(SLEEP_TIME)
    except URLError as e:
        print(e)
        print("error processing", id_url, "sleeping 5 mins.")
        time.sleep(60 * 5)


usernames = {}
if not Path("usernames.csv").is_file():
    with open("usernames.csv", "w+") as f:
        print("created usernames.csv")
else:
    with open("usernames.csv", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            steam_id, name = line.split(",")
            usernames[int(steam_id)] = html.escape(name)


downloaded_games = set()  # type: Set[int]
if not Path("game_logs.json").is_file():
    with open("game_logs.json", "w+") as f:
        print("created game_logs.json")
else:
    with open("game_logs.json", "r", encoding="utf-8") as f:
        for line in f:
            game = json.loads(line)
            downloaded_games.add(game["id"])
            for steamid3, username in game["names"].items():
                usernames[SteamID(steamid3).as_64] = html.escape(username)

print("found", len(downloaded_games), "games in game_logs.json")
print("found", len(usernames), "users in game_logs.json")


for gid in get_game_ids():
    if gid in downloaded_games:
        print(gid, "already downloaded")
        continue

    print("https://logs.tf/json/" + str(gid))
    try:
        details_request = request.urlopen(
            "https://logs.tf/json/" + str(gid), timeout=10)
        game_details = json.loads(details_request.read().decode("utf-8"))
        del game_details["chat"]
        game_details["id"] = gid

        for steamid3, username in game_details["names"].items():
            usernames[SteamID(steamid3).as_64] = " ".join(
                username.split()).replace("<", "").replace(">", "").replace(",", "")

        with open("game_logs.json", "a", encoding="utf-8") as games_file:
            games_file.write(json.dumps(game_details) + "\n")

    except URLError as e:
        print(e)
        print("error processing https://logs.tf/json/{} sleeping 5 mins.".format(gid))
        time.sleep(60 * 5)

    time.sleep(SLEEP_TIME)

with open("usernames.csv", "w") as f:
    for id64, name in usernames.items():
        f.write("{},{}\n".format(id64, name))
