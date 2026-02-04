import os
import re
import time
from openpyxl import Workbook, load_workbook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
START_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_dealmachine_results.xlsx"

def init_driver():
    options = webdriver.ChromeOptions()
    # Jenkins Requirements
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Bypass bot detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Force ChromeDriverManager to install the correct driver for Chrome 144+
    service = ChromeService(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def facebook_login(driver, wait):
    # Pulling credentials from Jenkins Environment
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        print("⚠️ Warning: FB_USERNAME or FB_PASSWORD not set in environment.")
        return

    print(f"🔐 Logging in as: {username}")
    driver.get("https://www.facebook.com/login")
    
    try:
        wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(username)
        driver.find_element(By.ID, "pass").send_keys(password + Keys.ENTER)
        time.sleep(5)
        print("✅ Login process triggered")
    except Exception as e:
        driver.save_screenshot("login_failure.png")
        print(f"❌ Login failed: {e}")

def facebook_dealmachine_scraper():
    driver = init_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        facebook_login(driver, wait)
        driver.get(START_URL)
        print(f"📍 Current URL: {driver.current_url}")
        
        # Capture evidence for Jenkins
        driver.save_screenshot("final_page.png")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    facebook_dealmachine_scraper()
