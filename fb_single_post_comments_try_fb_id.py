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
    OUTPUT_DIR, f"fb_single_post_comments_TRY_FBID_{TIMESTAMP}.xlsx"
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


# ================= TRY GET FB ID =================
def try_get_fb_id_by_opening(driver, profile_url):
    fb_id = ""
    try:
        original = driver.current_url
        driver.get(profile_url)
        time.sleep(3)

        current = driver.current_url
        match = re.search(r"id=(\d+)", current)
        if match:
            fb_id = match.group(1)

        driver.get(original)
        time.sleep(2)
    except:
        pass

    return fb_id


# ================= LOAD COMMENTS =================
def load_all_comments(driver):
    for _ in range(20):
        links = driver.find_elements(By.XPATH, "//a[contains(text(),'View more comments')]")
        clicked = False
        for l in links:
            try:
                l.click()
                clicked = True
                time.sleep(2)
            except:
                pass

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

        if not clicked:
            break


# ================= EXTRACT COMMENTS =================
def extract_comments(driver):
    results = []

    blocks = driver.find_elements(By.XPATH, "//div[.//a]")
    for b in blocks:
        try:
            name_el = b.find_element(By.XPATH, ".//a")
            name = name_el.text.strip()
            profile_url = name_el.get_attribute("href")

            text = b.text.replace(name, "").strip()

            if len(name) < 3 or len(text.split()) < 2:
                continue

            fb_id = ""
            match = re.search(r"id=(\d+)", profile_url)
            if match:
                fb_id = match.group(1)
            else:
                fb_id = try_get_fb_id_by_opening(driver, profile_url)

            results.append((name, fb_id, text))
        except:
            continue

    return results


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    driver.get(to_mbasic(POST_URL))
    time.sleep(5)

    load_all_comments(driver)
    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"post_loaded_{TIMESTAMP}.png")
    )

    comments = extract_comments(driver)
    driver.quit()

    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"

    headers = [
        "Source",
        "Keyword",
        "Commentator",
        "Commentator FB ID",
        "Comment",
        "Post URL"
    ]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for name, fb_id, comment in comments:
        ws.append([
            SOURCE,
            KEYWORD,
            name,
            fb_id,
            comment,
            POST_URL
        ])

    wb.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Comments:", len(comments))
    print("Excel:", OUTPUT_EXCEL)
    print("===================================")


if __name__ == "__main__":
    run()
