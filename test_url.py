import time
import os
from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
POST_URL = "https://mbasic.facebook.com/photo.php?fbid=122269379360224993"

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT = "fb_comments_replies.xlsx"

# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Linux; Android 10; SM-G960U) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.224 Mobile Safari/537.36"
    )
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

# ================= LOAD COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    if not os.path.exists(COOKIE_FILE):
        print("No cookie file found!")
        return

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
    time.sleep(4)
    print("Cookies loaded")

# ================= CLICK ALL COMMENTS =================
def expand_comments(driver):
    while True:
        try:
            btn = driver.find_element(
                By.XPATH,
                "//a[contains(text(),'View more comments') or contains(text(),'See more comments')]"
            )
            driver.get(btn.get_attribute("href"))
            time.sleep(3)
        except:
            break

# ================= EXTRACT COMMENTS =================
def get_comments(driver):
    data = []

    # each comment block
    comments = driver.find_elements(By.XPATH, "//div[contains(@id,'comment')]")
    for c in comments:
        try:
            text = c.text.strip()
        except:
            text = ""

        # look for reply blocks under this comment
        replies = []
        try:
            reply_elems = c.find_elements(
                By.XPATH, ".//div[contains(@id,'comment') and contains(@data-sigil,'comment-reply')]"
            )
            for r in reply_elems:
                replies.append(r.text.strip())
        except:
            pass

        data.append({
            "comment": text,
            "replies": replies
        })

    return data

# ================= EXCEL =================
def save_excel(data):
    wb = Workbook()
    ws = wb.active
    ws.title = "FB Comments"

    ws.append(["S.No", "Comment", "Replies"])
    for c in ws[1]:
        c.font = Font(bold=True)

    for idx, item in enumerate(data,1):
        replies_joined = " || ".join(item['replies'])
        ws.append([idx, item['comment'], replies_joined])

    wb.save(OUTPUT)
    print("Saved >>", OUTPUT)

# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    print("Opening post...")
    driver.get(POST_URL)
    time.sleep(5)

    print("Expanding comments…")
    expand_comments(driver)

    print("Extracting comments…")
    data = get_comments(driver)

    print("Total comments found:", len(data))

    save_excel(data)

    driver.quit()

if __name__ == "__main__":
    run()
