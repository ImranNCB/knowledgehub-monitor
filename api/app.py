import os

from dot env import load_dotenv

from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)
load_dotenv()
API_KEY = os.getenv("API_KEY")

SUPPORTED_METRICS = ["cpu", "memory", "disk"]


@app.get("/api/v1/health")
def health():
    return jsonify({
        "status": "healthy"
    }), 200


@app.post("/api/v1/measurements")
def create_measurement():
    if not API_KEY or request.headers.get("X-API-Key") != API_KEY:
        return jsonify({
            "error": "Unauthorized"
        }), 401
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must contain valid JSON"
        }), 400

    required_fields = [
        "timestamp",
        "hostname",
        "ip_address",
        "metric",
        "value",
        "unit"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    try:
        datetime.fromisoformat(data["timestamp"])
    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid timestamp"
        }), 400

    if data["metric"] not in SUPPORTED_METRICS:
        return jsonify({
            "error": "Unsupported metric"
        }), 400

    if (
        isinstance(data["value"], bool)
        or not isinstance(data["value"], (int, float))
    ):
        return jsonify({
            "error": "Value must be a number"
        }), 400

    if not 0 <= data["value"] <= 100:
        return jsonify({
            "error": "Value must be between 0 and 100"
        }), 400

    return jsonify({
        "message": "Measurement accepted",
        "measurement": data
    }), 201


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )