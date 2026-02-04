# =========================
# Jenkins-safe Facebook Scraper
# =========================

import sys
# Ensure UTF-8 output (still avoid emojis in logs)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import os
import time
import re

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager


# =========================
# CONFIG
# =========================
START_URL = "https://www.facebook.com/dealmachineapp/"
OUT_XLSX = "facebook_dealmachine_results.xlsx"

HEADERS = [
    "S.No",
    "Facebook Name",
    "Profile URL"
]


# =========================
# UTILITIES
# =========================
def setup_driver():
    options = webdriver.ChromeOptions()

    # Jenkins-friendly options
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")

    # Uncomment if Jenkins runs without desktop
    # options.add_argument("--headless=new")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 20)
    return driver, wait


def facebook_login(driver, wait):
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        print("WARNING: FB_USERNAME or FB_PASSWORD not set in environment.")
        print("Skipping login.")
        return

    print(f"Logging in as: {username}")

    driver.get("https://www.facebook.com/login")

    email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
    pass_input = wait.until(EC.presence_of_element_located((By.ID, "pass")))

    email_input.clear()
    email_input.send_keys(username)

    pass_input.clear()
    pass_input.send_keys(password)
    pass_input.send_keys(Keys.ENTER)

    # Wait for login to complete
    time.sleep(8)
    print("Login attempt completed.")


def extract_profiles(driver, wait, limit=20):
    print("Opening target page...")
    driver.get(START_URL)
    time.sleep(8)

    results = []
    seen = set()

    print("Collecting profile links...")

    anchors = driver.find_elements(By.TAG_NAME, "a")

    for a in anchors:
        href = a.get_attribute("href")
        text = a.text.strip()

        if not href or not text:
            continue

        if "facebook.com" in href and "profile" in href or "/people/" in href:
            if href in seen:
                continue

            seen.add(href)
            results.append((text, href))

            if len(results) >= limit:
                break

    print(f"Collected {len(results)} profiles.")
    return results


def save_to_excel(data):
    print("Saving data to Excel...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Facebook Data"

    header_font = Font(bold=True)

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font

    for idx, (name, url) in enumerate(data, start=1):
        ws.cell(row=idx + 1, column=1, value=idx)
        ws.cell(row=idx + 1, column=2, value=name)
        ws.cell(row=idx + 1, column=3, value=url)

    wb.save(OUT_XLSX)
    print(f"Excel file saved: {OUT_XLSX}")


# =========================
# MAIN FLOW
# =========================
def facebook_dealmachine_scraper():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)
        profiles = extract_profiles(driver, wait, limit=20)

        if profiles:
            save_to_excel(profiles)
        else:
            print("No profiles found.")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    facebook_dealmachine_scraper()
