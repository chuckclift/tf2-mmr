#!/usr/bin/env python3

from urllib import request
from urllib.error import URLError 
from pathlib import Path
from datetime import datetime, timedelta
import itertools
import time
import json
import re
import random

details_url = "http://logs.tf/json/"
SLEEP_TIME = 10
SEASON = datetime.now() - timedelta(days=30)
COMP_MAPS = {"cp_snakewater_final1", "pl_upward", "pl_vigil_rc7", 
             "cp_metalworks", "cp_sunshine", "koth_ashville_rc1_nb2", 
             "cp_process_final", "th_ashville_rc1_nb2", 
             "koth_ashville_rc1_nb4", "koth_product_rcx", 
             "cp_gullywash_final1", "pl_borneo", "koth_clearcut_b14c"}

player_ids = set()
with open("player_links.txt") as f:
    for line in f:
        m = re.search(r"\d{10,}", line)
        player_ids.add(int(m.group(0)))

shuffled_ids = list(player_ids)
random.shuffle(shuffled_ids)
        

def get_game_ids():
    for i, pid in enumerate(shuffled_ids):
        id_url = "http://logs.tf/api/v1/log?limit=50&player=" + str(pid)
        print(i, "/", len(player_ids), "getting game ids from", id_url)
        try:
            id_request = request.urlopen(id_url, timeout=10)
            game_search = json.loads(id_request.read().decode("utf-8"))
            for game in game_search["logs"]:
                if game["map"] in COMP_MAPS and game["date"] >= SEASON.timestamp():
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
