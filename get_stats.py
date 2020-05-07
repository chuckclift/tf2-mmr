#!/usr/bin/env python3
"""
This script parses data from the game_logs.json file and uses it to generate
an html report showing player statistics.
"""

import json
import datetime
from typing import Dict
import html
from steam.steamid import SteamID # type: ignore

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

newest_log = None # pylint: disable=C0103
oldest_log = None # pylint: disable=C0103
games_played = 0 # pylint: disable=C0103

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
            id64 = SteamID(id3).as_64 # pylint: disable=C0103
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

print("""
<html>
<head>
    <meta charset="UTF-8">
    <title>Player Stats</title>
    <link rel='icon' type='image/png' href='/favicon.ico'>
    <style>
    body {
        background-color:#4d4d4d;
        margin:0px;
    }
    td {
        width: 120px;
    }
    th {
        text-align:left;
    }
    </style>
</head>
<body>
<nav style='background-color:#595959;'>
&nbsp; &nbsp;
<a  style='font-size:36px; color:white;' href='/team_report.html'>
    Team Reports
</a> &nbsp; &nbsp;
<a  style='font-size:36px; color:white;' href='/'>
    Player Reports
</a>
</nav>
""")

for id64, s in stats.items():
    print("<div style='background-color:white; margin:20px; padding:10px; width: 80%;'>")
    print("<h1>", player_names[id64], id64, "</h1>")
    mmr = player_mmr.get(id64, float("nan"))
    print("<p><b>mmr</b> : {:.2f}</p>".format(mmr))
    print("<table>")
    print("<tr>" +
          "<th>classname</th>" +
          "<th> K / M </th>" +
          "<th> D / M </th>" +
          "<th> KA / D </th>" +
          "<th> DA / M </th>" +
          "<th> DT / M </th>" +
          "<th> DaS </th>" +
          "<th> Hours </th>" +
          "</tr>")
    for classname, class_stats in sorted(s.items(), key=lambda x: x[1]["total_time"], reverse=True):
        M = class_stats["total_time"] / 60
        if M < 1:
            # ignore classes with under 1 minute of playtime
            continue

        if classname not in classnames:
            continue

        ka_per_d = float("nan")
        if class_stats["deaths"] > 0:
            ka_per_d = ((class_stats["kills"] + class_stats["assists"]) /
                        class_stats["deaths"])
        damage_surplus = class_stats["dmg"] / M - class_stats["dt"] / M
        row_str = ("<tr>" +
                   "<td>{}</td>".format(classname) +
                   "<td>{:.2f}</td>".format(class_stats["kills"] / M) +
                   "<td>{:.2f}</td>".format(class_stats["deaths"] / M) +
                   "<td>{:.2f}</td>".format(ka_per_d) +
                   "<td>{:.2f}</td>".format(class_stats["dmg"] / M) +
                   "<td>{:.2f}</td>".format(class_stats["dt"] / M) +
                   "<td>{:.2f}</td>".format(damage_surplus) +
                   "<td>{:.2f}</td>".format(M / 60) +
                   "</tr>")
        print(row_str)

    print("</table>")
    print("</div>")


print("""
<div style='background-color:white; margin:20px; padding:10px; width: 80%;'>
<h1>Glossary</h1>
<h2>K / M : Kills per Minute</h2>
<h2>D / M : Deaths per Minute</h2>
<h2>KA / D : Kills and assists per death</h2>
<h2>DA / M : Damage per Minute</h2>
<h2>DT / M : Damage taken  per Minute</h2>
<h2>DaS : Damage Surplus ( DA/M - DT/M )</h2>
<p>log data from {oldest} to {newest}</p>
<p>{players} players found</p>
<p>{games} games analyzed</p>
</div>
""".format(oldest=oldest_log, newest=newest_log, players=len(stats),
           games=games_played))
print("</body></html>")
