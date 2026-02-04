import os
import re
import time
from urllib.parse import urlparse, parse_qs, unquote

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


# ================= CONFIG =================
START_URL = "https://www.facebook.com/dealmachineapp/followers/"
OUT_XLSX = "facebook_dealmachine_results.xlsx"

HEADERS = [
    "S.No",
    "Facebook Name",
    "Facebook Page URL",
    "Location",
    "Phone",
    "Email",
    "Website",
    "External Facebook",
    "External LinkedIn",
    "External Instagram",
]
# ==========================================


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def init_driver():
    options = webdriver.ChromeOptions()
    
    # --- Jenkins/Headless Requirements ---
    options.add_argument("--headless=new")           # Runs without a GUI
    options.add_argument("--no-sandbox")              # Bypass OS security model (Required for Jenkins/Linux)
    options.add_argument("--disable-dev-shm-usage")   # Overcomes limited resource problems in Docker/VMs
    options.add_argument("--window-size=1920,1080")   # Sets a standard screen size for headless mode
    
    # --- Stealth & Anti-Detection ---
    # Setting a real-looking User-Agent helps prevent immediate blocking by Facebook
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")
    
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # --- Automation Flag Removal ---
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Initialize Service and Driver
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Mask the 'navigator.webdriver' flag to further hide automation
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    driver.set_page_load_timeout(60)
    return driver


# ================= FACEBOOK LOGIN =================
def facebook_login(driver, wait):
    username = os.getenv("FB_USERNAME")
    password = os.getenv("FB_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "FB_USERNAME / FB_PASSWORD not set.\n"
            "Set them as environment variables (or Jenkins credentials)."
        )

    print("🔐 Logging into Facebook...")

    driver.get("https://www.facebook.com/login")
    wait.until(EC.presence_of_element_located((By.ID, "email")))

    driver.find_element(By.ID, "email").send_keys(username)
    driver.find_element(By.ID, "pass").send_keys(password + Keys.ENTER)

    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='navigation']")))
    time.sleep(3)

    print("✅ Facebook login successful")


# ================= EXCEL =================
def load_or_create_workbook(path: str):
    if os.path.exists(path):
        wb = load_workbook(path)
        ws = wb.active
        url_to_row = {}
        processed = set()
        max_sno = 0

        for r in range(2, ws.max_row + 1):
            sno = ws.cell(r, 1).value
            url = ws.cell(r, 3).value

            if sno and str(sno).isdigit():
                max_sno = max(max_sno, int(sno))

            if url:
                url = str(url).strip()
                url_to_row[url] = r
                fields = [ws.cell(r, c).value for c in range(4, 11)]
                if any(v for v in fields):
                    processed.add(url)

        return wb, ws, url_to_row, processed, max_sno + 1

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    bold = Font(bold=True)
    for i, h in enumerate(HEADERS, 1):
        c = ws.cell(1, i, h)
        c.font = bold

    wb.save(path)
    return wb, ws, {}, set(), 1


def upsert_row(wb, ws, path, url_to_row, row):
    url = row[2]
    if url in url_to_row:
        r = url_to_row[url]
        for i, v in enumerate(row, 1):
            ws.cell(r, i).value = v
    else:
        ws.append(row)
        url_to_row[url] = ws.max_row

    wb.save(path)


# ================= SCRAPING =================
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")


def scrape_contact_info(driver):
    location = phone = email = website = ""

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='main']"))
        )
    except TimeoutException:
        return location, phone, email, website

    text = driver.page_source

    m = EMAIL_RE.search(text)
    if m:
        email = m.group(0)

    m = PHONE_RE.search(text)
    if m:
        phone = m.group(1)

    if BeautifulSoup:
        soup = BeautifulSoup(text, "html.parser")
        for a in soup.select("a[href]"):
            h = a["href"]
            if h.startswith("http") and "facebook.com" not in h:
                website = h
                break

    return location, phone, email, website


# ================= MAIN =================
def facebook_dealmachine_scraper():
    driver = init_driver()
    wait = WebDriverWait(driver, 30)

    wb, ws, url_to_row, processed, next_sno = load_or_create_workbook(OUT_XLSX)

    try:
        facebook_login(driver, wait)

        driver.get(START_URL)
        time.sleep(5)

        anchors = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'facebook.com/') and .//span[@dir='auto']]"
        )

        for a in anchors:
            name = normalize_ws(a.text)
            href = a.get_attribute("href")

            if not name or not href or href in processed:
                continue

            driver.execute_script("window.open(arguments[0])", href)
            driver.switch_to.window(driver.window_handles[-1])

            time.sleep(3)
            location, phone, email, website = scrape_contact_info(driver)

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            row = [
                next_sno,
                name,
                href,
                location,
                phone,
                email,
                website,
                "",
                "",
                "",
            ]

            upsert_row(wb, ws, OUT_XLSX, url_to_row, row)
            processed.add(href)
            next_sno += 1

            print(f"✔ Saved: {name}")

    finally:
        wb.save(OUT_XLSX)
        driver.quit()


if __name__ == "__main__":
    facebook_dealmachine_scraper()

