import os
import time
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

POST_URL = "https://www.facebook.com/photo/?fbid=4168798373434713"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_single_post_comments_with_id_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--window-size=1200,900")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(4)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        driver.add_cookie({
                            "name": parts[5],
                            "value": parts[6],
                            "domain": ".facebook.com"
                        })

    driver.refresh()
    time.sleep(5)


def to_mbasic(url):
    return url.replace("www.facebook.com", "mbasic.facebook.com")


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    mbasic_url = to_mbasic(POST_URL)
    print("Opening:", mbasic_url)

    driver.get(mbasic_url)
    time.sleep(6)

    # Scroll to load comments
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, 1200)")
        time.sleep(2)

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"

    headers = [
        "Source",
        "Keyword",
        "Commentator",
        "Comment",
        "Commenter FB ID",
        "Commenter URL"
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    rows = 0

    # Each comment block usually has a profile link + text nearby
    for div in soup.find_all("div"):
        a = div.find("a", href=True)
        if not a:
            continue

        name = a.get_text(strip=True)
        href = a["href"]

        # Ignore non-profile links
        if "profile.php" not in href and not href.startswith("/"):
            continue

        # Extract FB ID
        fb_id = ""
        full_url = "https://facebook.com" + href if href.startswith("/") else href

        if "profile.php" in href:
            qs = parse_qs(urlparse(href).query)
            fb_id = qs.get("id", [""])[0]
        else:
            # username-based profile
            fb_id = href.strip("/").split("?")[0]

        # Try to find comment text near this name
        text = div.get_text(" ", strip=True)
        text = text.replace(name, "").strip()

        # Filter noise
        if len(text.split()) < 3:
            continue
        if "like" in text.lower() and "reply" in text.lower():
            continue

        ws.append([
            SOURCE,
            KEYWORD,
            name,
            text,
            fb_id,
            full_url
        ])
        rows += 1

    wb.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Comments written:", rows)
    print("Excel saved at:", OUTPUT_EXCEL)
    print("===================================")


if __name__ == "__main__":
    run()
