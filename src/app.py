import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from flask import Flask, jsonify

import config

# Create Instance of Flask Server
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "changeme")

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
                    "fullname": player.select_one("img")["title"],
                    "image": player.select_one("img")["src"],
                    "nickname": player["title"],
                    "country": {"name": country_name, "flag": country_flag}
                    if country_name
                    else None,
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
                    "ranking": ranking,
                    "coach": coach,
                    "average_player_age": average_player_age,
                    "players": players,
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
