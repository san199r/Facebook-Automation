import os
import time
import re

from openpyxl import Workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import StaleElementReferenceException

from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
PAGE_URL = "https://www.facebook.com/UseApolloIo/about"
COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXCEL_FILE = os.path.join(
    OUTPUT_DIR,
    "apollo_facebook_page_about.xlsx"
)

HEADERS = [
    "Page Name",
    "Page URL",
    "Website",
    "Email",
    "Phone",
    "Instagram",
    "LinkedIn",
]


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

            if not domain.endswith("facebook.com"):
                continue

            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
            }

            if expiry.isdigit():
                cookie["expiry"] = int(expiry)

            driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(5)


# ================= HELPERS =================
def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def find_text_by_label(driver, label):
    try:
        el = driver.find_element(
            By.XPATH,
            f"//span[text()='{label}']/ancestor::div[1]//span[last()]"
        )
        return normalize(el.text)
    except:
        return ""


def find_social_links(driver):
    links = {"instagram": "", "linkedin": ""}

    try:
        anchors = driver.find_elements(By.XPATH, "//a[@href]")
    except:
        return links

    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            if not links["instagram"] and "instagram.com" in href:
                links["instagram"] = href
            elif not links["linkedin"] and "linkedin.com" in href:
                links["linkedin"] = href
        except StaleElementReferenceException:
            continue

    return links


# ================= MAIN =================
def scrape_page_about():
    driver = init_driver()
    load_facebook_cookies(driver)

    driver.get(PAGE_URL)
    time.sleep(5)

    wb = Workbook()
    ws = wb.active
    ws.title = "Page About"

    bold = Font(bold=True)
    for i, h in enumerate(HEADERS, start=1):
        cell = ws.cell(1, i, h)
        cell.font = bold

    try:
        page_name = driver.find_element(By.XPATH, "//h1").text
    except:
        page_name = "Unknown"

    website = find_text_by_label(driver, "Website")
    email = find_text_by_label(driver, "Email")
    phone = find_text_by_label(driver, "Phone")

    socials = find_social_links(driver)

    ws.append([
        page_name,
        PAGE_URL.replace("/about", ""),
        website,
        email,
        phone,
        socials["instagram"],
        socials["linkedin"],
    ])

    wb.save(EXCEL_FILE)
    driver.quit()

    print("Data extracted successfully:", EXCEL_FILE)


if __name__ == "__main__":
    scrape_page_about()
