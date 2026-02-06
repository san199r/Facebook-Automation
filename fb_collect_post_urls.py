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


# ================= DRIVER (REAL CHROME PROFILE) =================
def init_driver():
    options = webdriver.ChromeOptions()

    # Basic stability
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    # REQUIRED FOR JENKINS
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # USE REAL CHROME PROFILE (CONFIRMED: Profile 6)
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


# ================= POST COLLECTION =================
def collect_post_urls(driver, scrolls=12):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i + 1}/{scrolls}")

        anchors = driver.find_elements(By.XPATH, "//a[@href]")
        for a in anchors:
            href = a.get_attribute("href")
            if not href:
                continue

            if (
                "facebook.com" in href
                and (
                    "permalink.php" in href
                    or "story_fbid=" in href
                    or "/posts/" in href
                    or ("/groups/" in href and "/posts/" in href)
                )
            ):
                post_urls.add(href.split("?")[0])

        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(5)

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    print("Opening Facebook posts search...")
    driver.get(SEARCH_URL)
    time.sleep(10)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"after_search_{TIMESTAMP}.png")
    )

    print("Collecting post URLs...")
    post_urls = collect_post_urls(driver)

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
