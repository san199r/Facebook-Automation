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
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = "https://www.facebook.com/search/top?q=probate"  # Fixed URL
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")  # Your file

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs("cookies", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, f"fb_probate_final_{TIMESTAMP}.xlsx")

# ================= LOAD YOUR TXT COOKIES =================
def load_cookies():
    driver = init_driver()
    driver.get("https://www.facebook.com/")
    time.sleep(3)
    
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookie = {
                            'name': parts[5],
                            'value': parts[6],
                            'domain': parts[0]
                        }
                        driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(8)
        print("✅ Cookies loaded!")
    return driver

# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ================= FIXED POST COLLECTION =================
def collect_real_post_urls(driver, scrolls=15):
    post_urls = set()
    
    for i in range(scrolls):
        print(f"Scroll {i+1}/{scrolls}")
        
        # FIXED: Target actual post links
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'/posts/') or contains(@href,'permalink') or contains(@href,'facebook.com/photo') or contains(@href,'facebook.com/watch')]")
        
        for a in links:
            href = a.get_attribute("href")
            if href and "facebook.com" in href and not "/search/" in href:
                clean_url = href.split("?")[0]
                post_urls.add(clean_url)
        
        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(4)
    
    return post_urls

# ================= MAIN (YOUR STRUCTURE) =================
def run():
    driver = load_cookies()  # Uses your cookies
    
    try:
        driver.get(SEARCH_URL)
        time.sleep(10)
        driver.save_screenshot(os.path.join(SCREENSHOT_DIR, f"search_{TIMESTAMP}.png"))
        
        found_urls = collect_real_post_urls(driver)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Probate Posts"
        ws.append(["S.No", "Post URL"])
        for cell in ws[1]: cell.font = Font(bold=True)
        
        for idx, url in enumerate(sorted(found_urls), 1):
            ws.append([idx, url])
        
        wb.save(OUTPUT_EXCEL)
        print(f"✅ {len(found_urls)} posts → {OUTPUT_EXCEL}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
