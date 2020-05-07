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
stats = {}  # type: Dict[int, Dict]
player_names = {}  # type: Dict[int, str]
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
        g = json.loads(line)
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
            player_names[SteamID(id3).as_64] = html.escape(name)

        game_time = g["info"]["total_length"]

        for id3, d in g["players"].items():
            id64 = SteamID(id3).as_64  # pylint: disable=C0103
            if id64 not in stats:
                stats[id64] = {}

            for c in d["class_stats"]:
                if c["type"] not in stats[id64]:
                    stats[id64][c["type"]] = {}

                safe_add(stats[id64][c["type"]], "kills", c["kills"])
                safe_add(stats[id64][c["type"]], "assists", c["assists"])
                safe_add(stats[id64][c["type"]], "deaths", c["deaths"])
                safe_add(stats[id64][c["type"]], "dmg", c["dmg"])
                safe_add(stats[id64][c["type"]], "total_time", c["total_time"])

                estimated_heal = d["heal"] * c["total_time"] / game_time
                safe_add(stats[id64][c["type"]], "heal", estimated_heal)

                estimated_dt = d["dt"] * c["total_time"] / game_time
                safe_add(stats[id64][c["type"]], "dt", estimated_dt)

                if c["type"] == "medic":
                    safe_add(stats[id64]["medic"], "drops", d["drops"])
                    safe_add(stats[id64]["medic"], "ubers", d["ubers"])
                elif c["type"] == "sniper":
                    safe_add(stats[id64]["sniper"],
                             "headshots_hit", d["headshots_hit"])
                elif c["type"] == "spy":
                    safe_add(stats[id64]["spy"], "backstabs", d["backstabs"])


search_dict = {n: i for i, n in player_names.items()}
with open("html/usernames.js", "w", encoding="utf-8") as usernames_file:
    usernames_file.write("var usernames = " + json.dumps(search_dict) + ";")


with open("profile.html", encoding="utf-8") as template_file:
    profile_template = Template(template_file.read())


class_stat = namedtuple("class_stat", "name kpm depm kapd dpm dtpm ds hrs")

for id64, s in stats.items():
    mmr = player_mmr.get(id64, float("nan"))
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
    with open("html/players/{}.html".format(id64), "w", encoding="utf-8") as html_profile:
        html_profile.write(profile_template.render(username=player_names[id64],
                                                   mmr=mmr,
                                                   classstats=player_class_stats,
                                                   games=games_played,
                                                   players=len(player_mmr),
                                                   oldest=oldest_log,
                                                   newest=newest_log))
