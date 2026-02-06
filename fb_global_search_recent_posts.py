import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


SEARCH_URL = "https://www.facebook.com/search/posts/?q=probate"
KEYWORD = "probate"


# ---------------- DRIVER SETUP ----------------
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


# ---------------- OPEN RECENT POSTS SEARCH ----------------
print("Opening Facebook RECENT POSTS search...")
driver.get(SEARCH_URL)
time.sleep(10)


# ---------------- SCROLL TO LOAD POSTS ----------------
print("Scrolling to load posts...")

for _ in range(6):
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

print(f"Total posts found: {len(post_links)}")


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


print("\nProcess completed. Browser stays open for 15 seconds.")
time.sleep(15)
driver.quit()
