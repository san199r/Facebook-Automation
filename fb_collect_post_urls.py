import os
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
    options.add_argument("--start-maximized")
    # Mimic a real user to avoid bot detection
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
        print(f"Cookie file missing: {COOKIE_FILE}")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            try:
                p = line.strip().split("\t")
                cookie = {"domain": p[0], "path": p[2], "name": p[5], "value": p[6]}
                if p[4].isdigit(): cookie["expiry"] = int(p[4])
                driver.add_cookie(cookie)
            except: continue
    driver.refresh()
    time.sleep(5)

# ================= SMART URL COLLECTION =================
def collect_real_post_urls(driver, scrolls=12):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scanning Scroll {i + 1}/{scrolls}...")
        
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            try:
                href = a.get_attribute("href")
                if not href or "facebook.com" not in href: continue

                # EXCLUDE: Navigation and Search pages
                if any(x in href for x in ["/search/", "/notifications", "/messages", "/friends"]):
                    continue

                # CLEAN: Remove tracking params
                clean_url = href.split("?")[0].split("&")[0]

                # INCLUDE: Specific Content Patterns
                # 1. Standard Posts: /posts/123...
                # 2. Group Posts: /groups/xyz/posts/123...
                # 3. Video Posts: /videos/123...
                # 4. PHP Permalinks: permalink.php?story_fbid=...
                
                is_post = "/posts/" in clean_url
                is_video = "/videos/" in clean_url and any(char.isdigit() for char in clean_url)
                is_permalink = "permalink.php" in href
                
                if is_post or is_video or is_permalink:
                    # Final filter to ensure we aren't just grabbing a profile or group home page
                    if not clean_url.endswith(("/groups/", "/videos/", "/posts/")):
                        post_urls.add(clean_url if not is_permalink else href.split("&")[0])
            except:
                continue

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)

    return post_urls

# ================= MAIN =================
def run():
    driver = init_driver()
    try:
        print("Initializing Session...")
        load_facebook_cookies(driver)

        print(f"Searching for: {KEYWORD}")
        driver.get(SEARCH_URL)
        time.sleep(10) # Essential wait for dynamic content

        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "load_check.png"))

        found_urls = collect_real_post_urls(driver)

        # Save to Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Captured Posts"
        ws.append(["S.No", "Post URL"])
        for cell in ws[1]: cell.font = Font(bold=True)

        for idx, url in enumerate(sorted(found_urls), start=1):
            ws.append([idx, url])

        wb.save(OUTPUT_EXCEL)
        print(f"Success! Collected {len(found_urls)} real post URLs.")
        print(f"Results saved to: {OUTPUT_EXCEL}")

    finally:
        driver.quit()

if __name__ == "__main__":
    run()
