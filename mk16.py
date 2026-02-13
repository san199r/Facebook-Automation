import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"
SEARCH_URL = f"https://www.facebook.com/search/posts/?q={KEYWORD}"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")


# ================= DRIVER =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    # For Jenkins use headless:
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.set_page_load_timeout(60)
    return driver


# ================= LOAD COOKIES =================
def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        print("❌ Cookie file not found.")
        return False

    print("Opening Facebook homepage...")
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    print("Injecting cookies...")

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

    print("Cookies loaded successfully.")
    return True


# ================= COLLECT POSTS =================
def collect_posts(driver, scrolls=10):
    post_urls = set()

    for i in range(scrolls):
        print(f"Scrolling {i+1}/{scrolls}")

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

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)

    return post_urls


# ================= MAIN =================
def run():
    driver = init_driver()

    try:
        if not load_cookies(driver):
            return

        print("Opening search page...")
        driver.get(SEARCH_URL)
        time.sleep(8)

        posts = collect_posts(driver)

        print("\n================ POSTS FOUND ================\n")

        for i, url in enumerate(sorted(posts), start=1):
            print(f"{i}. {url}")

        print("\nTotal posts collected:", len(posts))

    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    run()
