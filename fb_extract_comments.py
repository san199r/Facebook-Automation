import os
import time
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
INPUT_EXCEL = "fb_probate_results_20260207_121718.xlsx"
OUTPUT_EXCEL = "fb_probate_comments_extracted.xlsx"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

MAX_POSTS = 20
SCROLL_COMMENTS = 6


# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except Exception:
        print(text.encode("ascii", errors="ignore").decode())


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_driver_with_cookies():
    driver = init_driver()
    driver.get("https://www.facebook.com/")
    time.sleep(4)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        driver.add_cookie({
                            "name": parts[5],
                            "value": parts[6],
                            "domain": parts[0]
                        })
        driver.refresh()
        time.sleep(6)
        safe_print("Cookies loaded successfully")

    return driver


# ================= READ POST URLS =================
def read_post_urls():
    wb = load_workbook(INPUT_EXCEL)
    ws = wb.active

    headers = [cell.value for cell in ws[1]]
    post_col = headers.index("Post URL") + 1

    urls = []
    for row in ws.iter_rows(min_row=2):
        if len(urls) >= MAX_POSTS:
            break
        if row[post_col - 1].value:
            urls.append(row[post_col - 1].value)

    return urls


# ================= EXTRACT COMMENTS =================
def extract_comments(driver, post_url, ws_out):
    safe_print(f"Opening post: {post_url}")
    driver.get(post_url)
    time.sleep(8)

    # Scroll to load comments
    for _ in range(SCROLL_COMMENTS):
        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(3)

    comments = driver.find_elements(
        By.XPATH,
        "//div[@role='article']//span[contains(@class,'x1lliihq')]"
    )

    for c in comments:
        try:
            text = c.text.strip()
            if not text:
                continue

            parent = c.find_element(By.XPATH, "./ancestor::div[@role='article']")
            profile = parent.find_element(By.XPATH, ".//a[@role='link']")

            name = profile.text.strip()
            profile_url = profile.get_attribute("href")

            ws_out.append([
                post_url,
                name,
                profile_url,
                text
            ])

        except Exception:
            continue


# ================= MAIN =================
def run():
    driver = load_driver_with_cookies()

    post_urls = read_post_urls()
    safe_print(f"Processing {len(post_urls)} posts")

    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = "Comments"

    ws_out.append([
        "Post URL",
        "Commenter Name",
        "Commenter Profile URL",
        "Comment Text"
    ])

    for cell in ws_out[1]:
        cell.font = Font(bold=True)

    for url in post_urls:
        extract_comments(driver, url, ws_out)

    wb_out.save(OUTPUT_EXCEL)
    safe_print(f"Comments extracted and saved to {OUTPUT_EXCEL}")

    driver.quit()


if __name__ == "__main__":
    run()
