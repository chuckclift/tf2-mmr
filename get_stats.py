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
import get_rgl_matches
from parse_logs import get_midfight_survival

player_mmr = {}  # type: Dict[int, float]
stats = {}  # type: Dict[str, Dict[str, Any]]
player_names = {}  # type: Dict[str, str]
teammate_counts = {}  # type: Dict[str, Dict[str, int]]
classnames = [
    "soldier",
    "sniper",
    "medic",
    "scout",
    "spy",
    "pyro",
    "engineer",
    "demoman",
    "heavyweapons",
]
base_stats = [
    "wins",
    "losses",
    "draws",
    "kills",
    "assists",
    "deaths",
    "dmg",
    "dt",
    "total_time",
    "heal",
]

StatVal = Union[int, float, List]

base_player = {cname: {k: 0
                       for k in base_stats}
               for cname in classnames}  # type: Dict[str, Dict[str, StatVal]]
for cnm in classnames:
    base_player[cnm]["game_dpm"] = []
base_player["medic"]["drops"] = 0
base_player["medic"]["ubers"] = 0
base_player["medic"]["mid_escapes"] = 0
base_player["medic"]["mid_deaths"] = 0
base_player["sniper"]["headshots_hit"] = 0
base_player["sniper"]["sniper_kills"] = 0
base_player["sniper"]["deaths_to_sniper"] = 0
base_player["spy"]["backstabs"] = 0

MatchLogCombo = NamedTuple(
    "MatchLogCombo",
    [
        ("logs_tf_id", int),
        ("rgl_id", int),
        ("map", str),
        ("season", str),
        ("win", bool),
    ],
)

player_matches = {}  # type: Dict[str, List[MatchLogCombo]]
logs_tf_to_rgl = {
    logstf: rglmatch
    for rglmatch, logstf in link_match_logs.read_rgl_match_logs()
}  # type: Dict[int, int]

# matches rgl match id to the rgl season id
rgl_match_seasons = {}  # type: Dict[int, int]
for m in get_rgl_matches.read_matches():
    if m.season:
        rgl_match_seasons[m.id] = m.season

rgl_seasons = {}  # type: Dict[int,str]
with open("rgl_seasons.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        sid, sname = line.split(",")
        rgl_seasons[int(sid)] = sname.strip()


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

        if same_team:
            games_together = teammate_counts[user1_id3].get(user2_id3, 0) + 1
            teammate_counts[user1_id3][user2_id3] = games_together
            teammate_counts[user2_id3][user1_id3] = games_together


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

        if g["teams"]["Red"]["score"] == g["teams"]["Blue"]["score"]:
            match_draw = True
        elif g["teams"]["Red"]["score"] > g["teams"]["Blue"]["score"]:
            match_winner = "Red"
        elif g["teams"]["Red"]["score"] < g["teams"]["Blue"]["score"]:
            match_winner = "Blue"

        for id3, name in g["names"].items():
            # getting usernames
            player_names[id3] = name

            # updating rgl match info
            if g["id"] in logs_tf_to_rgl:
                if id3 not in player_matches:
                    player_matches[id3] = []
                rgl_match_id = logs_tf_to_rgl[g["id"]]
                rgl_season_id = rgl_match_seasons[rgl_match_id]

                player_team = g["players"][id3]["team"]
                enemy_team = "Red" if player_team == "Blue" else "Blue"
                match_win = (g["teams"][player_team]["score"] >
                             g["teams"][enemy_team]["score"])

                player_matches[id3].append(
                    MatchLogCombo(
                        g["id"],
                        rgl_match_id,
                        g["info"]["map"],
                        rgl_seasons[rgl_season_id],
                        match_win,
                    ))

        count_teammates(g)
        game_time = g["info"]["total_length"]

        for id3, d in g["players"].items():
            if id3 not in stats:
                stats[id3] = copy.deepcopy(base_player)

            for c in d["class_stats"]:
                if c["type"] == "medic":
                    stats[id3]["medic"]["drops"] += d["drops"]
                    if "medigun" in d["ubertypes"]:
                        stats[id3]["medic"]["ubers"] += d["ubertypes"][
                            "medigun"]

                    mfs = get_midfight_survival(g, id3)
                    if mfs:
                        mid_escapes, mid_deaths = mfs
                        stats[id3]["medic"]["mid_escapes"] += mid_escapes
                        stats[id3]["medic"]["mid_deaths"] += mid_deaths
                elif c["type"] == "sniper":
                    stats[id3]["sniper"]["headshots_hit"] += d["headshots_hit"]

                    # these stats are used for killing sniper vs sniper k/d ratio
                    sniper_kills = g["classkills"].get(id3,
                                                       {}).get("sniper", 0)
                    deaths_to_sniper = g["classdeaths"].get(id3, {}).get(
                        "sniper", 0)
                    stats[id3]["sniper"]["sniper_kills"] += sniper_kills
                    stats[id3]["sniper"][
                        "deaths_to_sniper"] += deaths_to_sniper
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
                    stats[id3][c["type"]]["game_dpm"].append(c["dmg"] /
                                                             c["total_time"])

                estimated_heal = d["heal"] * c["total_time"] / game_time
                stats[id3][c["type"]]["heal"] += estimated_heal

                estimated_dt = d["dt"] * c["total_time"] / game_time
                stats[id3][c["type"]]["dt"] += estimated_dt

search_dict = {n: str(SteamID(i).as_64)
               for i, n in player_names.items()}  # type: Dict[str, str]

with open("html/usernames.json", "w", encoding="utf-8") as usernames_json:
    usernames_json.write(json.dumps(search_dict))

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                               autoescape=True)
profile_template = jinja_env.get_template("profile.html")
class_stat = namedtuple("class_stat", "name kpm depm kapd dpm dtpm ds hrs")

for id3, s in stats.items():
    mmr = player_mmr.get(SteamID(id3).as_64, float("nan"))
    sorted_teammates = sorted([(teammate_counts[id3][a], a)
                               for a in teammate_counts[id3]],
                              reverse=True)
    top_teammates = (sorted_teammates
                     if len(sorted_teammates) < 10 else sorted_teammates[:10])
    teammate_names = [(player_names[tid3], SteamID(tid3).as_64)
                      for _, tid3 in top_teammates]

    total_kills = sum([a["kills"] for _, a in s.items()])
    total_dmg = sum([a["dmg"] for _, a in s.items()])
    total_dt = sum([a["dt"] for _, a in s.items()])
    total_ubers = s.get("medic", {}).get("ubers", 0)
    lifetime_stats = [("Total Kills", total_kills),
                      ("Total Damage", total_dmg),
                      ("Total Damage Taken", total_dt),
                      ("Total Ubers", total_ubers)]

    player_class_stats = []
    for classname, class_stats in sorted(s.items(),
                                         key=lambda x: x[1]["total_time"],
                                         reverse=True):
        M = class_stats["total_time"] / 60
        if M < 2:
            continue
        if classname not in classnames:
            continue
        kpm = class_stats["kills"] / M
        depm = class_stats["deaths"] / M

        kapd = float("nan")
        if class_stats["deaths"] > 0:
            kapd = (class_stats["kills"] +
                    class_stats["assists"]) / class_stats["deaths"]
        dpm = class_stats["dmg"] / M
        dtpm = class_stats["dt"] / M
        ds = dpm - dtpm
        hrs = M / 60
        player_class_stats.append(
            class_stat(classname, kpm, depm, kapd, dpm, dtpm, ds, hrs))

    advanced_stats = []
    if "medic" in s and s["medic"]["total_time"] > 2 * 60:
        M = s["medic"]["total_time"] / 60
        total_ubers += s["medic"]["ubers"]
        advanced_stats.append(("drops / M", s["medic"]["drops"] / M))
        advanced_stats.append(("ubers / M", s["medic"]["ubers"] / M))

        drops_to_ubers = (float("nan") if s["medic"]["drops"] == 0 else
                          s["medic"]["ubers"] / s["medic"]["drops"])
        advanced_stats.append(("ubers / drops", drops_to_ubers))

        if s["medic"]["mid_escapes"] or s["medic"]["mid_deaths"]:
            midfights = s["medic"]["mid_escapes"] + s["medic"]["mid_deaths"]
            survival_pct = 100 * s["medic"]["mid_escapes"] / midfights
            advanced_stats.append(("Midfight Survival %", survival_pct))

    if "sniper" in s and s["sniper"]["total_time"] > 2 * 60:
        M = s["sniper"]["total_time"] / 60
        advanced_stats.append(
            ("headshots / M", s["sniper"]["headshots_hit"] / M))

        if s["sniper"]["deaths_to_sniper"] == 0:
            svs = float("nan")
        else:
            svs = s["sniper"]["sniper_kills"] / s["sniper"]["deaths_to_sniper"]
        advanced_stats.append(("SvS", svs))

    if "spy" in s and s["spy"]["total_time"] > 2 * 60:
        M = s["spy"]["total_time"] / 60
        advanced_stats.append(("backstabs / M", s["spy"]["backstabs"] / M))

    profile_filename = "html/players/{}.html".format(SteamID(id3).as_64)
    with open(profile_filename, "w", encoding="utf-8") as html_profile:
        player_rgl_matches = player_matches.get(id3, [])
        html_profile.write(
            profile_template.render(username=player_names[id3],
                                    mmr=mmr,
                                    classstats=player_class_stats,
                                    advanced_stats=advanced_stats,
                                    teammates=teammate_names,
                                    games=games_played,
                                    players=len(player_mmr),
                                    rgl_matches=sorted(player_rgl_matches,
                                                       reverse=True),
                                    oldest=oldest_log,
                                    newest=newest_log,
                                    lifetime_stats=lifetime_stats))
