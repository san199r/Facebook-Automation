import os
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}"

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR,
    f"facebook_posts_{KEYWORD}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
)


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


# ================= COOKIES LOGIN =================
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
    time.sleep(6)


# ================= EXCEL =================
def init_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Post URLs"

    headers = ["S.No", "Post URL"]
    bold = Font(bold=True)

    for col, h in enumerate(headers, start=1):
        ws.cell(1, col, h).font = bold

    return wb, ws


# ================= COLLECT POSTS =================
def collect_post_urls(driver, scrolls=8):
    post_urls = set()

    for i in range(scrolls):
        links = driver.find_elements(By.XPATH, "//a[@href]")
        for a in links:
            href = a.get_attribute("href")
            if not href:
                continue

            if (
                "/posts/" in href
                or "/permalink/" in href
                or "story_fbid=" in href
            ):
                clean = href.split("?")[0]
                post_urls.add(clean)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    print("Loading Facebook cookies...")
    load_facebook_cookies(driver)

    print("Opening post search page...")
    driver.get(SEARCH_URL)
    time.sleep(8)

    # Screenshot after search load
    search_shot = os.path.join(
        SCREENSHOT_DIR,
        f"after_search_{datetime.now().strftime('%H%M%S')}.png"
    )
    driver.save_screenshot(search_shot)

    print("Scrolling and collecting post URLs...")
    post_urls = collect_post_urls(driver, scrolls=10)

    wb, ws = init_excel()

    for idx, url in enumerate(sorted(post_urls), start=1):
        ws.append([idx, url])

    wb.save(OUTPUT_EXCEL)
    print(f"Saved {len(post_urls)} post URLs")
    print(f"Excel file: {OUTPUT_EXCEL}")

    # Screenshot before close
    close_shot = os.path.join(
        SCREENSHOT_DIR,
        f"before_close_{datetime.now().strftime('%H%M%S')}.png"
    )
    driver.save_screenshot(close_shot)

    driver.quit()


# ================= RUN =================
if __name__ == "__main__":
    run()
