from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Callable, Iterable


def _normalize_event_date(value: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    return value


def sync_event_dates_to_sheet(
    *,
    spreadsheet_id: str,
    sheet_name: str,
    credentials_path: str | Path,
    rows: Iterable[dict],
    scraped_on: date | None = None,
    logger: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """スクレイピング結果の customer_name ごとに event_date をスプシへ書き込む。"""

    def log(message: str):
        if logger:
            logger(message)

    customers_to_dates: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        customer_name = (row.get("customer_name") or "").strip()
        event_date_raw = row.get("event_date") or row.get("date") or ""
        event_date = _normalize_event_date(str(event_date_raw))
        if not customer_name or not event_date:
            continue
        customers_to_dates[customer_name].add(event_date)
    summary = {
        "prepared": len(customers_to_dates),
        "updated": 0,
        "skipped_not_found": 0,
        "skipped_duplicate_sheet": 0,
        "skipped_ambiguous_event_date": 0,
    }

    if not customers_to_dates:
        log("スプシ同期: 対象データがないためスキップ")
        return summary

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except Exception as exc:
        raise RuntimeError(
            "Google Sheets連携に必要なライブラリが不足しています。"
            " `pip install google-api-python-client google-auth` を実行してください。"
        ) from exc

    credentials_file = Path(credentials_path)
    if not credentials_file.exists():
        raise FileNotFoundError(f"credentials.json が見つかりません: {credentials_file}")

    credentials = Credentials.from_service_account_file(
        str(credentials_file),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=credentials)

    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!B:B")
        .execute()
    )
    sheet_values = response.get("values", [])

    name_to_rows: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(sheet_values, start=1):
        if not row:
            continue
        value = str(row[0]).strip()
        if not value:
            continue
        name_to_rows[value].append(idx)

    updates: list[dict] = []
    for customer_name, date_values in customers_to_dates.items():
        if len(date_values) > 1:
            summary["skipped_ambiguous_event_date"] += 1
            log(
                "スプシ同期スキップ: customer_name='"
                f"{customer_name}' は event_date が複数あるため更新しません ({sorted(date_values)})"
            )
            continue

        rows_found = name_to_rows.get(customer_name, [])
        if not rows_found:
            summary["skipped_not_found"] += 1
            log(f"スプシ同期スキップ: customer_name='{customer_name}' がシートB列に見つかりません")
            continue

        if len(rows_found) > 1:
            summary["skipped_duplicate_sheet"] += 1
            log(
                "スプシ同期スキップ: customer_name='"
                f"{customer_name}' がシートB列で重複しているため更新しません (rows={rows_found})"
            )
            continue

        row_number = rows_found[0]
        date_value = next(iter(date_values))
        updates.append(
            {
                "range": f"{sheet_name}!AH{row_number}",
                "values": [[date_value]],
            }
        )

    if updates:
        (
            service.spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "valueInputOption": "RAW",
                    "data": updates,
                },
            )
            .execute()
        )

    summary["updated"] = len(updates)
    log(
        "スプシ同期完了: "
        f"updated={summary['updated']}, "
        f"not_found={summary['skipped_not_found']}, "
        f"duplicate_sheet={summary['skipped_duplicate_sheet']}, "
        f"ambiguous_event_date={summary['skipped_ambiguous_event_date']}"
    )
    return summary
