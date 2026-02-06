import os
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
KEYWORD = "probate"

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"facebook_posts_{KEYWORD}_{TIMESTAMP}.xlsx"
)


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


# ================= EXCEL =================
def init_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Posts"

    bold = Font(bold=True)
    ws.append(["S.No", "Post URL"])
    ws["A1"].font = bold
    ws["B1"].font = bold

    return wb, ws


# ================= MAIN LOGIC =================
def run():
    driver = init_driver()
    wait = WebDriverWait(driver, 30)

    # STEP 1: Open Facebook (already logged in)
    driver.get("https://www.facebook.com/")
    time.sleep(10)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"01_facebook_home_{TIMESTAMP}.png")
    )

    # STEP 2: Search for keyword
    search_box = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Search Facebook']")
        )
    )
    search_box.clear()
    search_box.send_keys(KEYWORD)
    search_box.send_keys(Keys.ENTER)

    time.sleep(10)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"02_after_search_{TIMESTAMP}.png")
    )

    # STEP 3: Click "Posts" tab
    posts_tab = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[text()='Posts']/ancestor::a")
        )
    )
    driver.execute_script("arguments[0].click();", posts_tab)

    time.sleep(10)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"03_posts_tab_{TIMESTAMP}.png")
    )

    # STEP 4: Scroll & collect post URLs
    post_urls = set()

    for i in range(10):
        print(f"Scrolling {i + 1}/10")

        articles = driver.find_elements(By.XPATH, "//div[@role='article']")
        print("Articles visible:", len(articles))

        for article in articles:
            try:
                links = article.find_elements(By.XPATH, ".//a[@href]")
                for a in links:
                    href = a.get_attribute("href")
                    if not href:
                        continue

                    clean = href.split("?")[0]

                    if (
                        "/posts/" in clean
                        or "permalink.php" in clean
                        or "story_fbid=" in clean
                    ):
                        post_urls.add(clean)
            except Exception:
                continue

        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(6)

    # STEP 5: Save to Excel
    wb, ws = init_excel()
    for idx, url in enumerate(sorted(post_urls), start=1):
        ws.append([idx, url])

    wb.save(OUTPUT_EXCEL)

    print("Total posts collected:", len(post_urls))
    print("Excel saved:", OUTPUT_EXCEL)

    driver.save_screenshot(
        os.path.join(SCREENSHOT_DIR, f"04_before_close_{TIMESTAMP}.png")
    )

    driver.quit()


# ================= RUN =================
if __name__ == "__main__":
    run()
