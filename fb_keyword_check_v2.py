import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
INPUT_EXCEL = "UseApolloIo_followers.xlsx"
KEYWORD = "probate"
OUTPUT_EXCEL = "UseApolloIo_keyword_check_v2.xlsx"


# ================= READ EXCEL =================
df = pd.read_excel(INPUT_EXCEL)

url_column = None
for col in df.columns:
    if "facebook" in col.lower() and "url" in col.lower():
        url_column = col
        break

if not url_column:
    raise Exception("❌ Facebook URL column not found in Excel")

print(f"✅ Facebook URL column detected: {url_column}")


# ================= DRIVER SETUP =================
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


def smart_scroll(max_scrolls=8):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


# ================= MAIN LOGIC =================
results = []

for idx, row in df.iterrows():
    url = str(row[url_column]).strip()
    print(f"\n🔍 [{idx+1}] Opening: {url}")

    if not url.startswith("http"):
        results.append({
            "Facebook URL": url,
            "Keyword": KEYWORD,
            "Found": "INVALID URL",
            "Snippet": ""
        })
        continue

    try:
        driver.get(url)
        time.sleep(6)

        smart_scroll()

        body_text = driver.find_element(By.TAG_NAME, "body").text
        body_text_lower = body_text.lower()

        if KEYWORD in body_text_lower:
            pos = body_text_lower.find(KEYWORD)
            snippet = body_text[max(0, pos - 60): pos + 60]
            found = "YES"
            print("✅ Keyword FOUND")
        else:
            snippet = ""
            found = "NO"
            print("❌ Keyword NOT found")

        results.append({
            "Facebook URL": url,
            "Keyword": KEYWORD,
            "Found": found,
            "Snippet": snippet
        })

    except Exception as e:
        print("⚠ Error:", e)
        results.append({
            "Facebook URL": url,
            "Keyword": KEYWORD,
            "Found": "ERROR",
            "Snippet": ""
        })


# ================= SAVE OUTPUT =================
out_df = pd.DataFrame(results)
out_df.to_excel(OUTPUT_EXCEL, index=False)

driver.quit()

print(f"\n✅ Output saved successfully: {OUTPUT_EXCEL}")
