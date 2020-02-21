from tkinter import Tk
from pathlib import Path
import re
import time

player_re = r"https://rgl\.gg/Public/PlayerProfile\.aspx"
team_re = r"https://rgl\.gg/Public/Team\.aspx"
links = set()

if not Path("player_links.txt").is_file():
    with open("player_links.txt", "w+") as f:
        print("player_links.txt")
else:
    with open("player_links.txt", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                links.add(tuple(line.split()))
        print("found", len(links), "in player_links.txt")
        
tk_window = Tk()

team_link = ""
while True:
    time.sleep(0.1)
    
    clipboard_text = tk_window.clipboard_get()
    team = re.search(team_re, clipboard_text)
    team_link = clipboard_text if team else team_link

    
    player = re.search(player_re, clipboard_text)
    if team_link and player and (team_link, clipboard_text) not in links:
        links.add( (team_link, clipboard_text) )
        print(team_link, clipboard_text)
        print(f"{len(links)} links found")
        with open("player_links.txt", "a", encoding="utf-8") as f:
            f.write(team_link + " " + clipboard_text + "\n")
            

