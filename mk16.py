import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://mbasic.facebook.com/search/posts/?q={KEYWORD}"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    # Jenkins usually needs headless mode
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Masking as a mobile iPhone ensures mbasic layout stays consistent
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1")
    options.add_argument("--window-size=414,896")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# ================= COLLECT POSTS (UPDATED XPATHS) =================
def collect_posts(driver, max_pages=3):
    post_urls = set()
    
    for page in range(max_pages):
        print(f"Scraping results page {page + 1}...")
        
        # Broad XPath to find links to posts, permalinks, or full stories
        xpath_query = "//a[contains(@href, 'story.php') or contains(@href, '/posts/') or contains(@href, 'permalink.php')]"
        links = driver.find_elements(By.XPATH, xpath_query)
        
        if not links:
            print("No links found on this page. Checking for login redirect...")
            if "login" in driver.current_url.lower():
                print("Error: Session expired or redirected to login.")
                break
            continue

        for a in links:
            try:
                href = a.get_attribute("href")
                if href and "facebook.com" in href:
                    # Clean the URL of tracking IDs
                    clean_url = href.split("&")[0].split("?")[0] if "/posts/" in href else href.split("&")[0]
                    post_urls.add(clean_url)
            except:
                continue

        # Pagination: The "See More Results" button
        try:
            # mbasic usually wraps the pagination link in a div with id='see_more_pager'
            next_pager = driver.find_element(By.ID, "see_more_pager")
            next_btn = next_pager.find_element(By.TAG_NAME, "a")
            next_btn.click()
            time.sleep(5) 
        except:
            print("Reached the end of search results.")
            break

    return post_urls

# (Include your run() and load_cookies() functions from previous versions here)
