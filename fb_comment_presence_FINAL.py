import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


TEST_URL = "https://www.facebook.com/photo/?fbid=4168798373434713"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")


def init_driver():
    options = Options()
    options.add_argument("--window-size=1200,900")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(4)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        driver.add_cookie({
                            "name": parts[5],
                            "value": parts[6],
                            "domain": ".facebook.com"
                        })

    driver.refresh()
    time.sleep(5)


def to_mbasic(url):
    return url.replace("www.facebook.com", "mbasic.facebook.com")


def run():
    driver = init_driver()
    load_cookies(driver)

    mbasic_url = to_mbasic(TEST_URL)
    print("\nOPENING URL:")
    print(mbasic_url)

    driver.get(mbasic_url)
    time.sleep(6)

    # Scroll a few times
    for i in range(3):
        driver.execute_script("window.scrollBy(0, 1200)")
        time.sleep(2)

    print("\n==============================")
    print("TRY 1: div id starts with comment_")
    print("==============================")

    blocks = driver.find_elements(By.XPATH, "//div[starts-with(@id,'comment_')]")
    print("Found blocks:", len(blocks))

    for i, b in enumerate(blocks, 1):
        print(f"\n[BLOCK {i}]")
        print(b.text)

    print("\n==============================")
    print("TRY 2: any <strong> (names)")
    print("==============================")

    strongs = driver.find_elements(By.TAG_NAME, "strong")
    for i, s in enumerate(strongs, 1):
        print(f"[STRONG {i}]: {s.text}")

    print("\n==============================")
    print("TRY 3: BODY TEXT (first 3000 chars)")
    print("==============================")

    body_text = driver.find_element(By.TAG_NAME, "body").text
    print(body_text[:3000])

    driver.quit()
    print("\nDONE")


if __name__ == "__main__":
    run()
