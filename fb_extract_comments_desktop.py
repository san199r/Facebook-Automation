import os
import time
from datetime import datetime

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

INPUT_EXCEL = "output/fb_probate_ALL_posts_20260209_110948.xlsx"

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


# ================= SCROLL COMMENTS =================
def scroll_page(driver, times=6):
    for _ in range(times):
        driver.execute_script("window.scrollBy(0, 1200);")
        time.sleep(3)


def click_view_more(driver):
    buttons = driver.find_elements(By.XPATH, "//span[contains(text(),'View more') or contains(text(),'See more')]")
    for btn in buttons:
        try:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
        except:
            pass


# ================= MAIN =================
def run():
    driver = init_driver()
    wait = WebDriverWait(driver, 15)

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

    row_out = 2

    try:
        for row in ws_in.iter_rows(min_row=2, values_only=True):
            post_url = row[1]

            print(f"Opening: {post_url}")
            driver.get(post_url)
            time.sleep(8)

            scroll_page(driver)
            click_view_more(driver)
            scroll_page(driver)

            driver.save_screenshot(
                os.path.join(SCREENSHOT_DIR, f"post_{row_out}.png")
            )

            comments = driver.find_elements(By.XPATH, "//div[@aria-label='Comment']")

            if not comments:
                ws_out.append([
                    SOURCE,
                    KEYWORD,
                    "NO_COMMENTS",
                    post_url,
                    "NO_COMMENTS"
                ])
                row_out += 1
                continue

            for c in comments:
                try:
                    name = c.find_element(By.XPATH, ".//strong").text.strip()
                except:
                    name = "UNKNOWN"

                try:
                    text = c.find_element(By.XPATH, ".//span").text.strip()
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
                    row_out += 1

    finally:
        wb_out.save(OUTPUT_EXCEL)
        driver.quit()

        print("===================================")
        print("DONE")
        print(f"Excel saved: {OUTPUT_EXCEL}")
        print("===================================")


if __name__ == "__main__":
    run()
