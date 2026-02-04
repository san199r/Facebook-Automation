# ======================================================
# Facebook Followers Extractor – Container Scroll FIXED
# Jenkins-safe | Robust scrolling | Full Excel output
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
MAX_FOLLOWERS = 50          # realistic target without blocks
MAX_NO_NEW = 15             # patience level

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
OUT_XLSX = os.path.join(
    OUTPUT_DIR, f"facebook_full_contact_data_{timestamp}.xlsx"
)


# ======================================================
# DRIVER SETUP
# ======================================================
def setup_driver():
    options = webdriver.ChromeOptions()

    # NOTE: Comment headless if you want more followers
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
# FOLLOWERS COUNT (DISPLAY)
# ======================================================
def get_total_followers_text(driver):
    time.sleep(4)
    spans = driver.find_elements(By.XPATH, "//span")
    for span in spans:
        text = span.text.lower().strip()
        if "followers" in text:
            return text
    return "Unknown"


# ======================================================
# SCROLL FOLLOWERS CONTAINER (CRITICAL FIX)
# ======================================================
def scroll_followers_container(driver):
    try:
        containers = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        if containers:
            container = containers[0]
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                container
            )
            return True
    except Exception:
        pass
    return False


# ======================================================
# COLLECT FOLLOWERS (ROBUST)
# ======================================================
def collect_all_followers(driver):
    print("Opening followers page...")
    driver.get(FOLLOWERS_URL)
    time.sleep(8)

    followers_text = get_total_followers_text(driver)
    print(f"Followers shown by Facebook: {followers_text}")

    collected = []
    seen = set()
    no_new = 0

    while len(collected) < MAX_FOLLOWERS and no_new < MAX_NO_NEW:
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
                    name
                    and href
                    and "facebook.com" in href
                    and href not in seen
                ):
                    seen.add(href)
                    collected.append((name, href))
                    new_found += 1
                    print(f"Collected {len(collected)}: {name}")

                    if len(collected) >= MAX_FOLLOWERS:
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

    print(f"Total followers collected: {len(collected)}")
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
# SAVE TO EXCEL
# ======================================================
def save_to_excel(data):
    wb = Workbook()
    ws = wb.active
    ws.title = "Facebook Data"

    bold = Font(bold=True)
    for col, header in enumerate(HEADERS, start=1):
        c = ws.cell(row=1, column=col, value=header)
        c.font = bold

    for idx, row in enumerate(data, start=1):
        ws.cell(row=idx + 1, column=1, value=idx)
        for col, val in enumerate(row, start=2):
            ws.cell(row=idx + 1, column=col, value=val)

    wb.save(OUT_XLSX)
    print(f"Excel saved at: {os.path.abspath(OUT_XLSX)}")


# ======================================================
# MAIN
# ======================================================
def main():
    driver, wait = setup_driver()

    try:
        facebook_login(driver, wait)
        followers = collect_all_followers(driver)

        final_data = []
        for name, url in followers:
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
            print("No data extracted.")

    finally:
        print("Closing browser...")
        driver.quit()


if __name__ == "__main__":
    main()
