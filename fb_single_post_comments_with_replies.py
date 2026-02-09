import os
import time
import re
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

POST_URL = "https://www.facebook.com/photo/?fbid=4168798373434713"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_single_post_comments_with_replies_{TIMESTAMP}.xlsx"
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


# ================= LOAD ALL COMMENTS =================
def load_all_comments(driver, tag):
    step = 1
    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"{tag}_{step:02d}_open.png")
    )
    step += 1

    for _ in range(30):
        clicked = False

        links = driver.find_elements(By.XPATH, "//a[contains(text(),'View more comments')]")
        for link in links:
            try:
                link.click()
                clicked = True
                time.sleep(2)
            except:
                pass

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"{tag}_{step:02d}_scroll.png")
        )
        step += 1

        if not clicked:
            break


# ================= LOAD ALL REPLIES =================
def expand_all_replies(driver):
    for _ in range(20):
        reply_links = driver.find_elements(
            By.XPATH,
            "//a[contains(text(),'reply')]"
        )
        if not reply_links:
            break

        for link in reply_links:
            try:
                link.click()
                time.sleep(2)
            except:
                pass


# ================= PARSE COMMENTS + REPLIES =================
def parse_comments_and_replies(body_text):
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]

    ignore = {
        "like", "reply", "share", "comment", "most relevant",
        "comments", "write a comment"
    }

    cleaned = []
    for line in lines:
        low = line.lower()
        if low in ignore:
            continue
        if re.match(r"\d+w", low):
            continue
        if re.match(r"\d+\s+of\s+\d+", low):
            continue
        if "view all" in low and "reply" in low:
            continue
        if low == "edited":
            continue
        if line in {"·", ".", "…"}:
            continue
        if line.isdigit():
            continue
        cleaned.append(line)

    results = []
    last_parent = ""

    i = 0
    while i < len(cleaned) - 1:
        name = cleaned[i]
        text = cleaned[i + 1]

        if len(name.split()) <= 4 and len(text.split()) > 2:
            if "replied" in name.lower():
                commenter = name.replace("replied", "").strip()
                results.append((commenter, text, "REPLY", last_parent))
            else:
                last_parent = name
                results.append((name, text, "COMMENT", ""))
            i += 2
        else:
            i += 1

    return results


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    mbasic_url = to_mbasic(POST_URL)
    print("Opening:", mbasic_url)

    driver.get(mbasic_url)
    time.sleep(6)

    load_all_comments(driver, "comments")
    expand_all_replies(driver)
    load_all_comments(driver, "after_replies")

    body_text = driver.find_element("tag name", "body").text
    driver.quit()

    parsed = parse_comments_and_replies(body_text)

    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"

    headers = [
        "Source",
        "Keyword",
        "Commentator",
        "Comment",
        "Comment Type",
        "Parent Commentator",
        "Post URL"
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for name, comment, ctype, parent in parsed:
        ws.append([
            SOURCE,
            KEYWORD,
            name,
            comment,
            ctype,
            parent,
            POST_URL
        ])

    wb.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Rows written:", len(parsed))
    print("Excel:", OUTPUT_EXCEL)
    print("Screenshots:", SCREENSHOT_DIR)
    print("===================================")


if __name__ == "__main__":
    run()
