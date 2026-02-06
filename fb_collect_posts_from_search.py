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

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"facebook_posts_{KEYWORD}_{TIMESTAMP}.xlsx"
)


# ================= DRIVER (REAL PROFILE) =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # YOUR WORKING PROFILE
    options.add_argument(
        r"--user-data-dir=C:\Users\Dell\AppData\Local\Google\Chrome\User Data"
    )
    options.add_argument("--profile-directory=Profile 6")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    return driver


# ================= EXCEL =================
def init_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Post URLs"

    bold = Font(bold=True)
    ws.cell(1, 1, "S.No").font = bold
    ws.cell(1, 2, "Post URL").font = bold

    return wb, ws


# ================= COLLECT POSTS WHILE SEARCHING =================
def collect_posts_from_search(driver, scrolls=10):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i + 1}/{scrolls}")

        # Timestamp links inside posts
        time_links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'/posts/') or contains(@href,'permalink.php') or contains(@href,'story_fbid=')]"
        )

        for a in time_links:
            try:
                href = a.get_attribute("href")
                if not href:
                    continue

                clean = href.split("?")[0]

                # Extra safety: ignore search URLs
                if "/search/" in clean:
                    continue

                post_urls.add(clean)

            except Exception:
                continue

        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(5)

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    print("Opening Facebook post search...")
    driver.get(SEARCH_URL)
    time.sleep(12)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"after_search_{TIMESTAMP}.png")
    )

    print("Collecting post URLs from visible posts...")
    post_urls = collect_posts_from_search(driver)

    wb, ws = init_excel()
    for idx, url in enumerate(sorted(post_urls), start=1):
        ws.append([idx, url])

    wb.save(OUTPUT_EXCEL)

    print(f"Total posts collected: {len(post_urls)}")
    print(f"Excel saved: {OUTPUT_EXCEL}")

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"before_close_{TIMESTAMP}.png")
    )

    driver.quit()


# ================= RUN =================
if __name__ == "__main__":
    run()
