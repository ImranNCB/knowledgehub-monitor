import argparse
import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv


DB_FILE = Path(__file__).with_name("monitoring.db")
CSV_FILE = Path(__file__).with_name("measurements.csv")
SUPPORTED_METRICS = ["cpu", "memory", "disk"]

load_dotenv(Path(__file__).parent / "api" / ".env")

API_URL = os.getenv(
    "MONITOR_API_URL",
    "https://app-kh-monitoring-imran.azurewebsites.net/api/v1/measurements",
)

API_KEY = os.getenv("API_KEY")


def initialize_database():
    """Create the local SQLite database and measurements table."""
    with sqlite3.connect(DB_FILE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hostname TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL
            )
            """
        )


def measure_metric(metric):
    """Measure one supported system metric."""
    if metric == "cpu":
        return psutil.cpu_percent(interval=1), "%"

    if metric == "memory":
        return psutil.virtual_memory().percent, "%"

    if metric == "disk":
        return psutil.disk_usage("/").percent, "%"

    raise ValueError(f"Unsupported metric: {metric}")


def send_measurement_to_api(measurement):
    """Send one measurement to the Azure API without breaking local storage."""
    if not API_KEY:
        print("Azure API skipped: API_KEY is not configured.")
        return False

    try:
        response = requests.post(
            API_URL,
            headers={"X-API-Key": API_KEY},
            json=measurement,
            timeout=10,
        )
    except requests.RequestException as error:
        print(f"Azure API unavailable: {error}")
        return False

    if response.status_code == 201:
        print(
            "Azure API: measurement stored "
            f"({measurement['metric']})."
        )
        return True

    try:
        error_body = response.json()
    except ValueError:
        error_body = response.text

    print(
        "Azure API rejected measurement: "
        f"HTTP {response.status_code} - {error_body}"
    )
    return False


def save_measurements(hostname, ip_address, metrics):
    """Measure metrics, store them locally, then send them to Azure."""
    initialize_database()

    with sqlite3.connect(DB_FILE) as connection:
        for metric in metrics:
            value, unit = measure_metric(metric)
            timestamp = datetime.now().isoformat(timespec="seconds")

            measurement = {
                "timestamp": timestamp,
                "hostname": hostname,
                "ip_address": ip_address,
                "metric": metric,
                "value": value,
                "unit": unit,
            }

            connection.execute(
                """
                INSERT INTO measurements (
                    timestamp,
                    hostname,
                    ip_address,
                    metric,
                    value,
                    unit
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    measurement["timestamp"],
                    measurement["hostname"],
                    measurement["ip_address"],