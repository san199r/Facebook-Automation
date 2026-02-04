import os
import re
import time

from openpyxl import load_workbook

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
EXCEL_FILE = os.path.join("output", "apollo_page_fb_followers.xlsx")
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

SLEEP_BETWEEN_PROFILES = 6


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
def load_facebook_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            domain, flag, path, secure, expiry, name, value = line.strip().split("\t")

            if not domain.endswith("facebook.com"):
                continue

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


# ================= HELPERS =================
def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_links(driver):
    links = driver.find_elements(By.XPATH, "//a[@href]")
    result = {
        "website": "",
        "fb": "",
        "linkedin": "",
        "instagram": "",
    }

    for a in links:
        href = a.get_attribute("href") or ""

        if not result["linkedin"] and "linkedin.com" in href:
            result["linkedin"] = href
        elif not result["instagram"] and "instagram.com" in href:
            result["instagram"] = href
        elif not result["website"] and href.startswith("http") and "facebook.com" not in href:
            result["website"] = href
        elif not result["fb"] and "facebook.com" in href:
            result["fb"] = href

    return result


def extract_location(driver):
    try:
        about = driver.find_element(By.XPATH, "//span[contains(text(),'Lives in')]")
        return normalize(about.text)
    except:
        return ""


# ================= MAIN =================
def enrich_profiles():
    if not os.path.exists(EXCEL_FILE):
        raise Exception("Excel file not found")

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    driver = init_driver()
    wait = WebDriverWait(driver, 20)

    load_facebook_cookies(driver)

    for row in range(2, ws.max_row + 1):
        profile_url = ws.cell(row, 3).value
        website = ws.cell(row, 7).value

        if not profile_url:
            continue

        # Skip already enriched rows
        if website:
            continue

        print(f"Enriching row {row}: {profile_url}")

        try:
            driver.get(profile_url)
            time.sleep(4)

            links = extract_links(driver)
            location = extract_location(driver)

            ws.cell(row, 4).value = location
            ws.cell(row, 7).value = links["website"]
            ws.cell(row, 8).value = links["fb"]
            ws.cell(row, 9).value = links["linkedin"]
            ws.cell(row, 10).value = links["instagram"]

            wb.save(EXCEL_FILE)

            time.sleep(SLEEP_BETWEEN_PROFILES)

        except TimeoutException:
            print(f"Timeout on {profile_url}")
            continue

    driver.quit()
    wb.save(EXCEL_FILE)
    print("Enrichment completed")


if __name__ == "__main__":
    enrich_profiles()
