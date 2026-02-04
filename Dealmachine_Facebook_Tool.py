# =========================================
# Jenkins-safe Facebook Followers Scraper
# Headless Chrome Enabled
# =========================================

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import time

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager


# =========================================
# CONFIG
# =========================================
FOLLOWERS_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_dealmachine_followers.xlsx"
MAX_FOLLOWERS = 20   # increase if needed


# =========================================
# SETUP DRIVER (HEADLESS)
# =========================================
def setup_driver():
    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 25)
    return driver, wait


# =========================================
# FACEBOOK LOGIN
# =========================================
def facebook_login(driver, wait):
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        print("WARNING: FB_USERNAME or FB_PASSWORD not set.")
        return

    print(f"Logging in as: {username}")

    driver.get("https://www.facebook.com/login")
    time.sleep(5)

    email = wait.until(EC.presence_of_element_located((By.ID, "email")))
    passwd = wait.until(EC.presence_of_element_located((By.ID, "pass")))

    email.clear()
    email.send_keys(username)

    passwd.clear()
    passwd.send_keys(password)
    passwd.send_keys(Keys.ENTER)

    time.sleep(10)
    print("Login completed.")


# =========================================
# EXTRACT FOLLOWERS
# =========================================
def extract_followers(driver, limit):
    print("Opening followers page...")
    driver.get(FOLLOWERS_URL)
    time.sleep(8)

    followers = []
    seen = set()

    last_height = driver.execute_script("return document.body.scrollHeight")

    while len(followers) < limit:
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'facebook.com')]")

        for link in links:
            name = link.text.strip()
            href = link.get_attribute("href")

            if not name or not href:
                continue

            if "/people/" in href and href not in seen:
                seen.add(href)
                followers.append((name, href))

                if len(followers) >= limit:
                    break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    print(f"Collected {len(followers)} followers.")
    return followers


# =========================================
# SAVE TO EXCEL
# =========================================
def save_to_excel(data):
    print("Saving followers to Excel...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Followers"

    headers = ["S.No", "Name", "Profile URL"]
    bold = Font(bold=True)

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = bold

    for idx, (name, url) in enumerate(data, start=1):
        ws.cell(row=idx + 1, column=1, value=idx)
        ws.cell(row=idx + 1, column=2, value=name)
        ws.cell(row=idx + 1, column=3, value=url)

    wb.save(OUT_XLSX)
    print(f"Excel saved: {OUT_XLSX}")


# =========================================
# MAIN
# =========================================
def main():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)
        followers = extract_followers(driver, MAX_FOLLOWERS)

        if followers:
            save_to_excel(followers)
        else:
            print("No followers found.")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
