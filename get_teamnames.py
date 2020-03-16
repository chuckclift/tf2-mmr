#!/usr/bin/env python3

import re
from bs4 import BeautifulSoup

team_re = re.compile(r"/Public/Team\.aspx")

with open("league_table.html", encoding="utf-8") as f:
    doc = BeautifulSoup(f.read(), "html.parser")
    team_links = doc.find_all("a", href=team_re)

    for l in team_links:
        link = l.get("href")
        teamid = re.search(r"(t=)([0-9]+)", link).group(2)

        with open("team_names.csv", "a", encoding="utf-8") as g:
            g.write(teamid + "," + l.text.strip() + "\n")
