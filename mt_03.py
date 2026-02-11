import os
import time
import sys
import pandas as pd
from openpyxl import load_workbook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG =================
INPUT_EXCEL = "clean_posts.xlsx"
OUTPUT_EXCEL = "fb_comments_structured.xlsx"
COOKIE_FILE = "cookies/facebook_cookies.txt"

FILTER_KEYWORD = ""   # put "probate" if you want filtering

# ================= UTF-8 FIX =================
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# ================= SAFE PRINT =================
def safe_print(text):
    try:
        print(text)
    except:
        print(text.encode("ascii", errors="ignore").decode())

# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ================= LOAD COOKIES =================
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

    print("Login URL:", driver.current_url)

# ================= READ POST URLS =================
def read_urls():
    wb = load_workbook(INPUT_EXCEL)
    ws = wb.active

    urls = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            urls.append(row[0])

    print("Total Posts:", len(urls))
    return urls

# ================= EXPAND COMMENTS =================
def expand_comments(driver):
    while True:
        try:
            more = driver.find_element(By.XPATH, "//span[contains(text(),'View more comments')]")
            driver.execute_script("arguments[0].click();", more)
            time.sleep(2)
        except:
            break

# ================= EXTRACT STRUCTURED COMMENTS =================
def extract_comments(driver, post_url):

    print("\nOpening:", post_url)

    driver.get(post_url)
    time.sleep(6)

    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    expand_comments(driver)

    # JS structured extraction
    comments = driver.execute_script("""
        let results = [];
        document.querySelectorAll('[aria-label="Comment"]').forEach(block => {

            let name = "";
            let text = "";

            let anchor = block.querySelector("a");
            if(anchor){
                name = anchor.innerText;
            }

            let textDiv = block.querySelector('div[dir="auto"]');
            if(textDiv){
                text = textDiv.innerText;
            }

            if(name && text){
                results.push({name: name, comment: text});
            }
        });
        return results;
    """)

    print("Extracted:", len(comments))

    return comments

# ================= MAIN =================
def run():
    driver = init_driver()
    load_cookies(driver)

    urls = read_urls()

    all_data = []

    for i, url in enumerate(urls, 1):
        print(f"Processing {i}/{len(urls)}")

        comments = extract_comments(driver, url)

        for c in comments:
            if FILTER_KEYWORD:
                if FILTER_KEYWORD.lower() not in c["comment"].lower():
                    continue

            all_data.append({
                "Post URL": url,
                "Commenter Name": c["name"],
                "Comment Text": c["comment"]
            })

        time.sleep(3)

    driver.quit()

    # Remove duplicates
    df = pd.DataFrame(all_data)
    df.drop_duplicates(inplace=True)

    df.to_excel(OUTPUT_EXCEL, index=False)

    print("\nSaved:", OUTPUT_EXCEL)
    print("Total Unique Comments:", len(df))


if __name__ == "__main__":
    run()
