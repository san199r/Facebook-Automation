import os
import time
import re
from datetime import datetime

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR,
    f"facebook_profiles_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
)

HEADERS = [
    "Name",
    "Profile URL",
    "Address",
    "Email",
    "Phone",
    "YouTube",
    "Instagram",
    "Website",
    "LinkedIn",
    "Twitter"
]


# ================= INPUT EXCEL (AUTO) =================
def get_latest_followers_excel():
    files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith("facebook_followers_") and f.endswith(".xlsx")
    ]

    if not files:
        raise FileNotFoundError(
            "No facebook_followers_*.xlsx found in output folder"
        )

    files.sort(reverse=True)
    latest = os.path.join(OUTPUT_DIR, files[0])
    print(f"Using input Excel: {latest}")
    return latest


INPUT_EXCEL = get_latest_followers_excel()


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

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path
            }

            if expiry.isdigit():
                cookie["expiry"] = int(expiry)

            driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(5)


# ================= EXCEL =================
def init_output_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Profiles"

    bold = Font(bold=True)
    for col, h in enumerate(HEADERS, start=1):
        cell = ws.cell(1, col, h)
        cell.font = bold

    return wb, ws


# ================= HELPERS =================
def extract_links(driver):
    links = {
        "youtube": "",
        "instagram": "",
        "website": "",
        "linkedin": "",
        "twitter": ""
    }

    anchors = driver.find_elements(By.XPATH, "//a[@href]")
    for a in anchors:
        href = a.get_attribute("href")
        if not href:
            continue

        href_l = href.lower()

        if "youtube.com" in href_l and not links["youtube"]:
            links["youtube"] = href
        elif "instagram.com" in href_l and not links["instagram"]:
            links["instagram"] = href
        elif "linkedin.com" in href_l and not links["linkedin"]:
            links["linkedin"] = href
        elif ("twitter.com" in href_l or "x.com" in href_l) and not links["twitter"]:
            links["twitter"] = href
        elif (
            "facebook.com" not in href_l
            and not links["website"]
            and re.match(r"https?://", href)
        ):
            links["website"] = href

    return links


def extract_value_by_label(driver, label):
    try:
        return driver.find_element(
            By.XPATH,
            f"//span[contains(text(),'{label}')]/following::span[1]"
        ).text.strip()
    except Exception:
        return ""


# ================= MAIN =================
def enrich_profiles():
    driver = init_driver()
    load_facebook_cookies(driver)

    if "login" in driver.current_url.lower():
        raise Exception("Cookie login failed")

    input_wb = load_workbook(INPUT_EXCEL)
    input_ws = input_wb.active

    out_wb, out_ws = init_output_excel()

    for row in range(2, input_ws.max_row + 1):
        name = input_ws.cell(row, 2).value
        profile_url = input_ws.cell(row, 3).value

        if not profile_url:
            continue

        print(f"Processing: {name}")

        try:
            driver.get(profile_url)
            time.sleep(4)

            driver.get(profile_url.rstrip("/") + "/about")
            time.sleep(4)

            address = extract_value_by_label(driver, "Address")
            email = extract_value_by_label(driver, "Email")
            phone = extract_value_by_label(driver, "Phone")

            links = extract_links(driver)

            out_ws.append([
                name,
                profile_url,
                address,
                email,
                phone,
                links["youtube"],
                links["instagram"],
                links["website"],
                links["linkedin"],
                links["twitter"]
            ])

        except TimeoutException:
            print(f"Timeout: {profile_url}")
            continue

    out_wb.save(OUTPUT_EXCEL)
    print(f"Output saved at: {OUTPUT_EXCEL}")

    driver.quit()


# ================= RUN =================
if __name__ == "__main__":
    enrich_profiles()
