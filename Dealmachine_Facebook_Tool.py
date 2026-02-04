import os
import re
import time
from urllib.parse import urlparse, parse_qs, unquote

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

# ================= CONFIG =================
START_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_dealmachine_results.xlsx"

HEADERS = [
    "S.No", "Facebook Name", "Facebook Page URL", "Location",
    "Phone", "Email", "Website", "External Facebook",
    "External LinkedIn", "External Instagram",
]

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def init_driver():
    options = webdriver.ChromeOptions()
    # Jenkins/Headless Requirements
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Anti-Bot measures
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    return driver

def facebook_login(driver, wait):
    # These grab values from the Jenkins Credential Bindings
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        raise RuntimeError("FB_USERNAME or FB_PASSWORD not found in environment.")

    print(f"🔐 Logging into Facebook as: {username}")
    driver.get("https://www.facebook.com/login")
    
    try:
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(username)
        driver.find_element(By.ID, "pass").send_keys(password + Keys.ENTER)
        
        # Verify login by looking for navigation
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='navigation']")))
        print("✅ Facebook login successful")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        driver.save_screenshot("login_failure.png") # Captured for Jenkins artifact
        raise

# ... [Keep your existing load_or_create_workbook, upsert_row, and scrape_contact_info functions here] ...

def facebook_dealmachine_scraper():
    driver = init_driver()
    wait = WebDriverWait(driver, 30)
    wb, ws, url_to_row, processed, next_sno = load_or_create_workbook(OUT_XLSX)

    try:
        facebook_login(driver, wait)
        driver.get(START_URL)
        time.sleep(5)

        # Scraper logic...
        # [Keep your existing scraping loop here]
        
    finally:
        wb.save(OUT_XLSX)
        driver.quit()

if __name__ == "__main__":
    facebook_dealmachine_scraper()
