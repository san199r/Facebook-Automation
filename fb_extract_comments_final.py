import os
import time
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
KEYWORD = "probate"
SOURCE = "Facebook"

INPUT_EXCEL = "output/fb_probate_ALL_posts_20260207_134513.xlsx"
FINAL_EXCEL = "fb_comments_final.xlsx"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

MAX_POSTS = 20

# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1200,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ================= LOAD COOKIES =================
def load_driver_with_cookies():
    driver = init_driver()
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    driver.add_cookie({
                        "name": parts[5],
                        "value": parts[6],
                        "domain": ".facebook.com"
                    })
        driver.refresh()
        time.sleep(5)

    print("Cookies loaded")
    return driver

# ================= READ POST URLS =================
def read_post_urls():
    wb = load_workbook(INPUT_EXCEL)
    ws = wb.active

    headers = [c.value for c in ws[1]]
    col = headers.index("Post URL") + 1

    urls = []
    for row in ws.iter_rows(min_row=2):
        if len(urls) >= MAX_POSTS:
            break
        val = row[col - 1].value
        if val:
            urls.append(val)

    return urls

# ================= EXTRACT COMMENTS =================
def extract_comments(driver, post_url, ws):
    fbid = post_url.split("fbid=")[-1]
    mbasic_url = f"https://mbasic.facebook.com/photo.php?fbid={fbid}"

    print(f"Opening: {mbasic_url}")
    driver.get(mbasic_url)
    time.sleep(5)

    comment_blocks = driver.find_elements(By.XPATH, "//div[contains(@id,'comment')]")

    if not comment_blocks:
        ws.append([
            SOURCE, KEYWORD, "",
            "NO_COMMENTS",
            post_url,
            "NO_COMMENTS",
            "", "", "", "", ""
        ])
        return

    for block in comment_blocks:
        try:
            name = block.find_element(By.XPATH, ".//h3").text.strip()
            comment = block.find_element(By.XPATH, ".//div[starts-with(@id,'comment')]").text.strip()

            ws.append([
                SOURCE,
                KEYWORD,
                "",
                name,
                post_url,
                comment,
                "",
                "",
                "",
                "",
                ""
            ])
        except Exception:
            continue

# ================= MAIN =================
def run():
    driver = load_driver_with_cookies()
    post_urls = read_post_urls()

    wb = Workbook()
    ws = wb.active
    ws.title = "Comments"

    headers = [
        "Source", "Keyword", "Group",
        "Commenter Name", "Url to find the Comment",
        "Comment", "CHATGPT response for Comment",
        "First Name of the Responder1",
        "Last Name of the Responder1",
        "Comment",
        "CHATGPT response for Comments Reponse"
    ]

    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for url in post_urls:
        extract_comments(driver, url, ws)

    wb.save(FINAL_EXCEL)
    print("EXCEL SAVED:", FINAL_EXCEL)
    driver.quit()

if __name__ == "__main__":
    run()
