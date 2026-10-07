import argparse
import csv
from datetime import datetime
from pathlib import Path

import psutil


DATA_FILE = Path(__file__).with_name("measurements.csv")
SUPPORTED_METRICS = ["cpu", "memory", "disk"]


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
    """Measure metrics and append them to CSV storage."""
    file_exists = DATA_FILE.exists()

    fieldnames = [
        "timestamp",
        "hostname",
        "ip_address",
        "metric",
        "value",
        "unit",
    ]

    with DATA_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for metric in metrics:
            value, unit = measure_metric(metric)
            timestamp = datetime.now().isoformat(timespec="seconds")

            writer.writerow(
                {
                    "timestamp": timestamp,
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                }
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
    if not DATA_FILE.exists():
        print("No measurements have been recorded yet.")
        return

    with DATA_FILE.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        print(
            f"{'Timestamp':<20} "
            f"{'Host':<12} "
            f"{'Metric':<10} "
            f"{'Value':<10}"
        )
        print("-" * 55)

        for row in reader:
            timestamp = datetime.fromisoformat(row["timestamp"])

            if start and timestamp < start:
                continue

            if end and timestamp > end:
                continue

            print(
                f"{row['timestamp']:<20} "
                f"{row['hostname']:<12} "
                f"{row['metric']:<10} "
                f"{row['value']}{row['unit']}"
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
        help="Record system metrics",
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


if __name__ == "__main__":
    main()
