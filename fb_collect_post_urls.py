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

# Ensure your cookie file is in the 'cookies' folder relative to the script
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, f"facebook_posts_{KEYWORD}_{TIMESTAMP}.xlsx")

# ================= DRIVER SETUP =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # Crucial for Jenkins: pretending to be a real browser
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Uncomment if running on a server without a GUI
    # options.add_argument("--headless=new") 

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    return driver

# ================= COOKIE HANDLING =================
def load_facebook_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    if not os.path.exists(COOKIE_FILE):
        print(f"ERROR: Cookie file not found at {COOKIE_FILE}")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            try:
                parts = line.strip().split("\t")
                if len(parts) < 7: continue
                
                domain, flag, path, secure, expiry, name, value = parts
                cookie = {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": path
                }
                if expiry.isdigit():
                    cookie["expiry"] = int(expiry)
                driver.add_cookie(cookie)
            except Exception as e:
                pass

    driver.refresh()
    time.sleep(8)

# ================= DATA COLLECTION =================
def collect_real_post_urls(driver, scrolls=12):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i + 1}/{scrolls}...")
        
        # We look for all links and filter based on Facebook's post URL patterns
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            try:
                href = a.get_attribute("href")
                if not href or "facebook.com" not in href:
                    continue

                # Remove tracking parameters (fbclid, etc.)
                clean_url = href.split("?")[0].split("&")[0]

                # Pattern matching for various FB post types
                is_post = any(term in href for term in ["/posts/", "/permalink.php", "story_fbid=", "/videos/"])
                is_group_post = "/groups/" in href and ("posts" in href or "permalink" in href)

                if is_post or is_group_post:
                    # Filter out noise like 'likes' or 'comment' specific links
                    if "/groups/" in clean_url and clean_url.endswith("/groups/"):
                        continue
                    post_urls.add(clean_url)
            except:
                continue

        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5) # Give FB time to load new content

    return post_urls

# ================= MAIN EXECUTION =================
def run():
    driver = init_driver()
    try:
        print("Loading cookies...")
        load_facebook_cookies(driver)

        print(f"Navigating to: {SEARCH_URL}")
        driver.get(SEARCH_URL)
        time.sleep(10)

        # Save screenshot to see what Jenkins sees
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"search_results_{TIMESTAMP}.png"))

        print("Collecting post URLs...")
        post_urls = collect_real_post_urls(driver)

        # Excel Export
        wb = Workbook()
        ws = wb.active
        ws.title = "Facebook Posts"
        ws.append(["S.No", "Post URL"])
        for cell in ws[1]: cell.font = Font(bold=True)

        for idx, url in enumerate(sorted(post_urls), start=1):
            ws.append([idx, url])

        wb.save(OUTPUT_EXCEL)

        print(f"Finished! Total real posts collected: {len(post_urls)}")
        print(f"Excel saved: {OUTPUT_EXCEL}")

        if len(post_urls) == 0:
            print("WARNING: No posts found. Check 'output/screenshots' to see if FB blocked the bot.")

    finally:
        driver.quit()

if __name__ == "__main__":
    run()
