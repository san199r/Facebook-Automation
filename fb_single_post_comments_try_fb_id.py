import os
import time
import re
from datetime import datetime

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"
INPUT_EXCEL = "output/fb_probate_ALL_posts_20260209_110948.xlsx"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")
OUTPUT_DIR = "output"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, f"fb_CLEAN_comments_{TIMESTAMP}.xlsx")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def init_driver():
    options = Options()
    options.add_argument("--window-size=1200,900")
    options.add_argument("--disable-notifications")
    # Adding a mobile User-Agent helps mbasic stay stable
    options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        driver.add_cookie({"name": parts[5], "value": parts[6], "domain": ".facebook.com"})
    driver.refresh()

def expand_page(driver):
    """Clicks 'View more comments' and 'See more' text expansions."""
    # Expand 'View more' comments
    for _ in range(15):
        try:
            more_link = driver.find_element(By.XPATH, "//a[contains(@href, 'pager')]")
            more_link.click()
            time.sleep(2)
        except:
            break

    # Click all 'See more' links to expand long probate stories
    see_mores = driver.find_elements(By.LINK_TEXT, "See more")
    for link in see_mores:
        try:
            driver.execute_script("arguments[0].click();", link)
        except:
            pass

def extract_structured_comments(driver):
    """Target specific HTML containers to avoid UI junk like '15h' or 'View replies'."""
    # On mbasic, each comment is usually in a div that contains an h3 (the name)
    # We find all divs that have an h3 child.
    found_data = []
    comment_blocks = driver.find_elements(By.XPATH, "//div[h3 and div]")

    for block in comment_blocks:
        try:
            author = block.find_element(By.TAG_NAME, "h3").text.strip()
            
            # The actual comment text is in a div that isn't the footer/action bar
            # We look for the div that contains the actual text
            content_div = block.find_element(By.XPATH, "./div[1]")
            content = content_div.text.strip()

            # Identify if it's a reply by checking for indentation (margin-left)
            style = block.get_attribute("style") or ""
            ctype = "REPLY" if "margin-left" in style.lower() or "padding-left" in style.lower() else "COMMENT"

            # Clean up: Ignore system blocks
            if author and content and "View all" not in author and "replied" not in author.lower():
                found_data.append({
                    "author": author,
                    "content": content,
                    "type": ctype
                })
        except NoSuchElementException:
            continue
            
    return found_data

def run():
    wb_in = load_workbook(INPUT_EXCEL)
    ws_in = wb_in.active
    
    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.append(["Source", "Keyword", "Commentator", "Comment", "Type", "Post URL"])
    
    driver = init_driver()
    load_cookies(driver)

    try:
        for row in ws_in.iter_rows(min_row=2, values_only=True):
            post_url = row[1]
            if not post_url: continue
            
            m_url = post_url.replace("www.facebook.com", "mbasic.facebook.com")
            print(f"Scraping: {m_url}")
            driver.get(m_url)
            time.sleep(3)
            
            expand_page(driver)
            comments = extract_structured_comments(driver)
            
            for c in comments:
                ws_out.append([SOURCE, KEYWORD, c['author'], c['content'], c['type'], post_url])
                
    finally:
        wb_out.save(OUTPUT_EXCEL)
        driver.quit()
        print(f"Finished! Clean data saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    run()
