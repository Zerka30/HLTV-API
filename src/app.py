import os
import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

import config

# Create Instance of Flask Server
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "changeme")
app.config["JSON_SORT_KEYS"] = False

# Function to get team upcoming matches
def get_upcomming_matches(team_id):
    # Fetch data for upcoming matches
    headers = {"User-Agent": config.USER_AGENT}
    response = requests.get(
        config.BASE_URL + "/matches?team=" + team_id, headers=headers
    )
    body = response.text
    soup = BeautifulSoup(body, "html.parser")
    incoming_match = soup.select_one(".upcomingMatchesWrapper")

    incoming_match_data = []
    for match in incoming_match.select(".upcomingMatch"):
        team2 = {
            "name": match.select_one(".matchTeam.team2 .matchTeamName").text,
            "logo": match.select_one(".matchTeam.team2 .matchTeamLogo")["src"],
        }

        # Opponent is always the other team
        opponent = team2

        incoming_match_data.append(
            {
                "id": int(match.select_one("a")["href"].split("/")[2]),
                "opponent": opponent,
                "tournament": {
                    "name": match.select_one(".matchEvent .matchEventName").text,
                    "logo": match.select_one(".matchEvent .matchEventLogo")["src"],
                },
                "type": match.select_one(".matchMeta").text,
                "date": int(match.select_one(".matchTime").get("data-unix")),
                "match_url": config.BASE_URL + match.select_one("a")["href"],
            }
        )

    return incoming_match_data


# Function to get team matches history
def get_history(team_id):

    # Fetch data for results
    headers = {"User-Agent": config.USER_AGENT}
    response = requests.get(
        config.BASE_URL + "/results?team=" + team_id, headers=headers
    )
    body = response.text
    soup = BeautifulSoup(body, "html.parser")
    result_match = soup.select_one(".results-all")
    res = []
    for day in result_match.select(".results-sublist"):
        for match in day.select_one(".result-con"):
            team1 = {
                "name": match.select_one(".team1 .team").text,
                "logo": match.select_one(".team1 .team-logo")["src"],
            }
            team2 = {
                "name": match.select_one(".team2 .team").text,
                "logo": match.select_one(".team2 .team-logo")["src"],
            }

            # Check who won
            winner = match.select_one(".team-won").text
            result = "Victory" if winner == team1["name"] else "Defeat"

            winner_score = match.select_one(".result-score .score-won").text
            looser_score = match.select_one(".result-score .score-lost").text

            score = (
                winner_score + " - " + looser_score
                if result == "Victory"
                else looser_score + " - " + winner_score
            )

            opponent = team2

            res.append(
                {
                    "id": int(match["href"].split("/")[2]),
                    "result": result,
                    "score": score,
                    "opponent": opponent,
                    "tournament": {
                        "name": match.select_one(".event-name").text,
                        "logo": match.select_one(".event-logo")["src"],
                    },
                    "type": match.select_one(".map-text").text,
                    "match_url": config.BASE_URL + match["href"],
                }
            )

    return res


# Route to get news
@app.route("/news", methods=["GET"])
def get_news():
    res = requests.get(config.RSS_URL + "/news")
    xml = res.text

    if not xml.startswith("<?xml"):
        return jsonify({"error": "Invalid XML"}), 400

    root = ET.fromstring(xml)
    rss = []

    for item in root.findall("./channel/item"):
        rss.append(
            {
                "title": item.find("./title").text,
                "description": item.find("./description").text,
                "link": item.find("./link").text,
                "pub_date": item.find("./pubDate").text,
            }
        )

    return jsonify(rss), 200


# Route to search a team or a player
@app.route("/search", methods=["GET"])
def search():
    # The query will be like this : /search?team=team_name or /search?player=player_name
    # First of all, we need to check if the query is for a team or a player

    # If the query is for a team
    if "team" in request.args:
        try:
            team_name = request.args["team"]
            headers = {"User-Agent": config.USER_AGENT}
            res = requests.get(
                config.BASE_URL + "/search?term=" + team_name, headers=headers
            )

            res = res.json()[0]["teams"][0]

            players = []
            for player in res["players"]:
                players.append(
                    {
                        "nickname": player["nickName"],
                        "firstName": player["firstName"],
                        "lastName": player["lastName"],
                        "flag": player["flagUrl"],
                        "hltv_url": config.BASE_URL + player["location"],
                    }
                )

            return (
                jsonify(
                    {
                        "id": res["id"],
                        "name": res["name"],
                        "logo": res["teamLogoDay"],
                        "flag": res["flagUrl"],
                        "hltv_url": config.BASE_URL + res["location"],
                        "players": players,
                    }
                ),
                200,
            )
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    # If the query is for a player
    elif "player" in request.args:
        try:
            player_nickname = request.args["player"]
            headers = {"User-Agent": config.USER_AGENT}
            res = requests.get(
                config.BASE_URL + "/search?term=" + player_nickname, headers=headers
            )

            res = res.json()[0]["players"][0]

            return (
                jsonify(
                    {
                        "id": res["id"],
                        "nickname": res["nickName"],
                        "firstName": res["firstName"],
                        "lastName": res["lastName"],
                        "flag": res["flagUrl"],
                        "picture": res["pictureUrl"],
                        "hltv_url": config.BASE_URL + res["location"],
                        "team": {
                            "name": res["team"]["name"],
                            "logo": res["team"]["teamLogoDay"],
                            "hltv_url": config.BASE_URL + res["team"]["location"],
                        },
                    }
                ),
                200,
            )
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "Invalid query"}), 400


# Route to get top 30 teams
@app.route("/ranking", methods=["GET"])
def get_top_teams():
    try:
        response = requests.get(
            config.BASE_URL + "/ranking/teams",
            headers={"User-Agent": config.USER_AGENT},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        all_content = soup.select(".ranked-team")
        teams = []

        for element in all_content:
            id = int(element.select_one(".moreLink")["href"].split("/")[2])
            ranking = int(element.select_one(".position").text.replace("#", ""))
            logo = element.select_one(".team-logo img")["src"]
            name = element.select_one(".teamLine .name").text
            players = []

            for p in element.select(".player-holder"):
                player = p.select_one("a")
                pic = player.select_one(".playerPicture")
                nickname = player.select_one(".nick").text

                players.append(
                    {
                        "id": int(player["href"].split("/")[2]),
                        "nickname": nickname,
                        "fullname": player.select_one(".playerPicture")["alt"]
                        .replace(f"'{nickname}'", "")
                        .replace("  ", " "),
                        "picture": player.select_one(".playerPicture")["src"],
                        "hltv_url": config.BASE_URL + player["href"],
                    }
                )
            teams.append(
                {
                    "id": id,
                    "ranking": ranking,
                    "name": name,
                    "logo": logo,
                    "players": players,
                }
            )

        return jsonify(teams), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get team data
@app.route("/team/<string:team_id>", methods=["GET"])
def get_team_date(team_id):
    try:
        headers = {"User-Agent": config.USER_AGENT}
        response = requests.get(
            config.BASE_URL + "/team/" + team_id + "/_", headers=headers
        )
        body = response.text

        soup = BeautifulSoup(body, "html.parser")
        team_profile = soup.select_one(".teamProfile")

        if not team_profile:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "There is no team available, something went wrong.",
                    }
                ),
                404,
            )

        lineup = team_profile.select(".bodyshot-team > a")

        players = []
        for player in lineup:
            country_name = player.select_one(".flag")["title"]
            country_flag = f"{config.BASE_URL}{player.select_one('.flag')['src']}"
            nickname = player["title"]
            players.append(
                {
                    "id": int(player["href"].split("/")[2]),
                    "fullname": player.select_one("img")["title"]
                    .replace(f"'{nickname}'", "")
                    .replace("  ", " "),
                    "image": player.select_one("img")["src"],
                    "nickname": player["title"],
                    "country": {"name": country_name, "flag": country_flag}
                    if country_name
                    else None,
                }
            )

        social_media = team_profile.select(".socialMediaButtons > a")
        social = []
        for media in social_media:
            social.append(
                {
                    "name": media["href"].split(".")[1],
                    "link": media["href"],
                }
            )

        name = team_profile.select_one(".profile-team-name").text
        logo = team_profile.select_one(".teamlogo")["src"]

        stats_container = team_profile.select(".profile-team-stats-container > div")
        ranking = int(stats_container[0].select_one(".right").text.replace("#", ""))
        average_player_age = float(stats_container[2].select_one(".right").text)
        coach = stats_container[3].select_one(".right").text.strip()

        # Get map statistics
        map_stats = {
            "dust2": None,
            "mirage": None,
            "inferno": None,
            "overpass": None,
            "nuke": None,
            "vertigo": None,
            "ancient": None,
            "anubis": None,
        }

        # Get team maps statistics
        try:
            maps_statistics = team_profile.select_one(".map-statistics")

            i = 0
            for maps in maps_statistics.select(".map-statistics-container"):
                map_name = maps_statistics.select(".map-statistics-row-map-mapname")[
                    i
                ].text
                map_stats[map_name.lower()] = float(
                    maps.select_one(".map-statistics-row-win-percentage").text.split(
                        "%"
                    )[0]
                )
                i += 1
        except:
            map_stats = "[ERROR] No map statistics available..."

        # Get team 5 last maps
        try:
            last_maps = team_profile.select_one(".last-5-matches")
            last_5_maps = []

            for maps in last_maps.select("a"):
                opponent = maps.select_one(".highlighted-team-name").text
                map_result = maps.select_one(".highlighted-match-status").text
                last_5_maps.append(
                    {
                        "opponent": opponent,
                        "result": map_result,
                    }
                )
        except:
            last_5_maps = "[ERROR] No last 5 maps available..."

        # Get team upcomming matches
        try:
            upcomming = team_profile.select_one("#ongoingEvents")
            events = upcomming.select_one(".upcoming-events-holder")
            upcoming_events = []
            for event in events.select("a"):
                date = event.select("span[data-unix]")

                # Managed events that start and end at the same date
                try:
                    start = int(date[0].get("data-unix"))
                    end = int(date[1].get("data-unix"))
                except:
                    start = int(date[0].get("data-unix"))
                    end = int(date[0].get("data-unix"))

                upcoming_events.append(
                    {
                        "name": event.select_one(".eventbox-eventname").text,
                        "logo": event.select_one(".eventbox-eventlogo").select_one(
                            "img"
                        )["src"],
                        "date": {
                            "start": start,
                            "end": end,
                        },
                        "hltv_url": config.BASE_URL + event["href"],
                    }
                )
        except Exception as e:
            upcoming_events = []

        # Get team trophies
        try:
            trophies = team_profile.select_one(".trophyRow")
            trophies_data = []
            for trophy in trophies.select("a"):
                trophies_data.append(
                    {
                        "name": trophies.select_one(".trophyDescription")["title"],
                        "logo": trophies.select_one(".trophyIcon")["src"],
                        "hltv_url": config.BASE_URL + trophy["href"],
                    }
                )
        except:
            trophies_data = []

        # Get team country
        country = {
            "name": team_profile.select_one(".team-country").text,
            "flag": config.BASE_URL + team_profile.select_one(".flag")["src"],
        }

        return (
            jsonify(
                {
                    "id": int(team_id),
                    "name": name,
                    "logo": logo,
                    "ranking": ranking,
                    "country": country,
                    "average_player_age": average_player_age,
                    "coach": coach,
                    "players": players,
                    "stats": {
                        "last_5_maps": last_5_maps,
                        "past_3_months": map_stats,
                    },
                    "trophies": trophies_data,
                    "social_media": social,
                    "upcomming_events": upcoming_events,
                    "matchs": {
                        "incoming": get_upcomming_matches(team_id),
                        "results": get_history(team_id),
                    },
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get team upcomming matches
@app.route("/team/<string:team_id>/upcoming", methods=["GET"])
def get_team_upcomming_matches(team_id):
    try:
        return jsonify(get_upcomming_matches(team_id)), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get team result
@app.route("/team/<string:team_id>/result", methods=["GET"])
def get_team_result(team_id):
    try:
        return jsonify(get_history(team_id)), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get player data
@app.route("/player/<string:player_id>", methods=["GET"])
def get_player_data(player_id):
    try:
        headers = {"User-Agent": config.USER_AGENT}
        response = requests.get(
            config.BASE_URL + "/player/" + player_id + "/_", headers=headers
        )
        body = response.text

        soup = BeautifulSoup(body, "html.parser")
        player_profile = soup.select_one(".playerProfile")

        # Get basics informations
        name = player_profile.select_one(".playerRealname").text.strip()
        team = player_profile.select_one(".playerTeam")

        # Get all appearances in hltv top 20
        try:
            all_appearances = player_profile.select_one(".top20ListRight").find_all("a")
            appearances = []
            for appearance in all_appearances:
                appearances.append(
                    {
                        "year": int(re.findall(r"\d{4}", appearance["href"])[1]),
                        "positon": int(appearance.text.split("#")[0]),
                        "news": config.BASE_URL + appearance["href"],
                    }
                )

            top20 = all_appearances[-1]
            top = {
                "has_appeared": True if top20 is not None else False,
                "last_appearance": {
                    "year": int(re.findall(r"\d{4}", top20["href"])[1]),
                    "positon": int(top20.text.split("#")[0]),
                    "news": config.BASE_URL + top20["href"],
                },
                "all_appearances": appearances,
            }
        except:
            top = {
                "has_appeared": False,
                "last_appearance": None,
                "all_appearances": [],
            }

        # Check if the player is a major winner
        try:
            major = player_profile.select_one(".majorWinner").text
            major_winner = {
                "winner": True,
                "champions": int(re.findall(r"\d{1}", major)[0]),
            }
        except:
            major_winner = {"winner": False, "champions": None}

        # General data about player and team
        try:
            stats = player_profile.select(".stat")
            stats_data = []
            for stat in stats:
                stats_data.append(stat.text)

            general_data = {
                "numbers_teams": int(stats_data[0]),
                "day_in_current_team": int(stats_data[1]),
                "day_in_team": int(stats_data[2]),
            }
        except:
            general_data = "error when getting general data"

        # Get current team of the player
        try:
            current_team = None

            team_element = player_profile.select_one(".team")
            trophies = team_element.select_one(".trophy-row-trophy").select("a")
            trophies_data = []
            for trophy in trophies:
                trophies_data.append(
                    {
                        "name": trophy.select_one("img")["title"],
                        "trophy": config.BASE_URL + trophy.select_one("img")["src"],
                        "event_url": config.BASE_URL + trophy["href"],
                    }
                )

            current_team = {
                "name": team_element.select_one(".team-name").text,
                "logo": team_element.select_one(".team-logo")["src"],
                "date": {
                    "entrance": int(
                        team_element.select_one(".time-period-cell")
                        .select_one("span")
                        .get("data-unix")
                    ),
                    "left": None,
                },
                "trophies": trophies_data,
                "hltv_url": config.BASE_URL
                + team_element.select_one(".team-name-cell").select_one("a")["href"],
            }
        except:
            current_team = None

        # Get former teams of the player
        try:
            former_teams = []
            for team in player_profile.select(".past-team"):
                date = team.select_one(".time-period-cell").select("span")
                trophies = team.select_one(".trophy-row-trophy").select("a")
                trophies_data = []
                for trophy in trophies:
                    trophies_data.append(
                        {
                            "name": trophy.select_one("img")["title"],
                            "trophy": config.BASE_URL + trophy.select_one("img")["src"],
                            "event_url": config.BASE_URL + trophy["href"],
                        }
                    )

                former_teams.append(
                    {
                        "name": team.select_one(".team-name").text,
                        "logo": team.select_one(".team-logo")["src"],
                        "date": {
                            "entrance": int(date[0].get("data-unix")),
                            "left": int(date[1].get("data-unix")),
                        },
                        "trophies": trophies_data,
                        "hltv_url": config.BASE_URL
                        + team.select_one(".team-name-cell").select_one("a")["href"],
                    }
                )
        except:
            former_teams = "error when fetching former teams"

        # Get trophies win by the player
        trophies = {"trophies": [], "mvps": [], "htlv_top20": top}
        try:
            trophies_selector = player_profile.select_one("#Trophies")
            trophies_element = trophies_selector.select(".trophy-detail")

            for trophy in trophies_element:
                trophyUrl = trophy.select_one("img")["src"]

                # Check if the trophy is a valid url
                if not trophyUrl.startswith("https://"):
                    trophyUrl = config.BASE_URL + trophy.select_one("img")["src"]

                trophies["trophies"].append(
                    {
                        "name": trophy.select_one(".trophy-event").text,
                        "trophy": trophyUrl,
                        "event_url": config.BASE_URL + trophy.select_one("a")["href"],
                    }
                )
        except:
            trophies["trophies"] = "error when fetching trophies"

        # Get mvps win by the player
        try:
            mvps_selector = player_profile.select_one("#MVPs")
            mvps_element = mvps_selector.select(".trophy-detail")

            for mvp in mvps_element:
                mvpUrl = mvp.select_one("img")["src"]

                # Check if the trophy is a valid url
                if not mvpUrl.startswith("https://"):
                    mvpUrl = config.BASE_URL + mvp.select_one("img")["src"]

                trophies["mvps"].append(
                    {
                        "name": mvp.select_one(".trophy-event").text,
                        "trophy": mvpUrl,
                        "event_url": config.BASE_URL + mvp.select_one("a")["href"],
                    }
                )
        except:
            trophies["mvps"] = "error when fetching mvps"

        # Get basics statistics
        stats = player_profile.select(".statsVal")
        stats_data = []
        for stats in stats:
            stats_data.append(stats.text)

        return jsonify(
            {
                "id": player_id,
                "nickname": player_profile.select_one(".playerNickname").text,
                "name": {
                    # Attribut fullname has a space between firstname, we want to remove it
                    "fullname": name,
                    "firstname": name.split(" ")[0],
                    "lastname": name.split(" ")[1],
                },
                "picture": player_profile.select_one(".bodyshot-img")["src"],
                "age": int(
                    re.findall(r"\d+", player_profile.select_one(".playerAge").text)[0]
                ),
                "flag": config.BASE_URL + player_profile.select_one(".flag")["src"],
                "teams": {
                    "general_data": general_data,
                    "current_team": current_team,
                    "former_teams": former_teams,
                },
                "trophies": trophies,
                "stats": {
                    "rating": float(stats_data[0]),
                    "kills_per_round": float(stats_data[1]),
                    "headshot_percentage": float(stats_data[2].split("%")[0]),
                    "maps_played": int(stats_data[3]),
                    "deaths_per_round": float(stats_data[4]),
                    "rounds_contributed": float(stats_data[5].split("%")[0]),
                },
                "major_winner": major_winner,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Route to get complete player statistics
@app.route("/player/<int:player_id>/stats", methods=["GET"])
def get_player_stats(player_id):
    try:
        headers = {"User-Agent": config.USER_AGENT}
        response = requests.get(
            config.BASE_URL + "/stats/players/" + str(player_id) + "/_", headers=headers
        )
        body = response.text

        soup = BeautifulSoup(body, "html.parser")
        player_profile = soup.select_one(".playerSummaryStatBox")
        stats_element = soup.select_one(".statistics")
        stats_data = {}
        for stats in stats_element.select(".stats-row"):
            stats_data[stats.select("span")[0].text] = float(
                stats.select("span")[1].text.split("%")[0]
            )

        for main_row in soup.select(".summaryStatBreakdownRow"):
            for stats in main_row.select(".summaryStatBreakdown"):
                if (
                    stats.select_one(".summaryStatBreakdownSubHeader")
                    .contents[0]
                    .strip()
                    == "KAST"
                ):
                    stats_data[
                        stats.select_one(".summaryStatBreakdownSubHeader")
                        .contents[0]
                        .strip()
                    ] = float(
                        stats.select_one(".summaryStatBreakdownDataValue").text.split(
                            "%"
                        )[0]
                    )
                elif (
                    stats.select_one(".summaryStatBreakdownSubHeader")
                    .contents[0]
                    .strip()
                    == "Impact"
                ):
                    stats_data[
                        stats.select_one(".summaryStatBreakdownSubHeader")
                        .contents[0]
                        .strip()
                    ] = float(stats.select_one(".summaryStatBreakdownDataValue").text)

        # Get player's shape
        shape = []
        shape_element = soup.select_one(".featured-ratings-container")
        for element in shape_element.select(".rating-value"):
            shape.append(float(element.text))

        # Fetching new page for more stats
        headers = {"User-Agent": config.USER_AGENT}
        response = requests.get(
            config.BASE_URL + "/stats/players/individual/" + str(player_id) + "/_",
            headers=headers,
        )
        body = response.text

        soup = BeautifulSoup(body, "html.parser")

        for stats_box in soup.select(".columns .standard-box"):
            for stats in stats_box.select(".stats-row"):
                # Just to avoid errors on specific data, using 3 span
                try:
                    stats_data[stats.select("span")[0].text.strip()] = float(
                        stats.select("span")[1].text.split("%")[0]
                    )
                except:
                    pass

        return jsonify(
            {
                "name": player_profile.select_one(".summaryNickname").text,
                "fullname": player_profile.select_one(".summaryRealname").text.strip(),
                "age": int(
                    re.findall(
                        r"\d+", player_profile.select_one(".summaryPlayerAge").text
                    )[0]
                ),
                "flag": config.BASE_URL + player_profile.select_one(".flag")["src"],
                "team": config.BASE_URL
                + player_profile.select_one(".SummaryTeamname").select_one("a")["href"],
                "stats": {
                    "rating": stats_data["Rating 1.0"],
                    "kast": stats_data["KAST"],
                    "impact": stats_data["Impact"],
                    "total_kills": stats_data["Total kills"],
                    "headshot_percentage": stats_data["Headshot %"],
                    "total_deaths": stats_data["Total deaths"],
                    "k/d_ratio": stats_data["K/D Ratio"],
                    "damage_per_round": stats_data["Damage / Round"],
                    "grenae_damage_per_round": stats_data["Grenade dmg / Round"],
                    "maps_played": stats_data["Maps played"],
                    "rounds_played": stats_data["Rounds played"],
                    "kills_per_round": stats_data["Kills / round"],
                    "assists_per_round": stats_data["Assists / round"],
                    "deaths_per_round": stats_data["Deaths / round"],
                    "saved_by_teammates": stats_data["Saved by teammate / round"],
                    "saved_teammates": stats_data["Saved teammates / round"],
                    "featured_rating": {
                        "vs_top_5": shape[0],
                        "vs_top_10": shape[1],
                        "vs_top_20": shape[2],
                        "vs_top_30": shape[3],
                        "vs_top_50": shape[4],
                    },
                    "rounds_stats": {
                        "0_kill_per_rounds": stats_data["0 kill rounds"],
                        "1_kill_per_rounds": stats_data["1 kill rounds"],
                        "2_kill_per_rounds": stats_data["2 kill rounds"],
                        "3_kill_per_rounds": stats_data["3 kill rounds"],
                        "4_kill_per_rounds": stats_data["4 kill rounds"],
                        "5_kill_per_rounds": stats_data["5 kill rounds"],
                    },
                    "opening_stats": {
                        "total_opening_kills": stats_data["Total opening kills"],
                        "total_opening_deaths": stats_data["Total opening deaths"],
                        "opening_kill_ratio": stats_data["Opening kill ratio"],
                        "opening_kill_rating": stats_data["Opening kill rating"],
                        "win_percentage_after_opening_kill": stats_data[
                            "Team win percent after first kill"
                        ],
                        "first_kill_won_per_round": stats_data[
                            "First kill in won rounds"
                        ],
                    },
                    "weapon_stats": {
                        "rifles": stats_data["Rifle kills"],
                        "snipers": stats_data["Sniper kills"],
                        "smgs": stats_data["SMG kills"],
                        "pistols": stats_data["Pistol kills"],
                        "nades": stats_data["Grenade"],
                        "other": stats_data["Other"],
                    },
                    "clutch_stats": {
                        "1v1": {
                            "wins": "",
                            "losses": "",
                        },
                        "1v2": {
                            "wins": "",
                            "losses": "",
                        },
                        "1v3": {
                            "wins": "",
                            "losses": "",
                        },
                        "1v4": {
                            "wins": "",
                            "losses": "",
                        },
                        "1v5": {
                            "wins": "",
                            "losses": "",
                        },
                    },
                },
            }
        )
    except Exception as e:
        raise e
        return jsonify({"status": "error", "message": str(e)}), 500


# Route for monitoring a container
@app.route("/health", methods=["GET"])
def healthcheck():
    return jsonify(
        {
            "state": "running",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
