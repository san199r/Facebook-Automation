import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
PAGE_BASE = "https://www.facebook.com/dealmachineapp"
KEYWORD = "probate"

SEARCH_URL = f"{PAGE_BASE}/search/?q={KEYWORD}"
COOKIE_FILE = "cookies/facebook_cookies.txt"


# ================= DRIVER SETUP =================
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


# ================= LOAD COOKIES =================
def load_facebook_cookies():
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("\t")
            if len(parts) < 7:
                continue

            cookie = {
                "domain": parts[0],
                "path": parts[2],
                "name": parts[5],
                "value": parts[6]
            }

            try:
                driver.add_cookie(cookie)
            except Exception:
                pass

    driver.refresh()
    time.sleep(6)


# ================= LOGIN =================
print("Loading Facebook cookies...")
load_facebook_cookies()
print("Cookies loaded. Logged-in session active.")


# ================= OPEN PAGE SEARCH =================
print("Opening page search URL...")
driver.get(SEARCH_URL)
time.sleep(8)


# ================= COLLECT POSTS =================
print("Collecting post links from search results...")

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


# ================= PROCESS POSTS =================
for post_url in post_links[:5]:
    print("\nOpening post:", post_url)
    driver.get(post_url)
    time.sleep(8)

    # Scroll to load comments
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

            print("\nMATCH FOUND")
            print("Post URL:", post_url)
            print("Comment Text:", comment_text)
            print("User Name:", user.text)
            print("User Profile URL:", user.get_attribute("href"))

        except Exception:
            continue


print("\nProcess completed. Browser will stay open for 15 seconds.")
time.sleep(15)
driver.quit()
