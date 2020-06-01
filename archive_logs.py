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
from typing import Set

SLEEP_TIME = 3
SEASON = datetime.now() - timedelta(days=60)


def is_compmap(name):
    """
    Tf2 maps have prefixes which tell the map types.  Control points (cp_),
    payload (pl), and king of the hill (koth_), are the only map types
    played competitively.
    """
    return name.startswith("cp_") or name.startswith("pl_") or name.startswith("koth_")


def get_game_ids():
    """
    lazily yields game ids of the most recent logs.tf games.
    This function filters out games with casual maps, using
    a competitive map whitelist.
    """
    id_url = "https://logs.tf/api/v1/log?limit=9000"
    try:
        id_request = request.urlopen(id_url, timeout=10)
        game_search = json.loads(id_request.read().decode("utf-8"))
        for game_log in game_search["logs"]:
            if is_compmap(game_log["map"]) and game_log["date"] >= SEASON.timestamp():
                yield game_log["id"]
        time.sleep(SLEEP_TIME)
    except URLError as e:
        print(e)
        print("error processing", id_url, "sleeping 5 mins.")
        time.sleep(60 * 5)


downloaded_games = set()  # type: Set[int]
if not Path("game_logs.json").is_file():
    with open("game_logs.json", "w+") as f:
        print("created game_logs.json")
else:
    with open("game_logs.json", "r", encoding="utf-8") as f:
        for line in f:
            game = json.loads(line)
            downloaded_games.add(game["id"])

print("found", len(downloaded_games), "games in game_logs.json")


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

        with open("game_logs.json", "a", encoding="utf-8") as games_file:
            games_file.write(json.dumps(game_details) + "\n")

    except URLError as e:
        print(e)
        print("error processing https://logs.tf/json/{} sleeping 5 mins.".format(gid))
        time.sleep(60 * 5)

    time.sleep(SLEEP_TIME)
