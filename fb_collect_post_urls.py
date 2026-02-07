import os
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, f"fb_probate_results_{TIMESTAMP}.xlsx")

# ================= DRIVER SETUP =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Force Desktop resolution for Jenkins
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

# ================= COOKIE LOADING =================
def load_facebook_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(5)
    if not os.path.exists(COOKIE_FILE):
        print(f"CRITICAL: Cookie file missing at {COOKIE_FILE}")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            try:
                p = line.strip().split("\t")
                # Domain, flag, path, secure, expiry, name, value
                cookie = {"domain": p[0], "path": p[2], "name": p[5], "value": p[6]}
                if p[4].isdigit(): cookie["expiry"] = int(p[4])
                driver.add_cookie(cookie)
            except: continue
    
    print("Cookies loaded. Refreshing session...")
    driver.refresh()
    time.sleep(8)

# ================= DATA COLLECTION =================
def collect_real_post_urls(driver, scrolls=12):
    post_urls = set()
    wait = WebDriverWait(driver, 25)

    print("Waiting for feed to populate...")
    try:
        # Wait until at least one post container or the feed is present
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='article'] | //div[@role='feed']")))
    except:
        print("TIMEOUT: Results did not load. Saving debug info...")
        return post_urls

    for i in range(scrolls):
        print(f"Scanning Scroll {i + 1}/{scrolls}...")
        
        # Check for modern FB post containers
        containers = driver.find_elements(By.XPATH, "//div[@role='article']")
        print(f"DEBUG: Found {len(containers)} post containers on screen.")

        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            try:
                href = a.get_attribute("href")
                if not href or "facebook.com" not in href: continue
                if "/search/" in href: continue

                clean_url = href.split("?")[0].split("&")[0]

                # Target posts, group threads, and videos
                is_standard = "/posts/" in clean_url
                is_group = "/groups/" in clean_url and ("/posts/" in clean_url or "/permalink/" in clean_url)
                is_video = "/videos/" in clean_url and any(c.isdigit() for c in clean_url)
                
                if is_standard or is_group or is_video:
                    if not clean_url.endswith(("/groups/", "/videos/", "/posts/")):
                        post_urls.add(clean_url)
            except: continue

        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(5) 

    return post_urls

# ================= MAIN =================
def run():
    driver = init_driver()
    try:
        # 1. Login
        print("Initializing Session...")
        load_facebook_cookies(driver)

        # 2. Verify Login State
        driver.get("https://www.facebook.com/me")
        time.sleep(5)
        print(f"Verification - Current URL: {driver.current_url}")
        print(f"Verification - Page Title: {driver.title}")
        
        if "login" in driver.current_url:
            print("ALERT: Login failed. Cookies are likely expired.")
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "LOGIN_FAILED.png"))
            return

        # 3. Search
        print(f"Searching for: {KEYWORD}")
        driver.get(SEARCH_URL)
        time.sleep(10) 

        # 4. Debugging Artifacts
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"search_view_{TIMESTAMP}.png"))
        with open(os.path.join(OUTPUT_DIR, f"debug_source_{TIMESTAMP}.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        # 5. Collect
        found_urls = collect_real_post_urls(driver)

        # 6. Export
        wb = Workbook()
        ws = wb.active
        ws.title = "Captured Posts"
        ws.append(["S.No", "Post URL"])
        for cell in ws[1]: cell.font = Font(bold=True)

        for idx, url in enumerate(sorted(found_urls), start=1):
            ws.append([idx, url])

        wb.save(OUTPUT_EXCEL)
        print(f"Success! Collected {len(found_urls)} real post URLs.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run()
