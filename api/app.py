import logging
import os
from datetime import datetime

import pyodbc
from dotenv import load_dotenv
from flask import Flask, jsonify, request


load_dotenv()

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)


API_KEY = os.getenv("API_KEY")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SUPPORTED_METRICS = ["cpu", "memory", "disk"]


def get_database_connection():
    required_settings = [
        DB_HOST,
        DB_NAME,
        DB_USER,
        DB_PASSWORD
    ]

    if not all(required_settings):
        raise RuntimeError(
            "Database configuration is incomplete"
        )

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{DB_HOST},1433;"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(connection_string)


def valid_api_key():
    return (
        API_KEY
        and request.headers.get("X-API-Key") == API_KEY
    )


@app.get("/api/v1/health")
def health():
    return jsonify({
        "status": "healthy"
    }), 200


@app.post("/api/v1/measurements")
def create_measurement():
    if not valid_api_key():
        logger.warning(
            "Unauthorized request to %s",
            request.path
        )

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

    try:
        with get_database_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO dbo.measurements (
                    [timestamp],
                    hostname,
                    ip_address,
                    metric,
                    value,
                    unit
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                data["timestamp"],
                data["hostname"],
                data["ip_address"],
                data["metric"],
                data["value"],
                data["unit"]
            )

            connection.commit()

    except Exception:
        logger.exception(
            "Database insert failed"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    logger.info(
        "Measurement stored: host=%s metric=%s",
        data["hostname"],
        data["metric"]
    )

    return jsonify({
        "message": "Measurement stored"
    }), 201


@app.get("/api/v1/measurements/latest")
def get_latest_measurement():
    if not valid_api_key():
        logger.warning(
            "Unauthorized request to %s",
            request.path
        )

        return jsonify({
            "error": "Unauthorized"
        }), 401

    try:
        with get_database_connection() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT TOP 1
                    id,
                    [timestamp],
                    hostname,
                    ip_address,
                    metric,
                    value,
                    unit,
                    created_at
                FROM dbo.measurements
                ORDER BY id DESC
                """
            )

            row = cursor.fetchone()

    except Exception:
        logger.exception(
            "Database query failed"
        )

        return jsonify({
            "error": "Database error"
        }), 500

    if row is None:
        return jsonify({
            "error": "No measurements available"
        }), 404

    return jsonify({
        "measurement": {
            "id": row.id,
            "timestamp": row.timestamp.isoformat(),
            "hostname": row.hostname,
            "ip_address": row.ip_address,
            "metric": row.metric,
            "value": row.value,
            "unit": row.unit,
            "created_at": row.created_at.isoformat()
        }
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )