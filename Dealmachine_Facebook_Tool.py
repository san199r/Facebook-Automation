# ======================================================
# Jenkins-safe Facebook Followers Full Data Extractor
# With Total Followers Count + Continuous Scrolling
# ======================================================

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import time
import re
import random
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from webdriver_manager.chrome import ChromeDriverManager


# ======================================================
# CONFIG
# ======================================================
FOLLOWERS_URL = "https://www.facebook.com/dealmachineapp/followers/"
MAX_FOLLOWERS = 200   # target number (best effort)

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

OUTPUT_DIR = os.path.join(os.getcwd(), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_XLSX = os.path.join(OUTPUT_DIR, f"facebook_full_contact_data_{timestamp}.xlsx")


# ======================================================
# DRIVER SETUP (HEADLESS)
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
# READ TOTAL FOLLOWERS COUNT
# ======================================================
def get_total_followers_text(driver):
    time.sleep(4)
    spans = driver.find_elements(By.XPATH, "//span")

    for span in spans:
        text = span.text.lower().strip()
        if "follower" in text:
            return text

    return "Unknown"


def normalize_follower_count(text):
    try:
        text = text.replace("followers", "").strip()
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        if "m" in text:
            return int(float(text.replace("m", "")) * 1_000_000)
        return int(text.replace(",", ""))
    except:
        return None


# ======================================================
# EXTRACT CONTACT DETAILS (BEST EFFORT)
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

    time.sleep(3)

    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        try:
            href = link.get_attribute("href")
            if not href:
                continue

            href_l = href.lower()
            if "linkedin.com" in href_l:
                details["External LinkedIn"] = href
            elif "instagram.com" in href_l:
                details["External Instagram"] = href
            elif href.startswith("http") and details["Website"] == "":
                details["Website"] = href

        except StaleElementReferenceException:
            continue

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
# COLLECT ALL FOLLOWERS (ROBUST SCROLLING)
# ======================================================
def collect_all_followers(driver, max_followers):
    print("Opening followers page...")
    driver.get(FOLLOWERS_URL)
    time.sleep(8)

    followers_text = get_total_followers_text(driver)
    est_count = normalize_follower_count(followers_text)

    print(f"Followers shown by Facebook: {followers_text}")
    if est_count:
        print(f"Estimated followers count: {est_count}")

    collected = []
    seen = set()

    no_new_attempts = 0
    MAX_NO_NEW = 5

    while len(collected) < max_followers and no_new_attempts < MAX_NO_NEW:
        elements = driver.find_elements(By.XPATH, "//a[contains(@href,'/people/')]")
        new_found = 0

        for el in elements:
            try:
                name = el.text.strip()
                href = el.get_attribute("href")

                if name and href and href not in seen:
                    seen.add(href)
                    collected.append((name, href))
                    new_found += 1
                    print(f"Collected {len(collected)}: {name}")

                    if len(collected) >= max_followers:
                        break

            except StaleElementReferenceException:
                continue

        if new_found == 0:
            no_new_attempts += 1
            print(f"No new followers found (attempt {no_new_attempts}/{MAX_NO_NEW})")
        else:
            no_new_attempts = 0

        driver.execute_script(
            "window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});"
        )
        time.sleep(random.uniform(4, 6))

    print(f"Total followers collected: {len(collected)}")
    return collected


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
    print(f"Excel saved at: {os.path.abspath(OUT_XLSX)}")


# ======================================================
# MAIN
# ======================================================
def main():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)
        followers = collect_all_followers(driver, MAX_FOLLOWERS)

        final_data = []
        for name, profile_url in followers:
            print(f"Extracting details for: {name}")
            driver.get(profile_url)
            time.sleep(5)

            details = extract_contact_details(driver)
            final_data.append([
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

            time.sleep(random.uniform(3, 5))

        if final_data:
            save_to_excel(final_data)
        else:
            print("No data extracted.")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
