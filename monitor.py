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
        help="Record system metrics in SQLite and send them to Azure",
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
