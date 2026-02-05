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


# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="ignore").decode())


def clean_text(text):
    if not text:
        return ""
    return str(text).strip()


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


# ================= INPUT EXCEL =================
def get_latest_followers_excel():
    files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith("facebook_followers_") and f.endswith(".xlsx")
    ]
    if not files:
        raise FileNotFoundError("No facebook_followers_*.xlsx found")

    files.sort(reverse=True)
    latest = os.path.join(OUTPUT_DIR, files[0])
    safe_print(f"Using input Excel: {latest}")
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

    if "login" in driver.current_url.lower() or "checkpoint" in driver.current_url.lower():
        safe_print("⚠ Facebook session warning, continuing anyway")


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


# ================= ABOUT PAGE =================
def open_about_and_scroll(driver):
    try:
        about_btn = driver.find_element(
            By.XPATH,
            "//a[contains(@href,'/about') or .//span[normalize-space()='About']]"
        )
        driver.execute_script("arguments[0].click();", about_btn)
        time.sleep(4)
    except Exception:
        driver.get(driver.current_url.rstrip("/") + "/about")
        time.sleep(4)

    for _ in range(8):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)


# ================= CONTACT EXTRACTION =================
def extract_contact_info(driver):
    data = {"email": "", "phone": "", "address": ""}

    blocks = driver.find_elements(
        By.XPATH,
        "//div[@role='main']//span | //div[@role='main']//div"
    )

    for b in blocks:
        raw = b.text.strip()
        if not raw:
            continue

        for t in raw.split("\n"):
            tl = t.lower()

            if not data["email"]:
                m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", t)
                if m:
                    data["email"] = m.group(0)
                    continue

            if not data["phone"]:
                m = re.search(r"\+?\d[\d\s\-]{7,}", t)
                if m:
                    data["phone"] = m.group(0)
                    continue

            if (
                not data["address"]
                and len(t) > 10
                and not "@" in t
                and not t.startswith("http")
            ):
                if any(x in tl for x in [
                    "street", "road", "suite", "city", "state",
                    "district", "bangladesh", "india",
                    "united", "california", "san francisco"
                ]):
                    data["address"] = t.strip()

    return data


# ================= LINK EXTRACTION =================
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

        h = href.lower()

        if "youtube.com" in h and not links["youtube"]:
            links["youtube"] = href
        elif "instagram.com" in h and not links["instagram"]:
            links["instagram"] = href
        elif "linkedin.com" in h and not links["linkedin"]:
            links["linkedin"] = href
        elif ("twitter.com" in h or "x.com" in h) and not links["twitter"]:
            links["twitter"] = href
        elif (
            not links["website"]
            and "facebook.com" not in h
            and not any(s in h for s in ["youtube", "instagram", "linkedin", "twitter", "x.com"])
        ):
            links["website"] = href

    return links


# ================= MAIN =================
def enrich_profiles():
    driver = init_driver()
    load_facebook_cookies(driver)

    input_wb = load_workbook(INPUT_EXCEL)
    input_ws = input_wb.active

    out_wb, out_ws = init_output_excel()

    for row in range(2, input_ws.max_row + 1):
        name = clean_text(input_ws.cell(row, 2).value)
        profile_url = input_ws.cell(row, 3).value

        safe_print(f"[ROW {row}] {name} -> {profile_url}")

        if not profile_url:
            continue

        try:
            driver.get(profile_url)
            time.sleep(4)

            open_about_and_scroll(driver)

            contact = extract_contact_info(driver)
            links = extract_links(driver)

            out_ws.append([
                name,
                profile_url,
                contact["address"],
                contact["email"],
                contact["phone"],
                links["youtube"],
                links["instagram"],
                links["website"],
                links["linkedin"],
                links["twitter"]
            ])

        except TimeoutException as e:
            safe_print(f"⏱ Timeout: {e}")
        except Exception as e:
            safe_print(f"❌ Error: {e}")

    out_wb.save(OUTPUT_EXCEL)
    safe_print(f"✅ Output saved: {OUTPUT_EXCEL}")

    driver.quit()
    safe_print("Browser closed")


# ================= RUN =================
if __name__ == "__main__":
    enrich_profiles()
