import os

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


def login(driver, wait):
    # email = os.getenv("TIMETREE_EMAIL")
    # password = os.getenv("TIMETREE_PASSWORD")
    email = "jiangqiantian54@gmail.com"
    password = "maedamaeda0612"

    if not email or not password:
        raise RuntimeError("環境変数 TIMETREE_EMAIL / TIMETREE_PASSWORD を設定してください")

    driver.get("https://timetreeapp.com/signin")

    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.clear()
    email_input.send_keys(email)

    password_input = driver.find_element(By.NAME, "password")
    password_input.clear()
    password_input.send_keys(password)
    password_input.send_keys(Keys.ENTER)

    wait.until(EC.url_contains("/calendar"))
