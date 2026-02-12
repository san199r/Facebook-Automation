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
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"

# ✅ RECENT POSTS SEARCH
SEARCH_URL = f"https://mbasic.facebook.com/search/posts/?q={KEYWORD}&filters=recent"

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_{KEYWORD}_RECENT_posts_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--window-size=412,915")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Linux; Android 10) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

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
                        "domain": ".facebook.com"
                    })

    driver.refresh()
    time.sleep(4)
    print("[INFO] Cookies loaded")


# ================= CLEAN URL =================
def clean_post_url(url):
    if not url:
        return None

    parsed = urlparse(url)
    clean = parsed.scheme + "://" + parsed.netloc + parsed.path

    if "story.php" in url and "story_fbid" in url:
        return url.split("&")[0]

    return clean


# ================= COLLECT POSTS =================
def collect_post_urls(driver, max_pages=60):
    post_urls = set()
    page = 1

    while page <= max_pages:
        print(f"[PAGE] {page}/{max_pages}")
        time.sleep(3)

        links = driver.find_elements(By.XPATH, "//a[@href]")
        next_page = None

        for a in links:
            try:
                href = a.get_attribute("href")
            except StaleElementReferenceException:
                continue

            if not href:
                continue

            # ✅ POST URL DETECTION
            if (
                "story.php?story_fbid=" in href
                or "/posts/" in href
                or "photo.php?fbid=" in href
            ):
                cleaned = clean_post_url(href)
                if cleaned:
                    post_urls.add(cleaned)

            # ✅ GENERIC PAGINATION DETECTION
            if "/search/" in href and "cursor=" in href:
                next_page = href

        if not next_page:
            print("[INFO] No more pages found")
            break

        print("[NEXT PAGE]")
        driver.get(next_page)
        page += 1

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    try:
        print("[OPEN] SEARCH PAGE")
        driver.get(SEARCH_URL)
        time.sleep(5)

        posts = collect_post_urls(driver)

        wb = Workbook()
        ws = wb.active
        ws.title = "Facebook Posts"

        ws.append(["S.No", "Post URL"])
        for c in ws[1]:
            c.font = Font(bold=True)

        for i, url in enumerate(sorted(posts), 1):
            ws.append([i, url])

        wb.save(OUTPUT_EXCEL)

        print("===================================")
        print("TOTAL UNIQUE POSTS:", len(posts))
        print("EXCEL:", OUTPUT_EXCEL)
        print("===================================")

    finally:
        driver.quit()


if __name__ == "__main__":
    run()
