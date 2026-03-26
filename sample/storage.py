import csv
import sqlite3
from pathlib import Path
from typing import Iterable

DB_PATH = Path("events.db")


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS timetree_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendar_id TEXT NOT NULL,
            calendar_name TEXT NOT NULL,
            event_date TEXT NOT NULL,
            title TEXT NOT NULL,
            actor_name TEXT,
            customer_name TEXT,
            sales_name TEXT,
            start_time TEXT,
            end_time TEXT,
            detail TEXT,
            event_url TEXT,
            scraped_at TEXT NOT NULL,
            UNIQUE(calendar_id, event_date, title, start_time, end_time, event_url)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timetree_events_date ON timetree_events(event_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timetree_events_title ON timetree_events(title)")
    conn.commit()


def save_events(conn: sqlite3.Connection, events: Iterable[dict]) -> int:
    records = [
        (
            e.get("calendar_id", ""),
            e.get("calendar_name", ""),
            e.get("date", ""),
            e.get("title", ""),
            e.get("actor_name"),
            e.get("customer_name"),
            e.get("sales_name"),
            e.get("start_time", ""),
            e.get("end_time", ""),
            e.get("detail", ""),
            e.get("event_url", ""),
            e.get("scraped_at", ""),
        )
        for e in events
    ]
    if not records:
        return 0
    cur = conn.executemany(
        """
        INSERT OR REPLACE INTO timetree_events(
            calendar_id, calendar_name, event_date, title,
            actor_name, customer_name, sales_name,
            start_time, end_time, detail, event_url, scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    conn.commit()
    return cur.rowcount


def export_events_to_csv(
    conn: sqlite3.Connection,
    output_path: str | Path,
    start_date: str,
    end_date: str,
    keyword: str = "",
) -> int:
    sql = """
        SELECT
            calendar_id, calendar_name, event_date, title,
            actor_name, customer_name, sales_name,
            start_time, end_time, detail, event_url, scraped_at
        FROM timetree_events
        WHERE event_date BETWEEN ? AND ?
    """
    params = [start_date, end_date]
    if keyword:
        sql += " AND (title LIKE ? OR detail LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    sql += " ORDER BY event_date ASC, calendar_name ASC, start_time ASC"

    rows = conn.execute(sql, params).fetchall()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "calendar_id", "calendar_name", "event_date", "title",
                "actor_name", "customer_name", "sales_name",
                "start_time", "end_time", "detail", "event_url", "scraped_at",
            ]
        )
        for row in rows:
            writer.writerow([row[key] for key in row.keys()])
    return len(rows)
