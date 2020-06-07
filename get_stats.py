#!/usr/bin/env python3
"""
This script generates user profile html pages from data in
the game_logs.json file.
"""

import json
import copy
import datetime
import itertools
from typing import Dict, Tuple, Optional, Any, Union, List, NamedTuple
from collections import namedtuple
from steam.steamid import SteamID  # type: ignore
import jinja2
import link_match_logs

player_mmr = {}  # type: Dict[int, float]
stats = {}  # type: Dict[str, Dict[str, Any]]
player_names = {}  # type: Dict[str, str]
teammate_counts = {}  # type: Dict[str, Dict[str, int]]
classnames = ["soldier", "sniper", "medic", "scout", "spy", "pyro",
              "engineer", "demoman", "heavyweapons"]
base_stats = ["kills", "assists", "deaths", "dmg", "dt", "total_time", "heal"]

StatVal = Union[int, float, List]

base_player = {cname: {k: 0 for k in base_stats} for cname in classnames}  # type: Dict[str, Dict[str, StatVal]]
for cnm in classnames:
    base_player[cnm]["game_dpm"] = []
base_player["medic"]["drops"] = 0
base_player["medic"]["ubers"] = 0
base_player["medic"]["mid_escapes"] = 0
base_player["medic"]["mid_deaths"] = 0
base_player["sniper"]["headshots_hit"] = 0
base_player["spy"]["backstabs"] = 0

MatchLogCombo = NamedTuple("MatchLogCombo", [("logs_tf_id", int),
                                             ("rgl_id", int)])

player_matches = {}  # type: Dict[str, List[Tuple[int, int]]]
log_matches = {logstf: rglmatch for rglmatch, logstf in
               link_match_logs.read_rgl_match_logs()}  # type: Dict[int, int]


def count_teammates(gamelog):
    """
    updates the number of times played with other players
    """
    for user1_id3, user2_id3 in itertools.combinations(gamelog["players"], 2):
        if user1_id3 not in teammate_counts:
            teammate_counts[user1_id3] = {}
        if user2_id3 not in teammate_counts:
            teammate_counts[user2_id3] = {}

        same_team = (gamelog["players"][user1_id3]["team"] ==
                     gamelog["players"][user2_id3]["team"])

        if not same_team:
            continue

        games_together = teammate_counts[user1_id3].get(user2_id3, 0) + 1
        teammate_counts[user1_id3][user2_id3] = games_together
        teammate_counts[user2_id3][user1_id3] = games_together


def get_midfight_survival(gamelog, med_id3):  # type: (Dict, str) -> Optional[Tuple]
    """
    gets the midfight survivals and the midfight deaths from a gamelog for a 
    medic player.  If the map isn't a koth or control points map, it returns
    None because other map types like payload do not have midfights.
    """
    game_map = gamelog["info"]["map"]
    if not game_map.startswith("koth_") and not game_map.startswith("cp_"):
        return None
    midfight_deaths = 0  # type: int
    midfight_escapes = 0  # type: int
    for r in gamelog["rounds"]:
        med_round = any([a for a in r["events"]
                         if a["type"] in {"medic_death", "charge"}
                         and a["steamid"] == med_id3])
        if not med_round:
            continue

        events = [a for a in r["events"] if a["type"] == "pointcap" or
                  (a["type"] == "medic_death" and a["steamid"] == med_id3)]
        if not events:
            # the game ended before pointcap
            midfight_escapes += 1
        elif events[0]["type"] == "pointcap":
            midfight_escapes += 1
        else:
            midfight_deaths += 1
    return (midfight_escapes, midfight_deaths)


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
        if newest_log:
            newest_log = max(newest_log, upload_date)
        else:
            newest_log = upload_date

        if oldest_log:
            oldest_log = min(oldest_log, upload_date)
        else:
            oldest_log = upload_date

        # getting usernames
        for id3, name in g["names"].items():
            player_names[id3] = name

            if g["id"] in log_matches:
                if id3 not in player_matches:
                    player_matches[id3] = []
                player_matches[id3].append(MatchLogCombo(g["id"], log_matches[g["id"]]))

        count_teammates(g)
        game_time = g["info"]["total_length"]

        for id3, d in g["players"].items():
            if id3 not in stats:
                stats[id3] = copy.deepcopy(base_player)

            for c in d["class_stats"]:
                if c["type"] == "medic":
                    stats[id3]["medic"]["drops"] += d["drops"]
                    if "medigun" in d["ubertypes"]:
                        stats[id3]["medic"]["ubers"] += d["ubertypes"]["medigun"]

                    mfs = get_midfight_survival(g, id3)
                    if mfs:
                        mid_escapes, mid_deaths = mfs
                        stats[id3]["medic"]["mid_escapes"] += mid_escapes
                        stats[id3]["medic"]["mid_deaths"] += mid_deaths
                elif c["type"] == "sniper":
                    stats[id3]["sniper"]["headshots_hit"] += d["headshots_hit"]
                elif c["type"] == "spy":
                    stats[id3]["spy"]["backstabs"] += d["backstabs"]
                elif c["type"] not in classnames:
                    continue

                stats[id3][c["type"]]["kills"] += c["kills"]
                stats[id3][c["type"]]["assists"] += c["assists"]
                stats[id3][c["type"]]["deaths"] += c["deaths"]
                stats[id3][c["type"]]["dmg"] += c["dmg"]
                stats[id3][c["type"]]["total_time"] += c["total_time"]
                if c["total_time"]:
                    stats[id3][c["type"]]["game_dpm"].append(c["dmg"] / c["total_time"])

                estimated_heal = d["heal"] * c["total_time"] / game_time
                stats[id3][c["type"]]["heal"] += estimated_heal

                estimated_dt = d["dt"] * c["total_time"] / game_time
                stats[id3][c["type"]]["dt"] += estimated_dt


search_dict = {n: str(SteamID(i).as_64) for i, n
               in player_names.items()}  # type: Dict[str, str]

with open("html/usernames.js", "w", encoding="utf-8") as usernames_file:
    usernames_file.write("var usernames = " + json.dumps(search_dict) + ";")

with open("html/usernames.json", "w", encoding="utf-8") as usernames_json:
    usernames_json.write(json.dumps(search_dict))

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                               autoescape=True)
profile_template = jinja_env.get_template("profile.html")
class_stat = namedtuple("class_stat", "name kpm depm kapd dpm dtpm ds hrs")


for id3, s in stats.items():
    mmr = player_mmr.get(SteamID(id3).as_64, float("nan"))
    sorted_teammates = sorted([(teammate_counts[id3][a], a)
                               for a in teammate_counts[id3]], reverse=True)
    top_teammates = sorted_teammates if len(
        sorted_teammates) < 10 else sorted_teammates[:10]
    teammate_names = [(player_names[tid3], SteamID(tid3).as_64)
                      for _, tid3 in top_teammates]

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

    advanced_stats = []
    if "medic" in s and s["medic"]["total_time"] > 2 * 60:
        M = s["medic"]["total_time"] / 60
        advanced_stats.append(("drops / M", s["medic"]["drops"] / M))
        advanced_stats.append(("ubers / M", s["medic"]["ubers"] / M))

        drops_to_ubers = (float("nan") if s["medic"]["drops"] == 0
                          else s["medic"]["ubers"] / s["medic"]["drops"])
        advanced_stats.append(("ubers / drops", drops_to_ubers))

        if s["medic"]["mid_escapes"] or s["medic"]["mid_deaths"]:
            midfights = s["medic"]["mid_escapes"] + s["medic"]["mid_deaths"]
            survival_pct = 100 * s["medic"]["mid_escapes"] / midfights
            advanced_stats.append(("Midfight Survival %", survival_pct))

    if "sniper" in s and s["sniper"]["total_time"] > 2 * 60:
        M = s["sniper"]["total_time"] / 60
        advanced_stats.append(
            ("headshots / M", s["sniper"]["headshots_hit"] / M))

    if "spy" in s and s["spy"]["total_time"] > 2 * 60:
        M = s["spy"]["total_time"] / 60
        advanced_stats.append(("backstabs / M", s["spy"]["backstabs"] / M))

    profile_filename = "html/players/{}.html".format(SteamID(id3).as_64)
    with open(profile_filename, "w", encoding="utf-8") as html_profile:
        player_rgl_matches = []
        if id3 in player_matches:
            player_rgl_matches = player_matches[id3]
        html_profile.write(profile_template.render(username=player_names[id3],
                                                   mmr=mmr,
                                                   classstats=player_class_stats,
                                                   advanced_stats=advanced_stats,
                                                   teammates=teammate_names,
                                                   games=games_played,
                                                   players=len(player_mmr),
                                                   rgl_matches=player_rgl_matches,
                                                   oldest=oldest_log,
                                                   newest=newest_log))
