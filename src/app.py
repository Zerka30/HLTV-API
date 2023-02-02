import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from flask import Flask, jsonify

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
                "date": match.select_one(".matchTime").get("data-unix"),
                "match_url": config.BASE_URL + match.select_one("a")["href"],
                "type": match.select_one(".matchMeta").text,
                "opponent": opponent,
                "tournament": {
                    "name": match.select_one(".matchEvent .matchEventName").text,
                    "logo": match.select_one(".matchEvent .matchEventLogo")["src"],
                },
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
                    "result": result,
                    "score": score,
                    "opponent": opponent,
                    "tournament": {
                        "name": match.select_one(".event-name").text,
                        "logo": match.select_one(".event-logo")["src"],
                    },
                    "type": match.select_one(".map-text").text,
                    "match_url": match["href"],
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

            players.append(
                {
                    "id": player["href"].split("/")[2],
                    "fullname": player.select_one("img")["title"],
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

        return (
            jsonify(
                {
                    "id": team_id,
                    "name": name,
                    "logo": logo,
                    "social_media": social,
                    "ranking": ranking,
                    "average_player_age": average_player_age,
                    "coach": coach,
                    "players": players,
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
@app.route("/team/<string:team_id>/upcomming", methods=["GET"])
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


# Route to get player id by nickname
@app.route("/player/<string:player_nickname>", methods=["GET"])
def get_player_id(player_nickname):
    try:
        headers = {"User-Agent": config.USER_AGENT}
        res = requests.get(
            config.BASE_URL + "search?term=" + player_nickname, headers=headers
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
                    "hltvUrl": config.BASE_URL + res["location"],
                    "team": {
                        "name": res["team"]["name"],
                        "logo": res["team"]["teamLogoDay"],
                        "hltvUrl": config.BASE_URL + res["team"]["location"],
                    },
                }
            ),
            200,
        )
    except Exception as e:
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
