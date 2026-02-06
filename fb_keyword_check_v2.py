import time
import os
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
INPUT_EXCEL = "UseApolloIo_followers.xlsx"
KEYWORD = "probate"

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR,
    "fb_probate_comments.xlsx"
)


# ================= READ EXCEL =================
df = pd.read_excel(INPUT_EXCEL)

url_column = None
for col in df.columns:
    if "facebook" in col.lower() and "url" in col.lower():
        url_column = col
        break

if not url_column:
    raise Exception("❌ Facebook URL column not found in Excel")

print(f"✅ Using URL column: {url_column}")


# ================= DRIVER SETUP =================
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


def smart_scroll(times=6):
    for _ in range(times):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(3)


# ================= MAIN LOGIC =================
results = []

for index, row in df.iterrows():
    page_url = str(row[url_column]).strip()
    print(f"\n🔍 Opening: {page_url}")

    if not page_url.startswith("http"):
        continue

    try:
        driver.get(page_url)
        time.sleep(6)
        smart_scroll()

        comments = driver.find_elements(
            By.XPATH,
            "//div[@aria-label='Comment']"
        )

        for comment in comments:
            try:
                text = comment.text.strip()

                if KEYWORD.lower() not in text.lower():
                    continue

                user = comment.find_element(
                    By.XPATH,
                    ".//a[contains(@href,'facebook.com')]"
                )

                results.append({
                    "Page URL": page_url,
                    "Keyword": KEYWORD,
                    "Comment Text": text,
                    "Commenter Name": user.text,
                    "Commenter Profile URL": user.get_attribute("href")
                })

                print(f"✔ Found keyword comment by: {user.text}")

            except Exception:
                continue

    except Exception as e:
        print("⚠ Error:", e)


# ================= SAVE OUTPUT =================
out_df = pd.DataFrame(results)
out_df.to_excel(OUTPUT_EXCEL, index=False)

driver.quit()

print(f"\n✅ Output saved at: {OUTPUT_EXCEL}")
