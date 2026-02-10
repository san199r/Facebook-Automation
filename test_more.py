import os
import time
import re
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

INPUT_EXCEL = "fb_probate_ALL_posts_20260210_115220.xlsx"
POST_URL_COLUMN = "Post URL"   # change ONLY if column name differs

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_ALL_posts_comments_{TIMESTAMP}.xlsx"
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


# ================= COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    if not os.path.exists(COOKIE_FILE):
        return

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                p = line.strip().split("\t")
                if len(p) >= 7:
                    driver.add_cookie({
                        "name": p[5],
                        "value": p[6],
                        "domain": ".facebook.com"
                    })

    driver.refresh()
    time.sleep(4)


# ================= HELPERS =================
def to_mbasic(url):
    return url.replace("www.facebook.com", "mbasic.facebook.com").replace(
        "photo/?", "photo.php?"
    )


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


def has_real_text(text):
    return bool(re.search(r"[A-Za-z]", text))


# ================= LOAD COMMENTS =================
def open_comment_section(driver):
    try:
        link = driver.find_element(
            By.XPATH, "//a[text()='Comment' or contains(text(),'Comment')]"
        )
        href = link.get_attribute("href")
        if href:
            driver.get(href)
            time.sleep(2)
    except:
        pass


def load_all_comments(driver):
    while True:
        try:
            more = driver.find_element(
                By.XPATH,
                "//a[contains(text(),'View more comments') or contains(text(),'See more')]"
            )
            href = more.get_attribute("href")
            if not href:
                break
            driver.get(href)
            time.sleep(2)
        except:
            break


# ================= STATEFUL PARSER =================
def parse_comments(body_text):
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]

    results = []
    current_name = None

    for line in lines:
        if is_timestamp(line) or is_ui_noise(line):
            continue

        if (
            1 <= len(line.split()) <= 4
            and has_real_text(line)
            and line == line.title()
        ):
            current_name = line
            continue

        if current_name and has_real_text(line):
            results.append((current_name, line))

    return results


# ================= READ POST URLS =================
def read_post_urls():
    wb = load_workbook(INPUT_EXCEL)
    ws = wb.active

    headers = [c.value for c in ws[1]]
    idx = headers.index(POST_URL_COLUMN)

    urls = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[idx]:
            urls.append(row[idx])

    return urls


# ================= MAIN =================
def run():
    post_urls = read_post_urls()
    print("Total posts:", len(post_urls))

    driver = init_driver()
    load_cookies(driver)

    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = "Comments"

    headers = ["Source", "Keyword", "Commentator", "Comment", "Post URL"]
    ws_out.append(headers)
    for c in ws_out[1]:
        c.font = Font(bold=True)

    total_comments = 0

    for idx, post_url in enumerate(post_urls, 1):
        print(f"[{idx}/{len(post_urls)}] Processing:", post_url)

        driver.get(to_mbasic(post_url))
        time.sleep(3)

        open_comment_section(driver)
        load_all_comments(driver)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        comments = parse_comments(body_text)

        if not comments:
            ws_out.append([SOURCE, KEYWORD, "NO_COMMENTS", "NO_COMMENTS", post_url])
            continue

        for name, comment in comments:
            ws_out.append([SOURCE, KEYWORD, name, comment, post_url])
            total_comments += 1

    driver.quit()
    wb_out.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Total comments:", total_comments)
    print("Output Excel:", OUTPUT_EXCEL)
    print("===================================")


if __name__ == "__main__":
    run()
