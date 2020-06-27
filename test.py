#!/usr/bin/env python3

import unittest
import json
from pprint import pprint
from parse_logs import get_meds_dropped, get_user_class_stats

with open("test/2596216.json", encoding="utf-8") as f:
    json_doc = json.loads(f.read())

stats = get_user_class_stats(json_doc)
red_med = "[U:1:101435715]"

blue_demo = "[U:1:155433728]"


class ParseTest(unittest.TestCase):
    def testbasic(self):
        self.assertEqual(stats[red_med]["medic"]["drops"], 2)
        self.assertEqual(stats[red_med]["medic"]["deaths"], 4)
        self.assertEqual(stats[red_med]["medic"]["kills"], 1)
        self.assertEqual(stats[red_med]["medic"]["dmg"], 60)
        self.assertEqual(stats[red_med]["medic"]["dt"], 1355)

    def testclasskills(self):
        self.assertEqual(stats[blue_demo]["demoman"]["scout_kills"], 6)
        self.assertEqual(stats[blue_demo]["demoman"]["medic_kills"], 4)
        self.assertEqual(stats[blue_demo]["demoman"]["soldier_kills"], 3)
        self.assertEqual(stats[blue_demo]["demoman"]["demoman_kills"], 1)
        self.assertEqual(stats[blue_demo]["demoman"]["heavyweapons_kills"], 0)

    def testdrop(self):
        self.assertEqual(2, get_meds_dropped(blue_demo, json_doc))


if __name__ == "__main__":
    unittest.main()
