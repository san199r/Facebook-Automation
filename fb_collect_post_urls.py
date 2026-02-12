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

# ✅ Normal Facebook Search (Recent)
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}&filters=recent"

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

    # ✅ JENKINS SAFE OPTIONS
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    if not os.path.exists(COOKIE_FILE):
        print("[WARN] Cookie file not found")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    try:
                        driver.add_cookie({
                            "name": parts[5],
                            "value": parts[6],
                            "domain": ".facebook.com"
                        })
                    except:
                        pass

    driver.refresh()
    time.sleep(5)
    print("[INFO] Cookies loaded")


# ================= CLEAN URL =================
def clean_post_url(url):
    if not url:
        return None

    if "story_fbid" in url:
        return url.split("&")[0]

    parsed = urlparse(url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path


# ================= COLLECT POSTS =================
def collect_post_urls(driver, max_scrolls=30):
    post_urls = set()

    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(max_scrolls):
        print(f"[SCROLL] {i+1}/{max_scrolls}")
        time.sleep(3)

        links = driver.find_elements(By.XPATH, "//a[@href]")

        for a in links:
            try:
                href = a.get_attribute("href")
            except StaleElementReferenceException:
                continue

            if not href:
                continue

            if (
                "story.php?story_fbid=" in href
                or "/posts/" in href
                or "/permalink/" in href
            ):
                cleaned = clean_post_url(href)
                if cleaned:
                    post_urls.add(cleaned)

        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            print("[INFO] No more scroll content")
            break

        last_height = new_height

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    try:
        print("[OPEN] SEARCH PAGE")
        driver.get(SEARCH_URL)
        time.sleep(8)

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
