team_leagues = {}

with open("team_id_leagues.csv", encoding="utf-8") as f:
    for line in f:
        league, team_id = line.strip().split(",")
        team_leagues[team_id] = league


with open("player_team_ids.csv", encoding="utf-8") as f:
    for line in f:
        teamid, playerid = line.strip().split(",")
        print(playerid + "," + teamid + "," + team_leagues[teamid])
