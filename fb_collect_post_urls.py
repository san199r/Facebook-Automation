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
# This direct URL forces the "Posts" tab using an encoded filter parameter
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}&filters=eyJycF9hdXRob3IiOiJ7XCJuYW1lXCI6XCJhdXRob3JcIixcImFyZ3NcIjpcXCJcIn0ifQ%3D%3D"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, f"fb_probate_final_{TIMESTAMP}.xlsx")

# ================= DRIVER SETUP =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

# ================= DATA COLLECTION =================
def collect_real_post_urls(driver, scrolls=12):
    post_urls = set()
    wait = WebDriverWait(driver, 25)

    print("Checking for search results on the Posts tab...")
    try:
        # Broad detection for the feed or individual articles
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='feed'] | //div[@role='article']")))
        print("Content detected!")
    except:
        print("TIMEOUT: Content did not appear. Saving screenshot...")
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, "EMPTY_RESULTS_FAIL.png"))
        return post_urls

    for i in range(scrolls):
        print(f"Scanning Scroll {i + 1}/{scrolls}...")
        
        # Grab all links and filter by post-specific patterns
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            try:
                href = a.get_attribute("href")
                if not href or "facebook.com" not in href or "/search/" in href:
                    continue

                # Clean tracking parameters
                clean_url = href.split("?")[0].split("&")[0]

                # Identify Posts, Permalinks, and Videos
                if any(term in clean_url for term in ["/posts/", "/permalink/", "/videos/"]):
                    if not clean_url.endswith(("/groups/", "/videos/", "/posts/")):
                        post_urls.add(clean_url)
            except:
                continue

        # Scroll to lazy-load more posts
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(6) 

    return post_urls

# ================= MAIN =================
def run():
    driver = init_driver()
    try:
        # 1. Login Logic
        driver.get("https://www.facebook.com/")
        # (Your existing cookie loading logic here...)

        # 2. Go directly to filtered search
        print(f"Navigating to Forced-Filter Search: {SEARCH_URL}")
        driver.get(SEARCH_URL)
        time.sleep(10) 

        # 3. Debugging trace
        print(f"Final Search URL: {driver.current_url}")
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"search_view_{TIMESTAMP}.png"))

        # 4. Extract
        found_urls = collect_real_post_urls(driver)

        # 5. Save Results
        wb = Workbook()
        ws = wb.active
        ws.title = "Scraped Posts"
        ws.append(["S.No", "Post URL"])
        for cell in ws[1]: cell.font = Font(bold=True)
        for idx, url in enumerate(sorted(found_urls), start=1):
            ws.append([idx, url])
        
        wb.save(OUTPUT_EXCEL)
        print(f"Finished! Found {len(found_urls)} URLs.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run()
