import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

COOKIE_FILE = "cookies/facebook_cookies.txt"
POST_URL = "https://www.facebook.com/photo/?fbid=26415314134719160"

def init_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

def load_cookies(driver):
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    if not os.path.exists(COOKIE_FILE):
        print("Cookie file not found!")
        return

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as file:
        for line in file:
            if line.startswith("#") or not line.strip():
                continue

            parts = line.strip().split("\t")
            if len(parts) >= 7:
                cookie = {
                    "domain": parts[0],
                    "name": parts[5],
                    "value": parts[6],
                    "path": parts[2],
                }
                try:
                    driver.add_cookie(cookie)
                except:
                    pass

    driver.refresh()
    time.sleep(5)

    print("After login URL:", driver.current_url)
    print("Page title:", driver.title)

def run():
    driver = init_driver()

    # Inject cookies
    load_cookies(driver)

    # Open test post
    driver.get(POST_URL)
    time.sleep(6)

    # Scroll
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    # Try to expand comments
    while True:
        try:
            more = driver.find_element(By.XPATH, "//span[contains(text(),'View more comments')]")
            driver.execute_script("arguments[0].click();", more)
            time.sleep(2)
        except:
            break

    # Extract comments using JS
    comments = driver.execute_script("""
        let data = [];
        document.querySelectorAll('div[dir="auto"]').forEach(el => {
            if(el.innerText.length > 5) {
                data.push(el.innerText);
            }
        });
        return data;
    """)

    print("\nTotal detected blocks:", len(comments))

    for c in comments[:10]:
        print("\n---")
        print(c)

    input("\nPress ENTER to close...")
    driver.quit()

if __name__ == "__main__":
    run()
