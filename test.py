#!/usr/bin/env python3

import unittest
import json
import sqlite3
from pprint import pprint
from steam.steamid import SteamID
from parse_logs import get_meds_dropped, get_user_class_stats
import sql_commands
import link_match_logs

with open("test/2596216.json", encoding="utf-8") as f:
    json_doc = json.loads(f.read())

stats = get_user_class_stats(json_doc)
red_med = "[U:1:101435715]"
blue_demo = "[U:1:155433728]"
game_format = link_match_logs.get_format(json_doc)

for player in stats:
    for c in stats[player]:
        stats[player][c]["log_id"] = 2596216
        stats[player][c]["format"] = game_format.name


class ParseTest(unittest.TestCase):
    def testbasic(self):
        self.assertEqual(stats[red_med]["medic"]["drops"], 2)
        self.assertEqual(stats[red_med]["medic"]["deaths"], 4)
        self.assertEqual(stats[red_med]["medic"]["kills"], 1)
        self.assertEqual(stats[red_med]["medic"]["dmg"], 60)
        self.assertEqual(stats[red_med]["medic"]["dt"], 1355)
        self.assertEqual(stats[blue_demo]["demoman"]["heals_received"], 2448)
        self.assertEqual(stats[blue_demo]["demoman"]["format"], "sixes")

    def testclasskills(self):
        self.assertEqual(stats[blue_demo]["demoman"]["scout_kills"], 6)
        self.assertEqual(stats[blue_demo]["demoman"]["medic_kills"], 4)
        self.assertEqual(stats[blue_demo]["demoman"]["soldier_kills"], 3)
        self.assertEqual(stats[blue_demo]["demoman"]["demoman_kills"], 1)
        self.assertEqual(stats[blue_demo]["demoman"]["heavyweapons_kills"], 0)

    def testdrop(self):
        self.assertEqual(2, get_meds_dropped(blue_demo, json_doc))


class MakeDbTest(unittest.TestCase):
    def testbasic(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row

        cur = con.cursor()
        cur.execute(sql_commands.create_player_stats)
        for id3 in stats:
            for cn in stats[id3]:
                cur.execute(sql_commands.insert_player_stats, stats[id3][cn])

        for row in cur.execute("select * from PlayerStats;"):
            keynames = [d[0] for d in cur.description]
            id3 = SteamID(row["player_id"]).as_steam3
            class_name = row["tf2_class"]
            for k in keynames:
                self.assertEqual(row[k], stats[id3][class_name][k])

        con.close()


if __name__ == "__main__":
    unittest.main()
