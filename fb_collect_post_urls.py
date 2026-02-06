import os
import time
from datetime import datetime
import threading

import cv2
import numpy as np
import pyautogui

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}"

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
VIDEO_DIR = os.path.join(OUTPUT_DIR, "videos")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"facebook_posts_{KEYWORD}_{TIMESTAMP}.xlsx"
)

VIDEO_FILE = os.path.join(
    VIDEO_DIR, f"facebook_search_{KEYWORD}_{TIMESTAMP}.avi"
)


# ================= VIDEO RECORDING =================
recording = True

def record_screen():
    global recording

    screen_width, screen_height = pyautogui.size()
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(
        VIDEO_FILE, fourcc, 8.0, (screen_width, screen_height)
    )

    while recording:
        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        out.write(frame)

    out.release()


# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(60)
    return driver


# ================= COOKIES LOGIN =================
def load_facebook_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(3)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            domain, flag, path, secure, expiry, name, value = line.strip().split("\t")

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path
            }

            if expiry.isdigit():
                cookie["expiry"] = int(expiry)

            driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(6)


# ================= EXCEL =================
def init_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Post URLs"

    headers = ["S.No", "Post URL"]
    bold = Font(bold=True)

    for col, h in enumerate(headers, start=1):
        ws.cell(1, col, h).font = bold

    return wb, ws


# ================= POST URL COLLECTION =================
def collect_post_urls(driver, scrolls=10):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i + 1}/{scrolls}")

        articles = driver.find_elements(By.XPATH, "//div[@role='article']")

        for article in articles:
            try:
                links = article.find_elements(By.XPATH, ".//a[@href]")
            except Exception:
                continue

            for a in links:
                href = a.get_attribute("href")
                if not href:
                    continue

                if (
                    "facebook.com" in href
                    and "search/posts" not in href
                    and "groups" not in href
                    and (
                        "story_fbid=" in href
                        or "/posts/" in href
                        or "/permalink/" in href
                    )
                ):
                    post_urls.add(href.split("?")[0])

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

    return post_urls


# ================= MAIN =================
def run():
    global recording

    # Start video recording
    video_thread = threading.Thread(target=record_screen)
    video_thread.start()

    driver = init_driver()

    print("Loading Facebook cookies...")
    load_facebook_cookies(driver)

    print("Opening post search page...")
    driver.get(SEARCH_URL)
    time.sleep(8)

    # Screenshot after search
    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"after_search_{TIMESTAMP}.png")
    )

    print("Collecting post URLs...")
    post_urls = collect_post_urls(driver, scrolls=10)

    wb, ws = init_excel()

    for idx, url in enumerate(sorted(post_urls), start=1):
        ws.append([idx, url])

    wb.save(OUTPUT_EXCEL)

    print(f"Collected {len(post_urls)} post URLs")
    print(f"Excel saved: {OUTPUT_EXCEL}")

    # Screenshot before close
    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"before_close_{TIMESTAMP}.png")
    )

    driver.quit()

    # Stop recording
    recording = False
    video_thread.join()

    print(f"Video saved: {VIDEO_FILE}")


# ================= RUN =================
if __name__ == "__main__":
    run()
