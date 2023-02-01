import os
import requests
import xml.etree.ElementTree as ET
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
