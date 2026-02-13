import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
KEYWORD = "probate"
# Note: Use mbasic search URL specifically
SEARCH_URL = f"https://mbasic.facebook.com/search/posts/?q={KEYWORD}"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    # Masking as a mobile device is critical for mbasic
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(60)
    return driver

# ================= LOAD COOKIES =================
def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        print("Cookie file not found.")
        return False

    # IMPORTANT: Must go to mbasic domain before adding cookies
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            parts = line.strip().split("\t")
            if len(parts) < 7: continue

            # Standard Netscape cookie format
            domain, flag, path, secure, expiry, name, value = parts
            cookie = {"name": name, "value": value, "path": "/"}
            if expiry.isdigit() and int(expiry) > 0:
                cookie["expiry"] = int(expiry)

            try:
                driver.add_cookie(cookie)
            except Exception:
                continue

    driver.refresh()
    time.sleep(5)
    return "login" not in driver.current_url.lower()

# ================= COLLECT POSTS (UPDATED XPATHS) =================
def collect_posts(driver, max_pages=3):
    post_urls = set()

    for page in range(max_pages):
        print(f"Scraping results page {page + 1}...")
        
        # XPath 1: Links to the full story/permalink
        # These are usually the 'Full Story' links or timestamps
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/story.php?') or contains(@href, '/posts/')]")

        for a in links:
            href = a.get_attribute("href")
            if href:
                # Clean tracking junk (strip everything after the first &)
                clean_url = href.split("&")[0] if "story.php" in href else href.split("?")[0]
                post_urls.add(clean_url)

        # Handle Pagination
        try:
            # 2026 mbasic uses a specific div ID for the 'See More' link
            next_btn = driver.find_element(By.XPATH, "//div[@id='see_more_pager']//a")
            next_btn.click()
            time.sleep(5) # Allow search results to populate
        except:
            print("Reached end of search results.")
            break

    return post_urls

# ================= MAIN =================
def run():
    driver = init_driver()
    try:
        if not load_cookies(driver):
            print("Login failed. Check your cookies.")
            return

        print(f"Searching for: {KEYWORD}")
        driver.get(SEARCH_URL)
        time.sleep(5)

        posts = collect_posts(driver, max_pages=5)

        print(f"\nCollected {len(posts)} posts:")
        for i, url in enumerate(sorted(posts), 1):
            print(f"{i}. {url}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
