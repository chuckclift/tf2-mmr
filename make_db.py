#!/usr/bin/env python3

import json
import sqlite3
import datetime
from typing import Dict
from steam.steamid import SteamID  # type: ignore
import parse_logs
import sql_commands
import link_match_logs

names: Dict[str, str] = {}



def main():
    con = sqlite3.connect(sql_commands.db_file)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql_commands.create_player_stats)
    cur.execute(sql_commands.create_match_table)
    cur.execute(sql_commands.create_weapon_stats)
    cur.execute(sql_commands.create_users)
    
    with open("game_logs.json", encoding="utf-8") as f:
        line: str
        for line in f:
            g = json.loads(line)

            id3: str
            for id3 in g["names"]:
                names[id3] = g["names"][id3]
    
            log_id = g["id"]
            class_stats = parse_logs.get_user_class_stats(g)
    
            match_date = datetime.datetime.fromtimestamp(g["info"]["date"])
    
            match_data = { 
                           "log_id": g["id"], 
                           "map": g["info"]["map"], 
                           "match_time": match_date.strftime("%Y:%m:%d %H:%m:%S"),
                           "format": link_match_logs.get_format(g).name,
                           "red_score": g["teams"]["Red"]["score"],
                           "blue_score": g["teams"]["Blue"]["score"] 
                         }
    
            cur.execute(sql_commands.insert_match, match_data)
    
            for id3 in class_stats:
                for cn in class_stats[id3]:
                    if cn not in sql_commands.class_ids:
                        # sometimes there are "undefined" classes
                        continue
                    class_stats[id3][cn]["log_id"] = log_id
                    class_stats[id3][cn]["tf2_class"] = sql_commands.class_ids[cn]
                    cur.execute(sql_commands.insert_player_stats, class_stats[id3][cn])

    for id3, name in names.items():
        cur.execute(sql_commands.insert_user, {"player_id": SteamID(id3).as_64,
                                               "name": name})

    
    con.commit()
    con.close()

if __name__ == "__main__":
    main()
