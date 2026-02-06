import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


SEARCH_URL = "https://www.facebook.com/search/top?q=probate"
KEYWORD = "probate"


# ---------------- DRIVER SETUP ----------------
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 30)


# ---------------- OPEN SEARCH PAGE ----------------
print("Opening Facebook global search...")
driver.get(SEARCH_URL)
time.sleep(8)


# ---------------- CLICK 'RECENT POSTS' TOGGLE ----------------
print("Trying to enable 'Recent posts' filter...")

try:
    recent_toggle = wait.until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//span[text()='Recent posts']/ancestor::label//input"
        ))
    )

    # Toggle only if not already enabled
    if not recent_toggle.is_selected():
        driver.execute_script("arguments[0].click();", recent_toggle)
        print("Recent posts filter enabled")
    else:
        print("Recent posts filter already enabled")

    time.sleep(6)

except Exception as e:
    print("Recent posts toggle not found or not clickable")
    print(e)
    driver.quit()
    exit(1)


# ---------------- SCROLL SEARCH RESULTS ----------------
print("Scrolling search results...")

for _ in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(4)


# ---------------- COLLECT POST LINKS ----------------
print("Collecting post links...")

posts = driver.find_elements(
    By.XPATH,
    "//a[contains(@href,'/posts/') or contains(@href,'/permalink/')]"
)

post_links = []
for p in posts:
    link = p.get_attribute("href")
    if link and link not in post_links:
        post_links.append(link)

print(f"Total posts collected: {len(post_links)}")


# ---------------- OPEN POSTS & READ COMMENTS ----------------
for post_url in post_links[:5]:
    print("\nOpening post:", post_url)
    driver.get(post_url)
    time.sleep(8)

    for _ in range(4):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    comments = driver.find_elements(
        By.XPATH,
        "//div[@aria-label='Comment']"
    )

    print(f"Comments found: {len(comments)}")

    for c in comments:
        try:
            comment_text = c.text.strip()
            if KEYWORD.lower() not in comment_text.lower():
                continue

            user = c.find_element(
                By.XPATH,
                ".//a[contains(@href,'facebook.com')]"
            )

            print("\nMATCH FOUND")
            print("Post URL:", post_url)
            print("Comment:", comment_text)
            print("User Name:", user.text)
            print("User Profile URL:", user.get_attribute("href"))

        except Exception:
            continue


print("\nProcess finished. Browser will stay open for 15 seconds.")
time.sleep(15)
driver.quit()
