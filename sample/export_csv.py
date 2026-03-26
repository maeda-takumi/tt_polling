import argparse
from datetime import datetime, timedelta

from storage import DB_PATH, export_events_to_csv, get_connection, init_db


def parse_args():
    parser = argparse.ArgumentParser(description="Export CSV from SQLite")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD (default: start + 30 days)")
    parser.add_argument("--keyword", default="", help="keyword filter")
    parser.add_argument("--db-path", default=str(DB_PATH), help="SQLite db path")
    parser.add_argument("--output", required=True, help="CSV output path")
    return parser.parse_args()


def main():
    args = parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else start + timedelta(days=30)

    with get_connection(args.db_path) as conn:
        init_db(conn)
        count = export_events_to_csv(
            conn=conn,
            output_path=args.output,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            keyword=args.keyword,
        )
    print(f"exported {count} events to {args.output}")


if __name__ == "__main__":
    main()
