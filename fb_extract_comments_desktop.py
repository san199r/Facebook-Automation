import os
import time
from datetime import datetime

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

INPUT_EXCEL = "output/fb_probate_ALL_posts_20260209_110948.xlsx"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_{KEYWORD}_COMMENTS_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(5)

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
                        "domain": parts[0]
                    })

    driver.refresh()
    time.sleep(8)
    print("Cookies loaded")


# ================= EXPAND COMMENTS =================
def expand_comments(driver, rounds=6):
    for _ in range(rounds):
        buttons = driver.find_elements(
            By.XPATH,
            "//span[contains(text(),'View more') or contains(text(),'See more')]"
        )
        for b in buttons:
            try:
                driver.execute_script("arguments[0].click();", b)
                time.sleep(1)
            except:
                pass

        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(3)


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    wb_in = load_workbook(INPUT_EXCEL)
    ws_in = wb_in.active

    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = "Comments"

    headers = [
        "Source",
        "Keyword",
        "Commentator Name",
        "Url to find the Comment",
        "Comment"
    ]
    ws_out.append(headers)
    for cell in ws_out[1]:
        cell.font = Font(bold=True)

    try:
        for idx, row in enumerate(ws_in.iter_rows(min_row=2, values_only=True), 1):
            post_url = row[1]
            print(f"[{idx}] Opening: {post_url}")

            driver.get(post_url)
            time.sleep(8)

            expand_comments(driver)

            driver.save_screenshot(
                os.path.join(SCREENSHOT_DIR, f"post_{idx}.png")
            )

            comment_blocks = driver.find_elements(
                By.XPATH, "//div[@role='article']"
            )

            if not comment_blocks:
                ws_out.append([
                    SOURCE,
                    KEYWORD,
                    "NO_COMMENTS",
                    post_url,
                    "NO_COMMENTS"
                ])
                continue

            for c in comment_blocks:
                try:
                    name = c.find_element(By.XPATH, ".//strong").text.strip()
                except StaleElementReferenceException:
                    continue
                except:
                    continue

                try:
                    text = c.find_element(By.XPATH, ".//div[@dir='auto']").text.strip()
                except:
                    text = ""

                if text:
                    ws_out.append([
                        SOURCE,
                        KEYWORD,
                        name,
                        post_url,
                        text
                    ])

    finally:
        wb_out.save(OUTPUT_EXCEL)
        driver.quit()

        print("================================")
        print("DONE")
        print(f"Excel saved: {OUTPUT_EXCEL}")
        print("================================")


if __name__ == "__main__":
    run()
