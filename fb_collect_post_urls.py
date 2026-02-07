import os
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except Exception:
        print(text.encode("ascii", errors="ignore").decode())


# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://www.facebook.com/search/top?q={KEYWORD}"

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs("cookies", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_{KEYWORD}_posts_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies():
    driver = init_driver()
    driver.get("https://www.facebook.com/")
    time.sleep(4)

    if not os.path.exists(COOKIE_FILE):
        safe_print("Cookie file not found")
        return driver

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    driver.add_cookie({
                        "name": parts[5],
                        "value": parts[6],
                        "domain": parts[0]
                    })

    driver.refresh()
    time.sleep(8)
    safe_print("Cookies loaded successfully")

    return driver


# ================= COLLECT POST URLS + SCREENSHOTS =================
def collect_post_urls(driver, scrolls=15):
    post_urls = set()

    for i in range(scrolls):
        safe_print(f"Scrolling {i+1}/{scrolls}")

        # Screenshot BEFORE collecting
        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"scroll_{i+1:02d}.png")
        )

        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'/posts/') or "
            "contains(@href,'permalink.php') or "
            "contains(@href,'facebook.com/photo')]"
        )

        for a in links:
            href = a.get_attribute("href")
            if not href or "facebook.com" not in href:
                continue

            parsed = urlparse(href)
            qs = parse_qs(parsed.query)

            # Text / status post
            if "/posts/" in href:
                clean_url = href.split("?")[0]

            # Photo post
            elif "fbid" in qs:
                clean_url = f"https://www.facebook.com/photo/?fbid={qs['fbid'][0]}"

            # Permalink post
            elif "story_fbid" in qs and "id" in qs:
                clean_url = f"https://www.facebook.com/{qs['id'][0]}/posts/{qs['story_fbid'][0]}"

            else:
                continue

            post_urls.add(clean_url)

        # Screenshot AFTER collecting
        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"collect_{i+1:02d}.png")
        )

        driver.execute_script("window.scrollBy(0, 1600);")
        time.sleep(4)

    return post_urls


# ================= MAIN =================
def run():
    driver = load_cookies()

    try:
        driver.get(SEARCH_URL)
        time.sleep(10)

        # Initial screenshot
        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"search_start_{TIMESTAMP}.png")
        )

        urls = collect_post_urls(driver, scrolls=15)

        wb = Workbook()
        ws = wb.active
        ws.title = "Facebook Posts"

        ws.append(["S.No", "Post URL"])
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for i, url in enumerate(sorted(urls), 1):
            ws.append([i, url])

        wb.save(OUTPUT_EXCEL)

        safe_print(f"Total posts collected: {len(urls)}")
        safe_print(f"Excel saved at: {OUTPUT_EXCEL}")

        # Final screenshot
        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"final_{TIMESTAMP}.png")
        )

    finally:
        driver.quit()


if __name__ == "__main__":
    run()
