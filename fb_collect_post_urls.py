import os
import time
from datetime import datetime
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"

SEARCH_URLS = {
    "posts": f"https://mbasic.facebook.com/search/posts/?q={KEYWORD}",
}

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs("cookies", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_{KEYWORD}_ALL_posts_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--window-size=412,915")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(4)

    if not os.path.exists(COOKIE_FILE):
        print("[WARN] Cookie file not found")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    driver.add_cookie({
                        "name": parts[5],
                        "value": parts[6],
                        "domain": ".facebook.com"   # ✅ FIXED
                    })

    driver.refresh()
    time.sleep(5)
    print("[INFO] Cookies loaded")


# ================= URL NORMALIZER =================
def clean_post_url(url):
    if not url:
        return None

    if "/posts/" in url:
        return url.split("?")[0]

    if "photo.php?fbid=" in url:
        return url.split("&")[0]

    if "permalink.php" in url:
        return url.split("&")[0]

    return None


# ================= COLLECT POSTS =================
def collect_post_urls(driver, scrolls=15):
    post_urls = set()

    for i in range(scrolls):
        print(f"[SCROLL] {i + 1}/{scrolls}")

        links = driver.find_elements(By.XPATH, "//a[@href]")
        for a in links:
            href = a.get_attribute("href")
            if not href:
                continue

            if (
                "/posts/" in href
                or "photo.php?fbid=" in href
                or "permalink.php" in href
            ):
                clean = clean_post_url(href)
                if clean:
                    post_urls.add(clean)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"scroll_{i+1:02d}.png")
        )

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    all_posts = set()

    try:
        for name, url in SEARCH_URLS.items():
            print(f"[OPEN] {name.upper()} SEARCH")
            driver.get(url)
            time.sleep(5)

            urls = collect_post_urls(driver)
            all_posts.update(urls)

        wb = Workbook()
        ws = wb.active
        ws.title = "Facebook Posts"

        ws.append(["S.No", "Post URL"])
        for c in ws[1]:
            c.font = Font(bold=True)

        for i, u in enumerate(sorted(all_posts), 1):
            ws.append([i, u])

        wb.save(OUTPUT_EXCEL)

        print("===================================")
        print("TOTAL UNIQUE POSTS:", len(all_posts))
        print("EXCEL:", OUTPUT_EXCEL)
        print("===================================")

    finally:
        driver.quit()


if __name__ == "__main__":
    run()
