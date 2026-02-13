import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # For Jenkins:
    # options.add_argument("--headless=new")
    # options.add_argument("--window-size=1920,3000")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.set_page_load_timeout(60)
    return driver


# ================= SCREENSHOT =================
def take_screenshot(driver, name):
    path = os.path.join(SCREENSHOT_DIR, f"{name}_{TIMESTAMP}.png")
    driver.save_screenshot(path)
    print("Screenshot saved:", path)


# ================= LOAD COOKIES =================
def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        print("Cookie file not found.")
        return False

    driver.get("https://www.facebook.com/")
    time.sleep(5)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("\t")
            if len(parts) < 7:
                continue

            domain, flag, path, secure, expiry, name, value = parts

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path
            }

            try:
                driver.add_cookie(cookie)
            except:
                continue

    driver.refresh()
    time.sleep(6)

    take_screenshot(driver, "after_cookies")
    return True


# ================= SEARCH USING SEARCH BOX =================
def search_keyword(driver):
    print("Searching for:", KEYWORD)

    search_box = driver.find_element(By.XPATH, "//input[@type='search']")
    search_box.clear()
    search_box.send_keys(KEYWORD)
    search_box.send_keys(Keys.ENTER)

    time.sleep(8)
    take_screenshot(driver, "after_search")

    # Click "Posts" tab
    try:
        posts_tab = driver.find_element(
            By.XPATH,
            "//a[contains(@href,'/search/posts') or contains(text(),'Posts')]"
        )
        posts_tab.click()
        time.sleep(6)
        take_screenshot(driver, "after_posts_tab")
    except:
        print("Posts tab not found (continuing).")


# ================= COLLECT POSTS =================
def collect_posts(driver, scrolls=8):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i+1}/{scrolls}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

    take_screenshot(driver, "after_scrolling")

    articles = driver.find_elements(By.XPATH, "//div[@role='article']")

    for art in articles:
        links = art.find_elements(By.XPATH, ".//a[@href]")
        for a in links:
            href = a.get_attribute("href")
            if not href:
                continue

            clean = href.split("?")[0]

            if "/search/" in clean:
                continue

            if (
                "/posts/" in clean
                or "permalink.php" in clean
                or "story_fbid=" in clean
                or ("/groups/" in clean and "/posts/" in clean)
            ):
                post_urls.add(clean)

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    try:
        if not load_cookies(driver):
            return

        search_keyword(driver)

        posts = collect_posts(driver)

        print("\n========== POSTS FOUND ==========\n")
        for i, url in enumerate(sorted(posts), start=1):
            print(f"{i}. {url}")

        print("\nTotal posts:", len(posts))

    except Exception as e:
        print("Error:", e)
        take_screenshot(driver, "error_state")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    run()
