import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

import psutil


DB_FILE = Path(__file__).with_name("monitoring.db")
CSV_FILE = Path(__file__).with_name("measurements.csv")
SUPPORTED_METRICS = ["cpu", "memory", "disk"]


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


def save_measurements(hostname, ip_address, metrics):
    """Measure system metrics and store them in SQLite."""
    initialize_database()

    with sqlite3.connect(DB_FILE) as connection:
        for metric in metrics:
            value, unit = measure_metric(metric)
            timestamp = datetime.now().isoformat(timespec="seconds")

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
                    timestamp,
                    hostname,
                    ip_address,
                    metric,
                    value,
                    unit,
                ),
            )

            print(
                f"{timestamp} | "
                f"{hostname} | "
                f"{metric}: {value}{unit}"
            )


def parse_datetime(value):
    """Convert an ISO formatted string into a datetime."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Use format YYYY-MM-DDTHH:MM:SS"
        ) from error


def show_measurements(start=None, end=None):
    """Display stored measurements, optionally filtered by time."""
    initialize_database()

    query = """
        SELECT timestamp, hostname, metric, value, unit
        FROM measurements
    """

    conditions = []
    parameters = []

    if start:
        conditions.append("timestamp >= ?")
        parameters.append(start.isoformat(timespec="seconds"))

    if end:
        conditions.append("timestamp <= ?")
        parameters.append(end.isoformat(timespec="seconds"))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp, id"

    with sqlite3.connect(DB_FILE) as connection:
        rows = connection.execute(query, parameters).fetchall()

    if not rows:
        print("No measurements found.")
        return

    print(
        f"{'Timestamp':<20} "
        f"{'Host':<12} "
        f"{'Metric':<10} "
        f"{'Value':<10}"
    )
    print("-" * 55)

    for timestamp, hostname, metric, value, unit in rows:
        print(
            f"{timestamp:<20} "
            f"{hostname:<12} "
            f"{metric:<10} "
            f"{value}{unit}"
        )


def migrate_csv():
    """Import existing Task 10 CSV measurements into SQLite."""
    if not CSV_FILE.exists():
        print("No measurements.csv file found.")
        return

    initialize_database()
    imported = 0

    with CSV_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        with sqlite3.connect(DB_FILE) as connection:
            for row in reader:
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
                        row["timestamp"],
                        row["hostname"],
                        row["ip_address"],
                        row["metric"],
                        float(row["value"]),
                        row["unit"],
                    ),
                )
                imported += 1

    print(
        f"Imported {imported} measurements "
        f"into {DB_FILE.name}."
    )


def build_parser():
    """Create command-line arguments."""
    parser = argparse.ArgumentParser(
        description="KnowledgeHub monitoring application"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    measure_parser = subparsers.add_parser(
        "measure",
        help="Record system metrics in SQLite",
    )

    measure_parser.add_argument(
        "--hostname",
        required=True,
    )

    measure_parser.add_argument(
        "--ip",
        required=True,
    )

    measure_parser.add_argument(
        "--metrics",
        nargs="+",
        required=True,
        choices=SUPPORTED_METRICS,
    )

    show_parser = subparsers.add_parser(
        "show",
        help="Display stored measurements",
    )

    show_parser.add_argument(
        "--start",
        type=parse_datetime,
    )

    show_parser.add_argument(
        "--end",
        type=parse_datetime,
    )

    subparsers.add_parser(
        "migrate-csv",
        help="Import Task 10 CSV data into SQLite",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "measure":
        save_measurements(
            args.hostname,
            args.ip,
            args.metrics,
        )

    elif args.command == "show":
        show_measurements(
            args.start,
            args.end,
        )

    elif args.command == "migrate-csv":
        migrate_csv()


if __name__ == "__main__":
    main()
