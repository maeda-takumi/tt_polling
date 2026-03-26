from __future__ import annotations

from datetime import date, datetime, timedelta
import re
import time

import requests
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

GET_CALENDARS_API = "https://totalappworks.com/timetree/api/get_calendars.php"


def fetch_calendars_from_api() -> list[dict]:
    response = requests.get(GET_CALENDARS_API, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"calendars API error: {data}")
    return data.get("calendars", [])


def wait_for_day_ul(driver, date_str: str, timeout: int = 15):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f'ul[data-date="{date_str}"]'))
        )
    except TimeoutException:
        return None


def get_event_count(driver, date_str: str, max_retry: int = 3) -> int:
    for _ in range(max_retry):
        ul = wait_for_day_ul(driver, date_str)
        if ul is None:
            continue
        try:
            return len(ul.find_elements(By.XPATH, "./div"))
        except StaleElementReferenceException:
            time.sleep(0.2)
    return 0


def parse_title(title: str):
    actor = customer = sales = None
    match = re.match(r"^(.*?)[\(\（](.*?)[\)\）](.*)$", title)
    if match:
        actor = match.group(1).strip()
        customer = match.group(2).strip()
        sales = match.group(3).strip()
    else:
        actor = title.strip()
    return actor, customer, sales


def extract_event_by_index(driver, date_str: str, index: int, max_retry: int = 2):
    for _ in range(max_retry):
        try:
            ul = driver.find_element(By.CSS_SELECTOR, f'ul[data-date="{date_str}"]')
            divs = ul.find_elements(By.XPATH, "./div")
            if index >= len(divs):
                return None

            a_tag = divs[index].find_element(By.TAG_NAME, "a")
            h3 = a_tag.find_elements(By.TAG_NAME, "h3")
            title = h3[0].text.strip() if h3 else ""

            texts = [d.text.strip() for d in a_tag.find_elements(By.TAG_NAME, "div") if d.text.strip()]
            time_text = next((t for t in texts if "終日" in t or any(c.isdigit() for c in t)), "")
            lines = time_text.splitlines()
            start_time = lines[0] if len(lines) > 0 else ""
            end_time = lines[1] if len(lines) > 1 else ""
            detail = next((t for t in texts if t not in (start_time, end_time)), "")

            actor, customer, sales = parse_title(title)
            return {
                "title": title,
                "actor_name": actor,
                "customer_name": customer,
                "sales_name": sales,
                "start_time": start_time,
                "end_time": end_time,
                "detail": detail,
                "event_url": a_tag.get_attribute("href"),
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except (StaleElementReferenceException, NoSuchElementException):
            time.sleep(0.2)
    return None


def nudge_scroll(driver):
    driver.execute_script("window.scrollTo(0, 200);")
    time.sleep(0.2)
    driver.execute_script("window.scrollTo(0, 0);")


def generate_target_dates(start_date: date, days: int = 31) -> list[date]:
    return [start_date + timedelta(days=i) for i in range(days)]


def passes_keyword_filter(info: dict, keyword: str) -> bool:
    if not keyword:
        return True
    keyword = keyword.lower()
    text = f"{info.get('title', '')} {info.get('detail', '')}".lower()
    return keyword in text


def scrape_events(driver, start_date: date, keyword: str = "") -> list[dict]:
    events: list[dict] = []
    calendars = fetch_calendars_from_api()

    for cal in calendars:
        calendar_name = cal["name"]
        calendar_id = cal["timetree_calendar_id"]

        for target in generate_target_dates(start_date):
            date_str = target.isoformat()
            driver.get(f"https://timetreeapp.com/calendars/{calendar_id}/daily/{date_str}")
            nudge_scroll(driver)

            for i in range(get_event_count(driver, date_str)):
                info = extract_event_by_index(driver, date_str, i)
                if not info or not passes_keyword_filter(info, keyword):
                    continue
                info["calendar_id"] = calendar_id
                info["calendar_name"] = calendar_name
                info["date"] = date_str
                events.append(info)

    return events
