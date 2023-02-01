import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, jsonify

import config

# Create Instance of Flask Server
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "changeme")


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
