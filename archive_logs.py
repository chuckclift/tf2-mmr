#!/usr/bin/env python3

from urllib import request
from urllib.error import URLError
from pathlib import Path
from datetime import datetime, timedelta
import time
import json
import re
from steam.steamid import SteamID
import pickle

details_url = "https://logs.tf/json/"
SLEEP_TIME = 3
SEASON = datetime.now() - timedelta(days=60)

comp_maps = set()
with open("comp_maps.txt", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        comp_maps.add(line.strip())


def get_game_ids():
    id_url = "https://logs.tf/api/v1/log?limit=2000"
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
            usernames[int(steam_id)] = name


downloaded_games = set()
if not Path("game_logs.json").is_file():
    with open("game_logs.json", "w+") as f:
        print("created game_logs.json")
else:
    with open("game_logs.json", "r", encoding="utf-8") as f:
        for line in f:
            game = json.loads(line)
            game_id = ["id"]
            downloaded_games.add(game["id"])
            for steamid3, username in game["names"].items():
                stripped_username = " ".join(username.split())
                clean_username = stripped_username.replace("<", "").replace(">", "").replace(",", "")
                usernames[SteamID(steamid3).as_64] = clean_username


print("found", len(downloaded_games), "games in game_logs.json")
print("found", len(usernames), "users in game_logs.json")


for gid in get_game_ids():
    if gid in downloaded_games:
        print(gid, "already downloaded")
        continue
    request_url = details_url + str(gid)
    print(request_url)
    try:
        details_request = request.urlopen(request_url, timeout=10)
        game_details = json.loads(details_request.read().decode("utf-8"))
        del game_details["chat"]
        game_details["id"] = gid

        for steamid3, username in game_details["names"].items():
            stripped_username = " ".join(username.split())
            clean_username = stripped_username.replace("<", "").replace(">", "").replace(",", "")
            usernames[SteamID(steamid3).as_64] = clean_username

        with open("game_logs.json", "a", encoding="utf-8") as games_file:
            games_file.write(json.dumps(game_details) + "\n")

    except URLError as e:
        print(e)
        print("error processing", request_url, "sleeping 5 mins.")
        time.sleep(60 * 5)

    time.sleep(SLEEP_TIME)

with open("usernames.csv", "w") as f:
    for id64, name in usernames.items():
        f.write("{},{}\n".format(id64, name))
