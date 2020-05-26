#!/usr/bin/env python3

from typing import Set, Dict, List, Any
import jinja2
from get_rgl_matches import read_player_entries

# p.id, player_join_date, player_leave_date, tid, rid, team_seasons[tid], league_id))

seasons = {} # type: Dict[int, str]
with open("rgl_seasons.csv", encoding="utf-8") as f:
    for line in f:
        season_id, season_name = line.split(",")
        seasons[int(season_id)] = season_name.strip()

teams = {} # type: Dict[int, str]
with open("rgl_teams.csv", encoding="utf-8") as f:
    for line in f:
        i, n = line.split(",")
        teams[int(i)] = n.strip()

league_names = {} # type: Dict[int, str]
with open("rgl_leagues.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        lid, lname = line.split(",")
        league_names[int(lid)] = lname.strip()

usernames = {} # type: Dict[int, str]
with open("rgl_users.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        uid, name = line.split(",")
        usernames[int(uid)] = name.strip()

user_mmr = {} # type: Dict[int, float]
with open("player_scores.csv", encoding="utf-8") as f:
    for line in f:
        if not line:
            continue
        id64, score = line.split(",")
        user_mmr[int(id64)] = float(score)


season_teams = {}   # type: Dict[int, Set]
season_leagues = {} # type: Dict[int, Set]
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

season_profiles = [] # type: List[Dict]
for s, team_set in season_teams.items():
    season = {} # type: Dict[str, Any]
    season["id"] = s
    season["name"] = seasons[s]
    season["leagues"] = []
    print("season id:", s, "season name:", seasons[s])
    for season_league in season_leagues[s]:
        print(seasons[s], league_names[season_league])
        league = {} # type: Dict[str, Any]
        league["id"] = season_league
        league["name"] = league_names[season_league]
        league_scores = [] # type: List[float]
        league["teams"] = []
        for tid in  league_teams[season_league]:
            team = {}  # type: Dict[str, Any]
            team["id"] = tid
            team["name"] = teams[tid]
            team["players"] = []

            for pid in team_players[tid]:
                player_mmr = float("nan") if pid not in user_mmr else user_mmr[pid]
                player_name = "Unnamed" if pid not in usernames else usernames[pid]
                team["players"].append((player_mmr, pid, player_name))
                if player_mmr:
                    league_scores.append(player_mmr)
            team["players"].sort(reverse=True)
            top6_players = team["players"] if len(team["players"]) < 6 else team["players"][:6]
            team["top6"] = sum([i[0] for i in top6_players])
            league["teams"].append(team)

        league_scores.sort(reverse=True)
        valid_scores = [a for a in league_scores if a]
        middle_entry = len(valid_scores) / 2
        league["median"] = valid_scores[int(middle_entry)]
        league["teams"].sort(reverse=True, key=lambda x: x["top6"])
        season["leagues"].append(league)
    season_profiles.append(season)


season_profiles.sort(reverse=True, key=lambda x: x["id"])
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"),
                               autoescape=True)
league_template = jinja_env.get_template("leagues.html")

with open("html/leagues.html", "w", encoding="utf-8") as f:
    f.write(league_template.render(seasons=season_profiles))
