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
    options.add_argument("--window-size=412,915")
    options.add_argument("--disable-notifications")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Linux; Android 10; SM-G960U) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.224 Mobile Safari/537.36"
    )

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(4)

    if not os.path.exists(COOKIE_FILE):
        print("Cookie file not found")
        return

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
    print("Cookies loaded")


# ================= URL HELPERS =================
def to_mbasic(url):
    if "mbasic.facebook.com" in url:
        return url
    return url.replace("www.facebook.com", "mbasic.facebook.com").replace(
        "photo/?", "photo.php?"
    )


# ================= OPEN COMMENT SECTION =================
def open_comment_section(driver):
    try:
        link = driver.find_element(
            By.XPATH, "//a[text()='Comment' or contains(text(),'Comment')]"
        )
        href = link.get_attribute("href")
        if href:
            driver.get(href)
            time.sleep(3)
    except:
        pass


# ================= LOAD ALL COMMENTS =================
def load_all_comments(driver, tag):
    step = 1
    while True:
        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"{tag}_{step:02d}.png")
        )
        step += 1
        try:
            more = driver.find_element(
                By.XPATH,
                "//a[contains(text(),'View more comments') or contains(text(),'See more')]"
            )
            href = more.get_attribute("href")
            if not href:
                break
            driver.get(href)
            time.sleep(3)
        except:
            break


# ================= LOAD ALL REPLIES =================
def expand_all_replies(driver):
    for _ in range(15):
        try:
            links = driver.find_elements(
                By.XPATH,
                "//a[contains(text(),'Reply') or contains(text(),'repl')]"
            )
            if not links:
                break
            for l in links:
                href = l.get_attribute("href")
                if href:
                    driver.get(href)
                    time.sleep(2)
        except:
            break


# ================= FILTER HELPERS =================
def is_timestamp(text):
    return bool(re.match(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},\s+\d{4}",
        text.lower()
    ))


def is_ui_noise(text):
    if re.match(r"^[\W_]+$", text):
        return True
    if re.match(r"^\d+$", text):
        return True
    if re.match(r"^[^\w\s]+\s*\d*$", text):
        return True
    if re.match(r"^(like|reply|share|watch)", text.lower()):
        return True
    if re.match(r"^[\uE000-\uF8FF]", text):
        return True
    return False


# ================= PARSE COMMENTS =================
def parse_comments_and_replies(body_text):
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    results = []
    last_parent = ""

    i = 0
    while i < len(lines) - 1:
        name = lines[i]

        if (
            len(name.split()) > 4
            or is_timestamp(name)
            or is_ui_noise(name)
        ):
            i += 1
            continue

        j = i + 1
        if j < len(lines) and is_timestamp(lines[j]):
            j += 1
        if j >= len(lines):
            break

        comment = lines[j]

        if (
            is_timestamp(comment)
            or is_ui_noise(comment)
            or len(comment.split()) < 3
        ):
            i += 1
            continue

        if "replied" in name.lower():
            commenter = name.replace("replied", "").strip()
            results.append((commenter, comment, "REPLY", last_parent))
        else:
            last_parent = name
            results.append((name, comment, "COMMENT", ""))

        i = j + 1

    return results


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    driver.get(to_mbasic(POST_URL))
    time.sleep(5)

    open_comment_section(driver)
    load_all_comments(driver, "comments")
    expand_all_replies(driver)
    load_all_comments(driver, "after_replies")

    body_text = driver.find_element(By.TAG_NAME, "body").text
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

    for r in parsed:
        ws.append([SOURCE, KEYWORD, *r, POST_URL])

    wb.save(OUTPUT_EXCEL)

    print("DONE")
    print("Rows:", len(parsed))
    print("Excel:", OUTPUT_EXCEL)


if __name__ == "__main__":
    run()
