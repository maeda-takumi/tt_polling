import argparse
from datetime import datetime

from selenium.webdriver.support.ui import WebDriverWait

from auth import login
from browser import create_driver
from scraper import scrape_events
from storage import DB_PATH, get_connection, init_db, save_events


def parse_args():
    parser = argparse.ArgumentParser(description="TimeTree scraping (31 days)")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--keyword", default="", help="Filter by keyword")
    parser.add_argument("--db-path", default=str(DB_PATH), help="SQLite db path")
    return parser.parse_args()


def main():
    args = parse_args()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()

    driver = create_driver()
    try:
        login(driver, WebDriverWait(driver, 20))
        events = scrape_events(driver, start_date=start_date, keyword=args.keyword)
    finally:
        driver.quit()

    with get_connection(args.db_path) as conn:
        init_db(conn)
        count = save_events(conn, events)

    print(f"saved {count} events into {args.db_path}")


if __name__ == "__main__":
    main()
