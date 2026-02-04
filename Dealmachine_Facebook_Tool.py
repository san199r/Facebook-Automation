import os
import re
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from webdriver_manager.chrome import ChromeDriverManager


START_URL = "https://www.facebook.com/dealmachineapp/followers/"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXCEL_FILE = os.path.join(
    OUTPUT_DIR,
    f"facebook_followers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
)

HEADERS = [
    "S.No",
    "Facebook Name",
    "Facebook Page URL",
]


# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="ignore").decode())


# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    return driver


# ================= COOKIES =================
def load_facebook_cookies(driver, cookie_file):
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    with open(cookie_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            domain, flag, path, secure, expiry, name, value = line.strip().split("\t")

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
            }

            if expiry.isdigit():
                cookie["expiry"] = int(expiry)

            driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(5)


# ================= EXCEL =================
def init_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Followers"

    bold = Font(bold=True)
    for c, h in enumerate(HEADERS, start=1):
        cell = ws.cell(1, c, h)
        cell.font = bold

    return wb, ws


# ================= HELPERS =================
def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def is_valid_name(name):
    bad = {
        "followers", "following", "about", "mentions", "reviews",
        "reels", "photos", "home", "friends", "messages"
    }
    return name and name.lower() not in bad and len(name) > 2


# ================= MAIN =================
def scrape_followers():
    driver = init_driver()
    wait = WebDriverWait(driver, 30)

    safe_print("Loading cookies")
    load_facebook_cookies(driver, COOKIE_FILE)

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "after_login.png"))

    if "login" in driver.current_url.lower():
        raise Exception("Cookie login failed. Facebook redirected to login page.")

    safe_print("Login successful")

    driver.get(START_URL)
    time.sleep(5)

    try:
        followers_text = driver.find_element(
            By.XPATH, "//span[contains(text(),'followers')]"
        ).text
        safe_print(f"Followers shown by Facebook: {followers_text}")
    except Exception:
        safe_print("Could not read followers count")

    wb, ws = init_excel()

    collected = set()
    sno = 1
    no_new_rounds = 0
    MAX_NO_NEW = 15

    safe_print("Collecting followers")

    while no_new_rounds < MAX_NO_NEW:
        found_this_round = 0

        anchors = driver.find_elements(
            By.XPATH,
            "//div[@role='main']//a[contains(@href,'facebook.com') and .//span[@dir='auto']]"
        )

        for a in anchors:
            try:
                name = normalize(a.text)
                href = a.get_attribute("href")

                if not is_valid_name(name):
                    continue

                if href in collected:
                    continue

                collected.add(href)

                ws.append([sno, name, href])
                safe_print(f"Collected {sno}: {name}")

                sno += 1
                found_this_round += 1

            except StaleElementReferenceException:
                continue

        if found_this_round == 0:
            no_new_rounds += 1
            safe_print(f"No new followers found ({no_new_rounds}/{MAX_NO_NEW})")
        else:
            no_new_rounds = 0

        driver.execute_script("window.scrollBy(0, 1600);")
        time.sleep(2)

    wb.save(EXCEL_FILE)
    safe_print(f"Excel saved at: {EXCEL_FILE}")

    driver.save_screenshot(os.path.join(OUTPUT_DIR, "before_close.png"))

    driver.quit()
    safe_print("Browser closed")


if __name__ == "__main__":
    scrape_followers()
