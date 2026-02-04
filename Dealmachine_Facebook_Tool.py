# ======================================================
# Facebook Followers Scraper (RESUME + SCREENSHOTS)
# Jenkins-safe | Container Scroll | No Duplicates
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

from openpyxl import Workbook, load_workbook
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
MAX_FOLLOWERS_PER_RUN = 50
MAX_NO_NEW = 15

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
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

OUT_XLSX = os.path.join(OUTPUT_DIR, "facebook_full_contact_data.xlsx")


# ======================================================
# DRIVER SETUP
# ======================================================
def setup_driver():
    options = webdriver.ChromeOptions()

    # Comment next line if you want non-headless
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
# FACEBOOK LOGIN + SCREENSHOT
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

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    login_shot = os.path.join(
        SCREENSHOT_DIR, f"after_login_{ts}.png"
    )
    driver.save_screenshot(login_shot)

    print("Login completed.")
    print(f"Login screenshot saved at: {os.path.abspath(login_shot)}")


# ======================================================
# LOAD EXISTING PROFILES (RESUME)
# ======================================================
def load_existing_profiles():
    existing = set()

    if not os.path.exists(OUT_XLSX):
        return existing

    wb = load_workbook(OUT_XLSX)
    ws = wb.active

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and len(row) > 2 and row[2]:
            existing.add(row[2])

    print(f"Resuming: {len(existing)} profiles already scraped")
    return existing


# ======================================================
# FILTER VALID FOLLOWERS
# ======================================================
def is_valid_follower(name, url):
    if not name or not url:
        return False

    name_l = name.lower()
    url_l = url.lower()

    blocked = [
        "followers",
        "following",
        "forgotten",
        "account",
        "log in",
        "sign up",
    ]

    for b in blocked:
        if b in name_l:
            return False

    if "facebook.com" not in url_l:
        return False

    if url_l.endswith("#"):
        return False

    if len(name.strip()) < 3:
        return False

    return True


# ======================================================
# SCROLL FOLLOWERS CONTAINER
# ======================================================
def scroll_followers_container(driver):
    try:
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        if dialogs:
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                dialogs[0]
            )
            return True
    except Exception:
        pass
    return False


# ======================================================
# COLLECT FOLLOWERS (RESUME SAFE)
# ======================================================
def collect_followers(driver, existing_profiles):
    print("Opening followers page...")
    driver.get(FOLLOWERS_URL)
    time.sleep(8)

    collected = []
    seen = set()
    no_new = 0

    while len(collected) < MAX_FOLLOWERS_PER_RUN and no_new < MAX_NO_NEW:
        elements = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'facebook.com') and @role='link']"
        )

        new_found = 0

        for el in elements:
            try:
                name = el.text.strip()
                href = el.get_attribute("href")

                if (
                    is_valid_follower(name, href)
                    and href not in seen
                    and href not in existing_profiles
                ):
                    seen.add(href)
                    collected.append((name, href))
                    new_found += 1
                    print(f"Collected {len(collected)}: {name}")

                    if len(collected) >= MAX_FOLLOWERS_PER_RUN:
                        break

            except StaleElementReferenceException:
                continue

        if new_found == 0:
            no_new += 1
            print(f"No new followers found ({no_new}/{MAX_NO_NEW})")
        else:
            no_new = 0

        scrolled = scroll_followers_container(driver)
        if not scrolled:
            driver.execute_script(
                "window.scrollTo({top: document.body.scrollHeight});"
            )

        time.sleep(random.uniform(6, 9))

    print(f"New followers collected this run: {len(collected)}")
    return collected


# ======================================================
# EXTRACT CONTACT DETAILS
# ======================================================
def extract_contact_details(driver):
    details = {
        "Location": "",
        "Phone": "",
        "Email": "",
        "Website": "",
        "External Facebook": "",
        "External LinkedIn": "",
        "External Instagram": "",
    }

    time.sleep(3)

    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        try:
            href = link.get_attribute("href")
            if not href:
                continue

            h = href.lower()
            if "linkedin.com" in h:
                details["External LinkedIn"] = href
            elif "instagram.com" in h:
                details["External Instagram"] = href
            elif href.startswith("http") and details["Website"] == "":
                details["Website"] = href

        except StaleElementReferenceException:
            continue

    page = driver.page_source.lower()

    phone = re.search(r"\+?\d[\d\s\-]{8,}", page)
    email = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", page
    )

    if phone:
        details["Phone"] = phone.group()
    if email:
        details["Email"] = email.group()

    return details


# ======================================================
# SAVE / APPEND TO EXCEL
# ======================================================
def save_to_excel(data):
    if os.path.exists(OUT_XLSX):
        wb = load_workbook(OUT_XLSX)
        ws = wb.active
        start_row = ws.max_row + 1
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Facebook Data"

        bold = Font(bold=True)
        for col, header in enumerate(HEADERS, start=1):
            c = ws.cell(row=1, column=col, value=header)
            c.font = bold

        start_row = 2

    for idx, row in enumerate(data, start=start_row):
        ws.cell(row=idx, column=1, value=idx - 1)
        for col, val in enumerate(row, start=2):
            ws.cell(row=idx, column=col, value=val)

    wb.save(OUT_XLSX)
    print(f"Excel updated at: {os.path.abspath(OUT_XLSX)}")


# ======================================================
# MAIN
# ======================================================
def main():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)

        existing_profiles = load_existing_profiles()
        new_followers = collect_followers(driver, existing_profiles)

        final_data = []

        for name, url in new_followers:
            print(f"Extracting details for: {name}")
            driver.get(url)
            time.sleep(random.uniform(4, 6))

            details = extract_contact_details(driver)

            final_data.append([
                name,
                url,
                details["Location"],
                details["Phone"],
                details["Email"],
                details["Website"],
                url,
                details["External LinkedIn"],
                details["External Instagram"],
            ])

        if final_data:
            save_to_excel(final_data)
        else:
            print("No new data to append.")

    finally:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            close_shot = os.path.join(
                SCREENSHOT_DIR, f"before_close_{ts}.png"
            )
            driver.save_screenshot(close_shot)
            print(f"Closing screenshot saved at: {os.path.abspath(close_shot)}")
        except Exception as e:
            print(f"Could not take closing screenshot: {e}")

        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
