from matplotlib import pyplot as plt

league_names = ["invite", "advanced", "main", "intermediate", "open", "newcomer"][::-1]
player_leagues = {}
with open("player_teamid_league.csv", encoding="utf-8") as f:
    for line in f:
        steamid64, _, league = line.strip().split(",")
        player_leagues[int(steamid64)] = league

scores = []
steam_ids = []
player_scores = {}
with open("player_scores.csv", encoding="utf-8") as f:
    for line in f:
        stid, score = line.strip().split(",")
        steam_ids.append(stid)
        scores.append(float(score))

        # print(">", stid)
        if int(stid) in player_leagues:
            if float(score) > 35:
                print(stid, score)
            player_scores[int(stid)] = float(score)


print("league, max, min, avg")
boxplot_data = []
for l in league_names:
    scores = [player_scores[i] for i in player_scores
              if player_leagues[i] == l]
    boxplot_data.append(scores)
    print("{},{:.1f},{:.1f},{:.1f}".format(l, max(scores), min(scores), sum(scores)/len(scores)))


print(len(player_scores), "rgl players found")

fig, axs = plt.subplots()
axs.hist(scores, bins=list(range(50)))
axs.axvline(x=18.5)
axs.axvline(x=21.7)
axs.axvline(x=23.7)
axs.axvline(x=25.8)
axs.axvline(x=28.8)
axs.set_ylabel("count")
axs.set_xlabel("TrueSkill MMR")
axs.set_title("RGL.GG Player MMR")
fig.savefig("score_hist.png")

fig, axs = plt.subplots()
axs.boxplot(boxplot_data, vert=False)
axs.set_yticklabels(league_names)
axs.set_xlabel("TrueSkill MMR")
axs.set_title("RGL.GG Division MMR")
fig.tight_layout()
fig.savefig("score_boxplot.png")
