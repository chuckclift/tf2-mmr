#!/usr/bin/env python3

from typing import Set, Dict, List, Any
import math
import jinja2
from get_rgl_matches import read_player_entries

# p.id, player_join_date, player_leave_date, tid, rid, team_seasons[tid], league_id))

seasons = {}  # type: Dict[int, str]
with open("rgl_seasons.csv", encoding="utf-8") as f:
    for line in f:
        season_id, season_name = line.split(",")
        seasons[int(season_id)] = season_name.strip()

teams = {}  # type: Dict[int, str]
with open("rgl_teams.csv", encoding="utf-8") as f:
    for line in f:
        i, n = line.split(",")
        teams[int(i)] = n.strip()

league_names = {}  # type: Dict[int, str]
with open("rgl_leagues.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        lid, lname = line.split(",")
        league_names[int(lid)] = lname.strip()

usernames = {}  # type: Dict[int, str]
with open("rgl_users.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        uid, name = line.split(",")
        usernames[int(uid)] = name.strip()

user_mmr = {}  # type: Dict[int, float]
with open("player_scores.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        id64, score = line.split(",")
        user_mmr[int(id64)] = float(score)


season_teams = {}   # type: Dict[int, Set]
season_leagues = {}  # type: Dict[int, Set]
team_leagues = {}   # type: Dict[int, int]
team_players = {}   # type: Dict[int, Set[int]]
league_teams = {}   # type: Dict[int, Set[int]]


player_entries = read_player_entries()
for p in player_entries:
    if p.season_id not in season_teams:
        season_teams[p.season_id] = set()
    if p.team_id not in team_players:
        team_players[p.team_id] = set()
    if p.season_id not in season_leagues:
        season_leagues[p.season_id] = set()
    if p.league_id not in league_teams:
        league_teams[p.league_id] = set()

    season_teams[p.season_id].add(p.team_id)
    team_leagues[p.team_id] = p.league_id
    team_players[p.team_id].add(p.id)
    season_leagues[p.season_id].add(p.league_id)
    league_teams[p.league_id].add(p.team_id)


def get_player(pid):
    mmr = float("nan") if pid not in user_mmr else user_mmr[pid]
    name = "Unnamed" if pid not in usernames else usernames[pid]
    return (mmr, pid, name)


season_profiles = []  # type: List[Dict]
for s, team_set in season_teams.items():
    season = {}  # type: Dict[str, Any]
    season["id"] = s
    season["name"] = seasons[s]
    season["leagues"] = []
    season_profiles.append(season)
    for season_league in season_leagues[s]:
        league = {}  # type: Dict[str, Any]
        league["id"] = season_league
        league["name"] = league_names[season_league]
        league_scores = []  # type: List[float]
        league["teams"] = []
        season["leagues"].append(league)

        for tid in league_teams[season_league]:
            team = {}  # type: Dict[str, Any]
            team["id"] = tid
            team["name"] = "UNKNOWN" if tid not in teams else teams[tid]
            players = [get_player(i) for i in team_players[tid]]
            team["players"] = [i for i in players if not math.isnan(i[0])]
            league_scores += [i[0] for i in team["players"]]
            team["players"].sort(reverse=True)
            top6_players = team["players"] if len(team["players"]) < 6 else team["players"][:6]
            team["top6"] = sum([i[0] for i in top6_players])
            league["teams"].append(team)
            league["teams"].sort(reverse=True, key=lambda x: x["top6"])

        league_scores.sort(reverse=True)

        league["median"] = float("nan")
        valid_scores = [a for a in league_scores if not math.isnan(a)]
        if len(valid_scores) > 2:
            middle_entry = len(valid_scores) / 2
            league["median"] = valid_scores[int(middle_entry)]
    season["leagues"].sort(reverse=True, key=lambda x: x["median"])

print(len(season_profiles), "seasons found")


season_profiles.sort(reverse=True, key=lambda x: x["id"])
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                               autoescape=True)
league_template = jinja_env.get_template("leagues.html")

with open("html/leagues.html", "w", encoding="utf-8") as f:
    f.write(league_template.render(seasons=season_profiles))
