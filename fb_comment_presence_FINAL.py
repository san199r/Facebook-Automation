import os
import time
import re
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

POST_URL = "https://www.facebook.com/photo/?fbid=4168798373434713"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_single_post_comments_{TIMESTAMP}.xlsx"
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


# ================= LOAD COOKIES =================
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

    body_text = driver.find_element("tag name", "body").text
    driver.quit()

    # -------- PARSE COMMENTS FROM BODY TEXT --------
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]

    ignore = {
        "like", "reply", "share", "comment", "most relevant",
        "view more comments", "write a comment", "comments"
    }

    cleaned = []
    for line in lines:
        low = line.lower()
        if low in ignore:
            continue
        if re.match(r"\d+w", low):   # time like 16w
            continue
        if line.isdigit():           # counts
            continue
        cleaned.append(line)

    # -------- WRITE TO EXCEL --------
    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"

    headers = [
        "Source",
        "Keyword",
        "Commentator",
        "Comment",
        "Commenter URL"
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    i = 0
    rows_written = 0
    while i < len(cleaned) - 1:
        name = cleaned[i]
        comment = cleaned[i + 1]

        # heuristic: name short, comment longer
        if len(name.split()) <= 4 and len(comment.split()) > 2:
            ws.append([
                SOURCE,
                KEYWORD,
                name,
                comment,
                POST_URL
            ])
            rows_written += 1
            i += 2
        else:
            i += 1

    wb.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Comments written:", rows_written)
    print("Excel saved at:", OUTPUT_EXCEL)
    print("===================================")


if __name__ == "__main__":
    run()
