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

    # For Jenkins use these:
    # options.add_argument("--headless=new")
    # options.add_argument("--window-size=412,915")

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

    print("Opening main Facebook site...")
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
                "path": "/"
            }

            if expiry.isdigit() and int(expiry) > 0:
                cookie["expiry"] = int(expiry)

            try:
                driver.add_cookie(cookie)
            except:
                continue

    driver.refresh()
    time.sleep(6)

    print("Current URL after login:", driver.current_url)

    if "login" in driver.current_url.lower():
        print("Login failed. Cookies expired.")
        return False

    print("Login successful.")
    take_screenshot(driver, "after_cookies")
    return True


# ================= COLLECT POSTS =================
def collect_posts(driver, max_pages=5):
    post_urls = set()

    for page in range(max_pages):
        print("Processing page", page + 1, "/", max_pages)

        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'story.php') or contains(@href,'/posts/')]"
        )

        for a in links:
            href = a.get_attribute("href")
            if href:
                clean = href.split("&")[0]
                post_urls.add(clean)

        try:
            more_btn = driver.find_element(
                By.XPATH,
                "//a[contains(text(),'See more results')]"
            )
            more_btn.click()
            time.sleep(5)
        except:
            print("No more pages found.")
            break

    take_screenshot(driver, "after_collection")
    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    try:
        if not load_cookies(driver):
            return

        print("Opening mbasic search page...")
        driver.get(SEARCH_URL)
        time.sleep(6)

        take_screenshot(driver, "after_search")

        if "login" in driver.current_url.lower():
            print("Redirected to login. Session invalid.")
            return

        posts = collect_posts(driver)

        print("\n========== POSTS FOUND ==========\n")

        for i, url in enumerate(sorted(posts), start=1):
            print(str(i) + ". " + url)

        print("\nTotal posts collected:", len(posts))

    except Exception as e:
        print("Error occurred:", str(e))
        take_screenshot(driver, "error_state")

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    run()
