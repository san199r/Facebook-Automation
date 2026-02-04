# ======================================================
# Facebook Followers Scraper (RESUME + SCREENSHOTS)
# Jenkins-safe | Container Scroll | No Duplicates
# ======================================================

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import os
import time
import re
import random
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from webdriver_manager.chrome import ChromeDriverManager


# ======================================================
# CONFIG
# ======================================================
FOLLOWERS_URL = "https://www.facebook.com/dealmachineapp/followers/"
MAX_FOLLOWERS_PER_RUN = 50
MAX_NO_NEW = 15

HEADERS = [
    "S.No",
    "Facebook Name",
    "Facebook Page URL",
    "Location",
    "Phone",
    "Email",
    "Website",
    "External Facebook",
    "External LinkedIn",
    "External Instagram",
]

OUTPUT_DIR = os.path.join(os.getcwd(), "output")
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

OUT_XLSX = os.path.join(OUTPUT_DIR, "facebook_full_contact_data.xlsx")


# ======================================================
# DRIVER SETUP
# ======================================================
def setup_driver():
    options = webdriver.ChromeOptions()

    # Comment next line if you want non-headless
    options.add_argument("--headless=new")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 25)
    return driver, wait


# ======================================================
# FACEBOOK LOGIN + SCREENSHOT
# ======================================================
def facebook_login(driver, wait):
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        print("WARNING: FB_USERNAME or FB_PASSWORD not set.")
        return

    print(f"Logging in as: {username}")

    driver.get("https://www.facebook.com/login")
    time.sleep(5)

    email = wait.until(EC.presence_of_element_located((By.ID, "email")))
    passwd = wait.until(EC.presence_of_element_located((By.ID, "pass")))

    email.clear()
    email.send_keys(username)
    passwd.clear()
    passwd.send_keys(password)
    passwd.send_keys(Keys.ENTER)

    time.sleep(10)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    login_shot = os.path.join(
        SCREENSHOT_DIR, f"after_login_{ts}.png"
    )
    driver.save_screenshot(login_shot)

    print("Login completed.")
    print(f"Login screenshot saved at: {os.path.abspath(login_shot)}")


# ======================================================
# LOAD EXISTING PROFILES (RESUME)
# ======================================================
def load_existing_profiles():
    existing = set()

    if not os.path.exists(OUT_XLSX):
        return existing

    wb = load_workbook(OUT_XLSX)
    ws = wb.active

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and len(row) > 2 and row[2]:
            existing.add(row[2])

    print(f"Resuming: {len(existing)} profiles already scraped")
    return existing


# ======================================================
# FILTER VALID FOLLOWERS
# ======================================================
def is_valid_follower(name, url):
    if not name or not url:
        return False

    name_l = name.lower()
    url_l = url.lower()

    blocked = [
        "followers",
        "following",
        "forgotten",
        "account",
        "log in",
        "sign up",
    ]

    for b in blocked:
        if b in name_l:
            return False

    if "facebook.com" not in url_l:_
