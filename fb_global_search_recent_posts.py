import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SEARCH_URL = "https://www.facebook.com/search/top?q=probate"
KEYWORD = "probate"

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ================= DRIVER SETUP =================
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


# ================= OPEN SEARCH PAGE =================
print("Opening Facebook RECENT POSTS search...")
driver.get(SEARCH_URL)
time.sleep(10)


# ================= SCREENSHOT: SEARCH LOADED =================
search_screenshot = os.path.join(SCREENSHOT_DIR, "search_loaded.png")
driver.save_screenshot(search_screenshot)
print(f"Saved screenshot: {search_screenshot}")


# ================= SCROLL TO LOAD POSTS =================
print("Scrolling to load posts...")

for _ in range(6):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(4)


# ================= COLLECT POST LINKS =================
print("Collecting post links...")

posts = driver.find_elements(
    By.XPATH,
    "//a[contains(@href,'/posts/') or contains(@href,'/permalink/')]"
)

post_links = []
for p in posts:
    link = p.get_attribute("href")
    if link and link not in post_links:
        post_links.append(link)

print(f"Total posts found: {len(post_links)}")


# ================= OPEN POSTS & READ COMMENTS =================
for post_url in post_links[:5]:
    print("\nOpening post:", post_url)
    driver.get(post_url)
    time.sleep(8)

    for _ in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    comments = driver.find_elements(
        By.XPATH,
        "//div[@aria-label='Comment']"
    )

    print(f"Comments found: {len(comments)}")

    for c in comments:
        try:
            comment_text = c.text.strip()
            if KEYWORD.lower() not in comment_text.lower():
                continue

            user = c.find_element(
                By.XPATH,
                ".//a[contains(@href,'facebook.com')]"
            )

            print("MATCH FOUND")
            print("Post URL:", post_url)
            print("Comment:", comment_text)
            print("User Name:", user.text)
            print("User Profile URL:", user.get_attribute("href"))

        except Exception:
            continue


# ================= SCREENSHOT: BEFORE CLOSE =================
before_close_screenshot = os.path.join(SCREENSHOT_DIR, "before_close.png")
driver.save_screenshot(before_close_screenshot)
print(f"Saved screenshot: {before_close_screenshot}")


# ================= CLOSE =================
print("Process completed. Closing browser.")
time.sleep(5)
driver.quit()
