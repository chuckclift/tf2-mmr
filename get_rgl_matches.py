#!/usr/bin/env python3

"""
Parses the RGL site to get match data including league, season, team,
and player data.
"""

from urllib.request import Request, urlopen
from typing import Dict, Set, NamedTuple, Optional, List, Tuple
import logging
import time
import re
from datetime import datetime
import bs4  # type: ignore

logging.basicConfig(format="%(asctime)s %(message)s",
                    filename="rgl_match_scraper.log", level=logging.DEBUG)

REQUEST_DELAY = 5
TEAM_RE = re.compile(r"Team\.aspx.*t=([0-9]+)")
PLAYER_RE = re.compile(r"PlayerProfile\.aspx.*p=([0-9]+)")
LEAGUE_TABLE_RE = re.compile(r"/Public/LeagueTable\.aspx")
LEAGUE_ID_RE = re.compile(r"LeagueTable\.aspx.*g=([0-9]+)")
MATCH_RE = re.compile(r"Match\.aspx\?.*m=([0-9]+)")
RGL_DATE = re.compile("[0-9]{1,2}/[0-9]{1,2}/[0-9]{1,4}")


Bs4Results = Optional[bs4.element.ResultSet]
Bs4Tag = Optional[bs4.element.Tag]

seasons = {}  # type: Dict[int, str]
team_names = {}  # typing: Dict[int, str]
team_regions = {}  # typing: Dict[int, int]
team_seasons = {}  # typing: Dict[int, int]
league_names = {}  # typing: Dict[int, str]
usernames = set()  # typing: Set[Tuple[int, str]]

RglPlayer = NamedTuple("RglPlayer", [("id", int),
                                     ("name", str),
                                     ("joined", Optional[datetime]),
                                     ("left", Optional[datetime])])

RglPlayerEntry = NamedTuple("RglPlayerEntry", [("id", int),
                                               ("joined", Optional[datetime]),
                                               ("left", Optional[datetime]),
                                               ("team_id", int),
                                               ("region_id", int),
                                               ("season_id", int),
                                               ("league_id", int)])

RglMatch = NamedTuple("RglMatch", [("id", int),
                                   ("date", Optional[datetime]),
                                   ("maps", Set[str]),
                                   ("team1", int),
                                   ("team1_score", Optional[float]),
                                   ("team2", int),
                                   ("team2_score", Optional[float])])


def read_player_entries():  # type: () -> List[RglPlayerEntry]
    player_entries = []
    with open("player_teams.csv", encoding="utf-8") as f:
        for line in f:
            pid, joined, left, tid, rid, season, league = line.split(",")

            joined_timestamp = float(joined)
            join_date = (None if not joined_timestamp
                         else datetime.fromtimestamp(joined_timestamp))

            left_timestamp = float(left)
            left_date = (None if not left_timestamp
                         else datetime.fromtimestamp(left_timestamp))

            player_entries.append(RglPlayerEntry(int(pid),
                                                 join_date,
                                                 left_date,
                                                 int(tid),
                                                 int(rid),
                                                 int(season),
                                                 int(league)))
    return player_entries


def read_matches():  # type: () -> List[RglMatch]
    csv_matches = []
    with open("matches.csv", encoding="utf-8") as f:
        for line in f:
            if not line:
                continue

            # format(m.id, m.team1, m.team1_score, m.team2, m.team2_score, m.date, mapname)
            fields = line.split(",")

            team1_score = None  # type: Optional[float]
            if not fields[2].strip() == "None":
                team1_score = float(fields[2])

            team2_score = None  # type: Optional[float]
            if not fields[4].strip() == "None":
                team2_score = float(fields[4])

            match_date = None
            if not fields[5].strip() == "None":
                match_date = datetime.fromtimestamp(float(fields[5]))
            maps = set(fields[6].split(" "))
            csv_matches.append(RglMatch(int(fields[0]),  # match id
                                        match_date,
                                        maps,
                                        int(fields[1]),  # team 1
                                        team1_score,
                                        int(fields[3]),  # team 2
                                        team2_score))
    return csv_matches


def read_teams():  # type: () -> Dict
    rgl_teams = {}
    with open("rgl_teams.csv", encoding="utf-8") as f:
        for line in f:
            if not line:
                continue
            tid, name = line.split(",")
            rgl_teams[int(tid)] = name
    return rgl_teams


def row_to_player(tr):  # type: (bs4.element.Tag) -> Optional[RglPlayer]
    """
    Extracts an RGL Player from a table row of a team page
    """
    player_link = tr.find("a", href=PLAYER_RE)  # type:  Bs4Tag
    date_rows = tr.find_all("td", text=RGL_DATE)  # type: Bs4Results

    if not player_link:
        logging.info("No player links in " + str(tr))
        return None
    if not date_rows:
        logging.info("No dates in " + str(tr))
        return None

    player_id_match = re.search(PLAYER_RE, player_link.get("href"))
    if not player_id_match:
        logging.info("No player id in " + str(tr))
        return None

    player_dates = [i.text.strip()
                    for i in date_rows if not i.find("a")]  # type: List[str]

    player_name = player_link.text.strip()
    joined = None  # type: Optional[datetime]
    left = None  # type: Optional[datetime]

    if player_dates:
        joined = datetime.strptime(player_dates.pop(0).strip(), "%m/%d/%Y")

    if player_dates:
        left = datetime.strptime(player_dates.pop(0).strip(), "%m/%d/%Y")

    player_id = int(player_id_match.group(1))
    return RglPlayer(player_id, player_name, joined, left)


def row_to_match(tr):  # type: (bs4.element.Tag) -> Optional[RglMatch]
    """
    Extracts an RGL Match from the table row of a team page
    """
    match_link = tr.find("a", href=MATCH_RE)  # type: Bs4Tag
    if not match_link:
        logging.info("No match link in " + str(tr))
        return None

    match_id_match = re.search(MATCH_RE, match_link.get("href"))
    if not match_id_match:
        logging.info("No match id in " + str(tr))
        return None
    match_id = int(match_id_match.group(1))

    team_links = tr.find_all("a", href=TEAM_RE)  # type: Bs4Results

    if not team_links:
        logging.info("No team link in " + str(tr))
        return None

    match_maps = {img.parent.get("title") for img in tr.find_all("img")}

    team_hrefs = [a.get("href") for a in team_links]  # type: List[str]
    teams = [re.search(TEAM_RE, h) for h in team_hrefs]
    team_ids = [int(t.group(1)) for t in teams if t]  # type: List[int]

    if len(team_ids) < 2:
        logging.info("under 2 teams found in " + str(tr))
        return None

    team1 = team_ids[0]  # type: int
    team2 = team_ids[1]  # type: int

    team1_score = None
    team2_score = None

    RGL_SCORE = re.compile(r"(-?\d{1,3}\.?\d{0,3})\s*-\s*(-?\d{1,3}\.?\d{0,3})")
    two_number_cells = tr.find_all("td", text=RGL_SCORE)  # type: Bs4Results
    if two_number_cells:
        # cells like the team cells, the match cell, and the map cells have links
        # in them.  This list comprehension gets rid of them
        score_cell = [c for c in two_number_cells if not c.find("a")][0]
        score_match = re.search(RGL_SCORE, score_cell.text)
        if score_match:
            team1_score = float(score_match.group(1))
            team2_score = float(score_match.group(2))

    match_dtime = None  # type: Optional[datetime]
    date_cells = tr.find_all("td", text=RGL_DATE)  # type: Bs4Results

    if date_cells:
        match_date = [d.text for d in date_cells
                      if not d.find("a")][0]  # type: str
        if match_date:
            match_date = " ".join(match_date.split()[:3])
            match_dtime = datetime.strptime(
                match_date.strip(), "%m/%d/%Y %I:%M %p")
    return RglMatch(match_id, match_dtime, match_maps, team1, team1_score,
                    team2, team2_score)


def main():
    h = {"User-Agent": "Rgl Retriever"}
    r = Request("https://rgl.gg/Public/Regions.aspx", headers=h)
    response = urlopen(r).read().decode("utf-8")
    doc = bs4.BeautifulSoup(response, "html.parser")

    for l in doc.find_all("a", href=LEAGUE_TABLE_RE):
        season_id_match = re.search("s=([0-9]+)", l.get("href"))
        if season_id_match:
            season_id = int(season_id_match.group(1))
            season_name = l.text.strip()
            seasons[season_id] = season_name

    for s in seasons:
        time.sleep(REQUEST_DELAY)
        league_table = "https://rgl.gg/Public/LeagueTable.aspx?s=" + str(s)
        r = Request(league_table, headers=h)
        league_table_string = urlopen(r).read().decode("utf-8")
        league_table_doc = bs4.BeautifulSoup(
            league_table_string, "html.parser")
        team_links = league_table_doc.find_all("a", href=TEAM_RE)
        logging.info("{} team links found for {}".format(
            len(team_links), seasons[s]))

        for l in team_links:
            team_id_match = re.search(TEAM_RE, l.get("href"))
            if not team_id_match:
                logging.info("no team id found for {}".format(s))
                continue
            team_name = l.text.strip()
            tid = int(team_id_match.group(1))  # type: int

            team_names[tid] = team_name
            team_seasons[tid] = s

            region_id_match = re.search("r=([0-9]+)", l.get("href"))
            if region_id_match:
                team_regions[tid] = int(region_id_match.group(1))

    logging.info("{} team names found".format(len(team_names)))
    logging.info("{} regions found".format(len(team_regions)))
    logging.info("{} seasons found".format(len(seasons)))

    for tid, rid in team_regions.items():
        time.sleep(REQUEST_DELAY)
        team_url = "https://rgl.gg/Public/Team.aspx?t={}&r={}".format(tid, rid)
        r = Request(team_url, headers=h)
        team_string = urlopen(r).read().decode("utf-8")
        team_doc = bs4.BeautifulSoup(team_string, "html.parser")

        logging.info(team_url)
        league_link = team_doc.find("a", href=LEAGUE_ID_RE)
        if not league_link:
            logging.info("no league link for team {} skipping it".format(tid))
            continue
        league_id_match = re.search(LEAGUE_ID_RE, league_link.get("href"))
        if league_id_match:
            league_id = int(league_id_match.group(1))
            league_names[league_id] = league_link.text.strip()

        player_rows = [tr for tr in team_doc.find_all("tr")
                       if tr.find("a", href=PLAYER_RE)]

        players = [row_to_player(i) for i in player_rows]
        valid_players = [p for p in players if p]  # type: List[RglPlayer]
        usernames.update({(p.id, p.name) for p in valid_players})
        with open("player_teams.csv", "a", encoding="utf-8") as f:
            for p in valid_players:
                player_join_date = 0 if not p.joined else p.joined.timestamp()
                player_leave_date = 0 if not p.left else p.left.timestamp()
                f.write("{},{},{},{},{},{},{}\n".format(p.id,
                                                        player_join_date,
                                                        player_leave_date,
                                                        tid,
                                                        rid,
                                                        team_seasons[tid],
                                                        league_id))

        match_rows = [tr for tr in team_doc.find_all("tr")
                      if tr.find("a", href=MATCH_RE)]  # type: List[Optional[RglMatch]]
        matches = [row_to_match(tr) for tr in match_rows]
        valid_matches = [m for m in matches if m]  # type: List[RglMatch]
        with open("matches.csv", "a", encoding="utf-8") as f:
            for m in valid_matches:
                map_cell = " ".join(m.maps)
                date_cell = "None"
                if m.date:
                    date_cell = str(m.date.timestamp())
                f.write("{},{},{},{},{},{},{}\n".format(m.id, m.team1, m.team1_score,
                                                        m.team2, m.team2_score,
                                                        date_cell, map_cell))

    with open("rgl_teams.csv", "w", encoding="utf-8") as f:
        for t, n in team_names.items():
            f.write("{},{}\n".format(t, n.replace(",", " ")))

    with open("rgl_leagues.csv", "w", encoding="utf-8") as f:
        for l, n in league_names.items():
            f.write("{},{}\n".format(l, n.replace(",", " ")))

    with open("rgl_users.csv", "w", encoding="utf-8") as f:
        for id64, username in usernames:
            f.write("{},{}\n".format(id64, username.replace(",", " ")))


if __name__ == "__main__":
    main()
