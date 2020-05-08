#!/usr/bin/env python3
"""
This script generates user profile html pages from data in
the game_logs.json file.
"""

import json
import datetime
from typing import Dict
import html
from collections import namedtuple
from steam.steamid import SteamID  # type: ignore
from jinja2 import Template

player_mmr = {}  # type: Dict[int, float]
stats = {}  # type: Dict[str, Dict]
player_names = {}  # type: Dict[str, str]
teammate_counts = {}  # type: Dict[str, Dict[str, int]]
classnames = ["soldier", "sniper", "medic", "scout", "spy", "pyro",
              "engineer", "demoman", "heavyweapons"]


def safe_add(dct, key, value):
    """
    adds the given value to the key's value in the dictionary.
    If the key is not present in the dictionary, the value
    is set to the supplied value.
    """
    if key in dct:
        dct[key] += value

    else:
        dct[key] = value


with open("player_scores.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        id_field, mmr_field = line.split(",")
        player_mmr[int(id_field)] = float(mmr_field)

newest_log = None  # pylint: disable=C0103
oldest_log = None  # pylint: disable=C0103
games_played = 0  # pylint: disable=C0103

with open("game_logs.json") as game_logs:
    for line in game_logs:
        games_played += 1
        g = json.loads(line)  # json.loads(line)
        upload_date = datetime.datetime.fromtimestamp(g["info"]["date"])
        if not newest_log:
            newest_log = upload_date
        else:
            newest_log = max(newest_log, upload_date)

        if not oldest_log:
            oldest_log = upload_date
        else:
            oldest_log = min(oldest_log, upload_date)

        # getting usernames
        for id3, name in g["names"].items():
            player_names[id3] = html.escape(name)

        red = [id3 for id3, d in g["players"].items() if d["team"] == "Red"]
        blue = [id3 for id3, d in g["players"].items() if d["team"] == "Blue"]
        for id3 in red:
            if id3 not in teammate_counts:
                teammate_counts[id3] = {}

            for teammate_id3 in red:
                if teammate_id3 is id3:
                    continue

                if teammate_id3 not in teammate_counts[id3]:
                    teammate_counts[id3][teammate_id3] = 1
                else:
                    teammate_counts[id3][teammate_id3] += 1

        for id3 in blue:
            if id3 not in teammate_counts:
                teammate_counts[id3] = {}

            for teammate_id3 in blue:
                if teammate_id3 is id3:
                    continue

                if teammate_id3 not in teammate_counts[id3]:
                    teammate_counts[id3][teammate_id3] = 1
                else:
                    teammate_counts[id3][teammate_id3] += 1

        game_time = g["info"]["total_length"]

        for id3, d in g["players"].items():
            if id3 not in stats:
                stats[id3] = {}

            for c in d["class_stats"]:
                if c["type"] not in stats[id3]:
                    stats[id3][c["type"]] = {}

                safe_add(stats[id3][c["type"]], "kills", c["kills"])
                safe_add(stats[id3][c["type"]], "assists", c["assists"])
                safe_add(stats[id3][c["type"]], "deaths", c["deaths"])
                safe_add(stats[id3][c["type"]], "dmg", c["dmg"])
                safe_add(stats[id3][c["type"]], "total_time", c["total_time"])

                estimated_heal = d["heal"] * c["total_time"] / game_time
                safe_add(stats[id3][c["type"]], "heal", estimated_heal)

                estimated_dt = d["dt"] * c["total_time"] / game_time
                safe_add(stats[id3][c["type"]], "dt", estimated_dt)

                if c["type"] == "medic":
                    safe_add(stats[id3]["medic"], "drops", d["drops"])
                    safe_add(stats[id3]["medic"], "ubers", d["ubers"])
                elif c["type"] == "sniper":
                    safe_add(stats[id3]["sniper"],
                             "headshots_hit", d["headshots_hit"])
                elif c["type"] == "spy":
                    safe_add(stats[id3]["spy"], "backstabs", d["backstabs"])


search_dict = {n: SteamID(i).as_64 for i, n
               in player_names.items()}  # type: Dict[str, int]

with open("html/usernames.js", "w", encoding="utf-8") as usernames_file:
    usernames_file.write("var usernames = " + json.dumps(search_dict) + ";")


with open("profile.html", encoding="utf-8") as template_file:
    profile_template = Template(template_file.read())


class_stat = namedtuple("class_stat", "name kpm depm kapd dpm dtpm ds hrs")

for id3, s in stats.items():
    mmr = player_mmr.get(id3, float("nan"))
    top_teammates = sorted([(teammate_counts[id3][a], a)
                            for a in teammate_counts[id3]], reverse=True)[:3]
    teammate_names = [(html.escape(player_names[tid3]), SteamID(
        tid3).as_64) for _, tid3 in top_teammates]
    player_class_stats = []
    for classname, class_stats in sorted(s.items(), key=lambda x: x[1]["total_time"], reverse=True):
        M = class_stats["total_time"] / 60
        if M < 2:
            continue
        if classname not in classnames:
            continue
        kpm = class_stats["kills"] / M
        depm = class_stats["deaths"] / M

        kapd = float("nan")
        if class_stats["deaths"] > 0:
            kapd = ((class_stats["kills"] + class_stats["assists"]) /
                    class_stats["deaths"])
        dpm = class_stats["dmg"] / M
        dtpm = class_stats["dt"] / M
        ds = dpm - dtpm
        hrs = M / 60
        player_class_stats.append(class_stat(
            classname, kpm, depm, kapd, dpm, dtpm, ds, hrs))
    with open("html/players/{}.html".format(SteamID(id3).as_64), "w", encoding="utf-8") as html_profile:
        html_profile.write(profile_template.render(username=html.escape(player_names[id3]),
                                                   mmr=mmr,
                                                   classstats=player_class_stats,
                                                   teammates=teammate_names,
                                                   games=games_played,
                                                   players=len(player_mmr),
                                                   oldest=oldest_log,
                                                   newest=newest_log))
