import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

KEYWORDS = [
    "probate",
    "estate",
    "will"
]

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


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


# ================= COOKIES =================
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

            try:
                driver.add_cookie(cookie)
            except Exception:
                pass

    driver.refresh()
    time.sleep(5)


# ================= SCREENSHOT =================
def take_screenshot(driver, label):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{label}_{ts}.png")
    driver.save_screenshot(path)
    print(f"Saved screenshot: {path}")


# ================= SEARCH USING SEARCH BOX =================
def search_keyword(driver, keyword):
    print(f"Searching keyword: {keyword}")

    # Facebook global search input (top bar)
    search_input = driver.find_element(
        By.XPATH,
        "//input[@aria-label='Search Facebook']"
    )

    search_input.click()
    time.sleep(1)

    search_input.send_keys(Keys.CONTROL, "a")
    search_input.send_keys(Keys.DELETE)

    search_input.send_keys(keyword)
    search_input.send_keys(Keys.ENTER)

    time.sleep(8)


# ================= MAIN =================
def run():
    driver = init_driver()

    print("Loading Facebook cookies...")
    load_facebook_cookies(driver)

    # ---- VERIFY LOGIN ----
    driver.get("https://www.facebook.com/me")
    time.sleep(5)

    if driver.find_elements(By.XPATH, "//input[@name='email']"):
        take_screenshot(driver, "login_failed")
        print("Login failed. Cookies expired.")
        driver.quit()
        return

    print("Login successful.")
    take_screenshot(driver, "after_login")

    # ---- OPEN HOME ----
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    # ---- SEARCH KEYWORDS ONE BY ONE (CLICK SEARCH AGAIN EACH TIME) ----
    for idx, keyword in enumerate(KEYWORDS, start=1):
        search_keyword(driver, keyword)
        take_screenshot(driver, f"search_{idx}_{keyword}")

    # ---- FINAL ----
    take_screenshot(driver, "before_close")
    driver.quit()
    print("Done.")


# ================= RUN =================
if __name__ == "__main__":
    run()
