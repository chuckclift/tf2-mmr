#!/usr/bin/env python3

from enum import Enum
from typing import Dict, Set, List, Tuple
from datetime import datetime, date, timedelta
import get_rgl_matches
from get_rgl_matches import RglMatch
from mmr_calc import get_sorted_games
from steam.steamid import SteamID  # type: ignore

DAY = timedelta(days=1)


class Tf2Format(Enum):
    fours = 1
    sixes = 2
    prolander = 3
    highlander = 4


def read_region_formats():  # type: () -> Dict[int, Tf2Format]
    region_formats = {}
    with open("region_format.csv", encoding="utf-8") as f:
        for line in f:
            rid, formatid, _ = line.split(",")
            region_formats[int(rid)] = Tf2Format(int(formatid))
    return region_formats


def read_rgl_match_logs():  # type: () -> List[Tuple[int, int]]
    values = []
    with open("rgl_match_logs.csv", encoding="utf-8") as rml:
        for line in rml:
            if not line:
                continue
            rgl_id, log_id = line.split(",")
            values.append((int(rgl_id), int(log_id)))
    return values


def get_format(gamelog):  # type: (Dict) -> Tf2Format
    game_seconds = gamelog["length"]
    gamer_seconds = 0
    for _, player in gamelog["players"].items():
        for c in player["class_stats"]:
            gamer_seconds += c["total_time"]

    gamers_per_second = gamer_seconds / game_seconds
    if gamers_per_second < 10:
        return Tf2Format.fours
    elif gamers_per_second < 12.2:
        return Tf2Format.sixes
    elif gamers_per_second < 14.2:
        return Tf2Format.prolander
    else:
        return Tf2Format.highlander


matches = {}  # type: Dict[int, RglMatch]
format_matches = {i: set() for i in Tf2Format}  # type: Dict[Tf2Format, Set[int]]
match_dates = {}  # type: Dict[date, Set[int]]
possible_logs = {}  # type: Dict[int, Set[int]]
roster = {}  # type: Dict[int, Set[int]]
map_matches = {}  # type: Dict[str, Set[int]]
id64s = {}  # type: Dict[str, int]
team_format = {}  # type: Dict[int, Tf2Format]


def get_id64(id3):  # type: (str) -> int
    if id3 not in id64s:
        id64s[id3] = SteamID(id3).as_64
    return id64s[id3]


def team_match(red, blu, team1, team2):  # type: (Set[int], Set[int], Set[int], Set[int]) -> bool
    red_ringers = len(red - team1)
    red_ringers2 = len(red - team2)
    blu_ringers = len(blu - team1)
    blu_ringers2 = len(blu - team2)

    too_many_ringers = (min(red_ringers, red_ringers2) > 4 or
                        min(blu_ringers, blu_ringers2) > 4)
    return not too_many_ringers


def get_similar_maps(map_name):
    matchids = set()
    for key_map, v in map_matches.items():
        if key_map.split("_")[:2] == map_name.split("_")[:2]:
            matchids |= v
    return matchids


if __name__ == "__main__":
    region_format = read_region_formats()
    for p in get_rgl_matches.read_player_entries():
        if p.team_id in roster:
            roster[p.team_id].add(p.id)
        else:
            roster[p.team_id] = {p.id}
        team_format[p.team_id] = region_format[p.region_id]

    for rgl_match in get_rgl_matches.read_matches():
        matches[rgl_match.id] = rgl_match
        if rgl_match.date:
            md = rgl_match.date.date()
            if md in match_dates:
                match_dates[md].add(rgl_match.id)
            else:
                match_dates[md] = {rgl_match.id}

            if md + DAY in match_dates:
                match_dates[md + DAY].add(rgl_match.id)
            else:
                match_dates[md + DAY] = {rgl_match.id}

        if rgl_match.team1 in team_format:
            match_format = team_format[rgl_match.team1]
        elif rgl_match.team2 in team_format:
            match_format = team_format[rgl_match.team2]

        format_matches[match_format].add(rgl_match.id)
        for rgl_map in rgl_match.maps:
            if rgl_map in map_matches:
                map_matches[rgl_map].add(rgl_match.id)
            else:
                map_matches[rgl_map] = {rgl_match.id}

    for logstf in get_sorted_games():
        if logstf["length"] < 120:  # skip game if it's too short
            continue

        log_match_date = datetime.fromtimestamp(logstf["info"]["date"]).date()
        log_match_format = get_format(logstf)

        matchdate_set = match_dates.get(log_match_date, set())  # type: Set[int]
        map_set = get_similar_maps(logstf["info"]["map"])

        format_set = format_matches[log_match_format]  # type: Set[int]
        rgl_possible_match_ids = format_set & matchdate_set & map_set

        rgl_possible_matches = [matches[i] for i in
                                rgl_possible_match_ids]  # type: List[RglMatch]

        red_roster = {get_id64(i) for i in logstf["players"]
                      if logstf["players"][i]["team"] == "Red"}
        blue_roster = {get_id64(i) for i in logstf["players"]
                       if logstf["players"][i]["team"] == "Blue"}

        valid_rosters = [i for i in rgl_possible_matches
                         if i.team1 in roster and i.team2 in roster]
        valid_games = [pm for pm in valid_rosters
                       if team_match(red_roster, blue_roster,
                                     roster[pm.team1], roster[pm.team2])]

        for vg in valid_games:
            if vg.id in valid_games:
                possible_logs[vg.id].add(logstf["id"])
            else:
                possible_logs[vg.id] = {logstf["id"]}

    with open("rgl_match_logs.csv", "a", encoding="utf-8") as f:
        for rgl_id, log_ids in possible_logs.items():
            for log_id in log_ids:
                f.write("{},{}\n".format(rgl_id, log_id))
