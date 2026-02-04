# ======================================================
# Jenkins-safe Facebook Followers Full Data Extractor
# ======================================================

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
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


# ======================================================
# CONFIG
# ======================================================
FOLLOWERS_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_full_contact_data.xlsx"
MAX_FOLLOWERS = 10   # increase slowly to avoid blocks


HEADERS = [
    "S.No",
    "Facebook Name",
    "Facebook Page URL",
    "Location",
    "Phone",
    "Email",
    "Website",
    "External Facebook",
    "External LinkedIn",
    "External Instagram",
]


# ======================================================
# SETUP DRIVER (HEADLESS)
# ======================================================
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


# ======================================================
# FACEBOOK LOGIN
# ======================================================
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


# ======================================================
# EXTRACT CONTACT DETAILS FROM PROFILE
# ======================================================
def extract_contact_details(driver):
    details = {
        "Location": "",
        "Phone": "",
        "Email": "",
        "Website": "",
        "External Facebook": "",
        "External LinkedIn": "",
        "External Instagram": ""
    }

    time.sleep(4)

    # Extract links
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href")
        if not href:
            continue

        href_l = href.lower()

        if "linkedin.com" in href_l:
            details["External LinkedIn"] = href
        elif "instagram.com" in href_l:
            details["External Instagram"] = href
        elif "facebook.com" in href_l and details["External Facebook"] == "":
            details["External Facebook"] = href
        elif href.startswith("http") and details["Website"] == "":
            details["Website"] = href

    # Extract text-based info (best-effort)
    page_text = driver.page_source.lower()

    phone_match = re.search(r"\+?\d[\d\s\-]{8,}", page_text)
    if phone_match:
        details["Phone"] = phone_match.group()

    email_match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", page_text
    )
    if email_match:
        details["Email"] = email_match.group()

    return details


# ======================================================
# EXTRACT FOLLOWERS + DETAILS
# ======================================================
def extract_followers_with_details(driver, limit):
    print("Opening followers page...")
    driver.get(FOLLOWERS_URL)
    time.sleep(8)

    data = []
    seen = set()

    follower_links = driver.find_elements(By.XPATH, "//a[contains(@href,'/people/')]")

    for link in follower_links:
        name = link.text.strip()
        profile_url = link.get_attribute("href")

        if not name or not profile_url or profile_url in seen:
            continue

        seen.add(profile_url)
        print(f"Processing profile: {name}")

        driver.get(profile_url)
        time.sleep(6)

        details = extract_contact_details(driver)

        data.append([
            name,
            profile_url,
            details["Location"],
            details["Phone"],
            details["Email"],
            details["Website"],
            profile_url,
            details["External LinkedIn"],
            details["External Instagram"],
        ])

        if len(data) >= limit:
            break

        time.sleep(3)  # slow down to avoid blocks

    print(f"Collected {len(data)} profiles.")
    return data


# ======================================================
# SAVE TO EXCEL
# ======================================================
def save_to_excel(data):
    wb = Workbook()
    ws = wb.active
    ws.title = "Facebook Data"

    bold = Font(bold=True)

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = bold

    for idx, row in enumerate(data, start=1):
        ws.cell(row=idx + 1, column=1, value=idx)
        for col, value in enumerate(row, start=2):
            ws.cell(row=idx + 1, column=col, value=value)

    wb.save(OUT_XLSX)
    print(f"Excel saved: {OUT_XLSX}")


# ======================================================
# MAIN
# ======================================================
def main():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)
        data = extract_followers_with_details(driver, MAX_FOLLOWERS)

        if data:
            save_to_excel(data)
        else:
            print("No data extracted.")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
