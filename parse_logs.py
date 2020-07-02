#!/usr/bin/env python3

from typing import Dict, Union, Tuple, Optional
from steam.steamid import SteamID  # type: ignore
import link_match_logs

id3_to_id64: Dict[str, int] = {}
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

med_stats = [
    "advantages_lost", "biggest_advantage_lost", "deaths_with_95_99_uber",
    "deaths_within_20s_after_uber", "avg_time_before_healing",
    "avg_time_to_build", "avg_time_before_using"
]


def get_meds_dropped(id3: str, game_log: Dict) -> int:
    """
    gets the number of enemy medics the id3 player has dropped in the given
    game log.
    """

    player_team = game_log["players"][id3]["team"]
    enemy_team = "Red" if player_team == "Blue" else "Blue"

    mediguns: Dict[str, str] = dict()
    meds_dropped = 0

    for r in game_log["rounds"]:
        latest_drop: Dict = {}
        for e in r["events"]:
            if e["type"] == "charge":
                mediguns[e["steamid"]] = e["medigun"]
            elif e["type"] == "drop" and e["team"] == enemy_team:
                latest_drop = e
            elif (e["type"] == "medic_death" and e["killer"] == id3
                  and e["time"] == latest_drop.get("time", 0) and mediguns.get(
                      latest_drop["steamid"], "medigun") == "medigun"):
                # sometimes logs.tf fails to log the medigun charge event.
                # to account for this, the get() method is used with a
                # default value of "medigun" because that is the most
                # common kind.
                meds_dropped += 1
    return meds_dropped


def get_midfight_survival(med_id3: str, gamelog: Dict) -> Tuple:
    """
    gets the midfight survivals and the midfight deaths from a gamelog for a
    medic player.  If the map isn't a koth or control points map, it returns
    (0,0) because other map types like payload do not have midfights.
    """
    game_map = gamelog["info"]["map"]
    if not game_map.startswith("koth_") and not game_map.startswith("cp_"):
        return (0, 0)
    midfight_deaths = 0  # type: int
    midfight_escapes = 0  # type: int
    for r in gamelog["rounds"]:
        med_round = any([
            a for a in r["events"] if a["type"] in {"medic_death", "charge"}
            and a["steamid"] == med_id3
        ])
        if not med_round:
            continue

        events = [
            a for a in r["events"] if a["type"] == "pointcap" or (
                a["type"] == "medic_death" and a["steamid"] == med_id3)
        ]
        if not events:
            # the game ended before pointcap
            midfight_escapes += 1
        elif events[0]["type"] == "pointcap":
            midfight_escapes += 1
        else:
            midfight_deaths += 1
    return (midfight_escapes, midfight_deaths)


def get_heals_received(id3: str, game_log: Dict) -> int:
    heal_total = 0
    for med_id, heals in game_log["healspread"].items():
        heal_total += heals.get(id3, 0)
    return heal_total


def get_user_class_stats(game_log: Dict) -> Dict[str, Dict]:
    user_classes: Dict[str, Dict] = {}
    game_format = link_match_logs.get_format(game_log)
    for id3, player in game_log["players"].items():
        if id3 not in id3_to_id64:
            id3_to_id64[id3] = SteamID(id3).as_64

        player_time = sum([c["total_time"] for c in player["class_stats"]])

        for class_stat in player["class_stats"]:
            class_name = class_stat["type"]
            user_entry: Dict[str, Union[int, str]] = {}

            # user_entry["log_id"] = game_log["id"]
            user_entry["team"] = game_log["players"][id3]["team"]
            user_entry["player_id"] = id3_to_id64[id3]
            user_entry["tf2_class"] = class_name
            user_entry["format"] = game_format.name

            user_entry["drops"] = player["drops"]
            mfs = get_midfight_survival(id3, game_log)
            user_entry["mids_survived"] = mfs[0]
            user_entry["mid_deaths"] = mfs[1]

            user_entry["headshots_hit"] = player["headshots_hit"]
            user_entry["backstabs"] = player["backstabs"]
            user_entry["ubers"] = player.get("ubertypes", {}).get("medigun", 0)

            user_entry["kills"] = class_stat["kills"]
            user_entry["assists"] = class_stat["assists"]
            user_entry["deaths"] = class_stat["deaths"]
            user_entry["dmg"] = class_stat["dmg"]
            user_entry["total_time"] = class_stat["total_time"]
            user_entry["med_drops"] = get_meds_dropped(id3, game_log)
            user_entry["heals_received"] = get_heals_received(id3, game_log)
            for m in med_stats:
                user_entry[m] = player.get("medicstats", {}).get(m, 0)

            avg_uber_length = player.get("medicstats",
                                         {}).get("avg_uber_length", 0)
            user_entry["uber_length"] = avg_uber_length * player["ubers"]

            # logs.tf doesn't offer player class-specific breakdowns on these
            # stats, so they are estimated based on the fraction of the
            # playtime
            playtime_fraction = class_stat["total_time"] / player_time
            for cn in classnames:
                class_kills = game_log["classkills"].get(id3, {}).get(cn, 0)
                class_deaths = game_log["classdeaths"].get(id3, {}).get(cn, 0)
                class_assists = game_log["classkillassists"].get(id3, {}).get(
                    cn, 0)

                user_entry[cn + "_kills"] = round(class_kills *
                                                  playtime_fraction)
                user_entry[cn + "_deaths"] = round(class_deaths *
                                                   playtime_fraction)
                user_entry[cn + "_assists"] = round(class_assists *
                                                    playtime_fraction)

            estimated_heal = (player["heal"] * class_stat["total_time"] /
                              player_time)
            user_entry["heal"] = estimated_heal

            estimated_dt = round(player["dt"] * class_stat["total_time"] /
                                 player_time)

            user_entry["dt"] = estimated_dt
            if id3 not in user_classes:
                user_classes[id3] = {}
            user_classes[id3][class_name] = user_entry
    return user_classes
