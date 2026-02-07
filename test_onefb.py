import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_URL = "https://mbasic.facebook.com/photo.php?fbid=1424104163059216"


def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1200,900")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def load_driver_with_cookies():
    driver = init_driver()
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        driver.add_cookie({
                            "name": parts[5],
                            "value": parts[6],
                            "domain": parts[0]
                        })

        driver.refresh()
        time.sleep(4)
        print("Cookies loaded")

    return driver


def extract_comments(driver):
    driver.get(TEST_URL)
    time.sleep(6)

    # Scroll slowly to load comments
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(2)

    # 📸 TAKE SCREENSHOT
    screenshot_path = os.path.join(OUTPUT_DIR, "mbasic_test_post.png")
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved at: {screenshot_path}")

    comment_blocks = driver.find_elements(By.XPATH, "//div[@data-ft]")

    if not comment_blocks:
        print("NO_COMMENTS")
        return

    print(f"Found {len(comment_blocks)} comment blocks\n")

    for block in comment_blocks:
        try:
            name = block.find_element(By.XPATH, ".//h3").text.strip()
            comment = block.find_element(
                By.XPATH,
                ".//div[starts-with(@id,'comment')]"
            ).text.strip()

            if comment:
                print("NAME   :", name)
                print("COMMENT:", comment)
                print("-" * 50)

        except Exception:
            continue


if __name__ == "__main__":
    driver = load_driver_with_cookies()
    extract_comments(driver)
    driver.quit()
