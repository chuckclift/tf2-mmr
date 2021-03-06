#!/usr/bin/env python3

db_file = "stats.db"

class_ids = {
    "scout":1,
    "soldier":2,
    "pyro":3,
    "demoman":4,
    "heavyweapons":5,
    "engineer":6,
    "medic":7,
    "sniper":8,
    "spy":9
}

classnames = {
    1:"scout",
    2:"soldier",
    3:"pyro",
    4:"demoman",
    5:"heavyweapons",
    6:"engineer",
    7:"medic",
    8:"sniper",
    9:"spy"
}

create_player_stats = """
create table if not exists PlayerStats 
(
    log_id int,
    player_id int,
    tf2_class text,
    kills int,
    deaths int,
    assists int,
    team int,
    dmg int,
    dt int,
    total_time int, 
    playtime_pct int,
    med_drops int,
    heals_received int,
    heal int,
    drops int,
    ubers int,
    deaths_with_95_99_uber int,
    deaths_within_20s_after_uber int,
    advantages_lost int,
    biggest_advantage_lost int,
    avg_time_before_healing int,
    avg_time_to_build int,
    avg_time_before_using int,
    uber_length real,
    mid_deaths int,
    mids_survived int,
    backstabs int,
    headshots_hit int,
    soldier_kills int,
    sniper_kills int,
    medic_kills int,
    scout_kills int,
    spy_kills int,
    pyro_kills int,
    engineer_kills int,
    demoman_kills int,
    heavyweapons_kills int,
    soldier_assists int,
    sniper_assists int,
    medic_assists int,
    scout_assists int,
    spy_assists int,
    pyro_assists int,
    engineer_assists int,
    demoman_assists int,
    heavyweapons_assists int,
    soldier_deaths int,
    sniper_deaths int,
    medic_deaths int,
    scout_deaths int,
    spy_deaths int,
    pyro_deaths int,
    engineer_deaths int,
    demoman_deaths int,
    heavyweapons_deaths int,
    primary key (log_id, player_id, tf2_class )
);"""

create_users = """
create table if not exists Users
(
player_id int primary key,
name text
);
"""

insert_user = """
insert or replace into users
values
(
:player_id,
:name
);
"""

create_match_table = """
create table if not exists MatchLogs
(
log_id int primary key,
map text,
match_time text,
format text,
red_score int,
blue_score int
);
"""

create_weapon_stats = """
create table if not exists WeaponStats
(
player_id int,
weapon_name text,
weapon_time int,
weapon_dmg int,
weapon_kills int,
primary key (player_id, weapon_name)
);
"""



insert_player_stats = """
insert or ignore into PlayerStats values
(
:log_id,
:player_id,
:tf2_class,
:kills,
:deaths,
:assists,
:team,
:dmg,
:dt,
:total_time,
:playtime_pct,
:med_drops,
:heals_received,
:heal,
:drops,
:ubers,
:deaths_with_95_99_uber,
:deaths_within_20s_after_uber,
:advantages_lost,
:biggest_advantage_lost,
:avg_time_before_healing,
:avg_time_to_build,
:avg_time_before_using,
:uber_length,
:mid_deaths,
:mids_survived,
:headshots_hit,
:backstabs,
:soldier_kills,
:sniper_kills,
:medic_kills,
:scout_kills,
:spy_kills,
:pyro_kills,
:engineer_kills,
:demoman_kills,
:heavyweapons_kills,
:soldier_assists,
:sniper_assists,
:medic_assists,
:scout_assists,
:spy_assists,
:pyro_assists,
:engineer_assists,
:demoman_assists,
:heavyweapons_assists,
:soldier_deaths,
:sniper_deaths,
:medic_deaths,
:scout_deaths,
:spy_deaths,
:pyro_deaths,
:engineer_deaths,
:demoman_deaths,
:heavyweapons_deaths
);
"""

get_player_stats = """
select
player_id,
tf2_class,
sum(kills),
sum(deaths),
sum(assists),
sum(team),
sum(dmg),
sum(dt),
sum(total_time),
sum(med_drops),
sum(heals_received),
sum(heal),
sum(drops),
sum(ubers),
sum(deaths_with_95_99_uber),
sum(deaths_within_20s_after_uber),
sum(advantages_lost),
sum(biggest_advantage_lost),
sum(avg_time_before_healing),
sum(avg_time_to_build),
sum(avg_time_before_using),
sum(uber_length),
sum(mid_deaths),
sum(mids_survived),
sum(headshots_hit),
sum(backstabs),
sum(soldier_kills),
sum(sniper_kills),
sum(medic_kills),
sum(scout_kills),
sum(spy_kills),
sum(pyro_kills),
sum(engineer_kills),
sum(demoman_kills),
sum(heavyweapons_kills),
sum(soldier_assists),
sum(sniper_assists),
sum(medic_assists),
sum(scout_assists),
sum(spy_assists),
sum(pyro_assists),
sum(engineer_assists),
sum(demoman_assists),
sum(heavyweapons_assists),
sum(soldier_deaths),
sum(sniper_deaths),
sum(medic_deaths),
sum(scout_deaths),
sum(spy_deaths),
sum(pyro_deaths),
sum(engineer_deaths),
sum(demoman_deaths),
sum(heavyweapons_death),
sum(deaths)
from PlayerStats
group by player_id, tf2_class;
"""

get_game_rosters = ("select log_id, team, group_concat(player_id) as roster" +
                    " from PlayerStats group by log_id, team;")



insert_match = """
insert or ignore into MatchLogs
values
(
:log_id,
:map,
:match_time,
:format,
:red_score,
:blue_score
);
"""
