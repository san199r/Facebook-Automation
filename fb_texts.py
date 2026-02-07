import os
import time
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except Exception:
        print(text.encode("ascii", errors="ignore").decode())


# ================= CONFIG =================
KEYWORD = "probate"

SEARCH_URLS = {
    "top":   f"https://www.facebook.com/search/top?q={KEYWORD}",
    "posts": f"https://www.facebook.com/search/posts?q={KEYWORD}",
}

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs("cookies", exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_{KEYWORD}_TEXT_posts_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= LOAD COOKIES =================
def load_cookies():
    driver = init_driver()
    driver.get("https://www.facebook.com/")
    time.sleep(5)

    if not os.path.exists(COOKIE_FILE):
        safe_print("Cookie file not found")
        return driver

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
    time.sleep(8)
    safe_print("Cookies loaded successfully")

    return driver


# ================= COLLECT ONLY TEXT POSTS =================
def collect_text_post_urls(driver, source_name, scrolls=12):
    post_urls = set()

    for i in range(scrolls):
        safe_print(f"[{source_name}] Scroll {i+1}/{scrolls}")
        time.sleep(3)

        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"{source_name}_scroll_{i+1:02d}.png")
        )

        # JS-based extraction – TEXT POSTS ONLY
        urls = driver.execute_script("""
            let results = new Set();
            document.querySelectorAll('a').forEach(a => {
                if (!a.href) return;

                if (
                    a.href.includes('/posts/') ||
                    a.href.includes('permalink.php')
                ) {
                    results.add(a.href);
                }
            });
            return Array.from(results);
        """)

        for href in urls:
            if "/posts/" in href:
                clean = href.split("?")[0]
            elif "permalink.php" in href:
                clean = href.split("&")[0]
            else:
                continue

            post_urls.add(clean)

        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"{source_name}_collect_{i+1:02d}.png")
        )

        driver.execute_script("window.scrollBy(0, 1800);")
        time.sleep(4)

    return post_urls


# ================= MAIN =================
def run():
    driver = load_cookies()
    all_posts = set()

    try:
        for source, url in SEARCH_URLS.items():
            safe_print(f"Opening {source.upper()} search")
            driver.get(url)
            time.sleep(10)

            driver.save_screenshot(
                os.path.join(SCREENSHOT_DIR, f"{source}_start_{TIMESTAMP}.png")
            )

            urls = collect_text_post_urls(driver, source_name=source)
            all_posts.update(urls)

        wb = Workbook()
        ws = wb.active
        ws.title = "Text Posts Only"

        ws.append(["S.No", "Post URL"])
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for i, url in enumerate(sorted(all_posts), 1):
            ws.append([i, url])

        wb.save(OUTPUT_EXCEL)

        safe_print(f"TOTAL TEXT POSTS COLLECTED: {len(all_posts)}")
        safe_print(f"Excel saved at: {OUTPUT_EXCEL}")

        driver.save_screenshot(
            os.path.join(SCREENSHOT_DIR, f"final_{TIMESTAMP}.png")
        )

    finally:
        driver.quit()


if __name__ == "__main__":
    run()
