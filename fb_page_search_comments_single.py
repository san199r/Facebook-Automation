import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


PAGE_URL = "https://www.facebook.com/dealmachineapp/"
KEYWORD = "probate"


# ---------------- DRIVER SETUP ----------------
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 25)


# ---------------- OPEN PAGE ----------------
print("Opening Facebook page...")
driver.get(PAGE_URL)
time.sleep(6)


# ---------------- CLICK PAGE SEARCH ----------------
print("Clicking page search button...")
search_button = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, "//div[@aria-label='Search']")
    )
)
search_button.click()
time.sleep(2)


# ---------------- ENTER KEYWORD ----------------
print("Searching keyword:", KEYWORD)
search_input = wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//input[@aria-label='Search this Page']")
    )
)

search_input.clear()
search_input.send_keys(KEYWORD)
search_input.send_keys(Keys.ENTER)
time.sleep(6)


# ---------------- OPEN POSTS FROM RESULTS ----------------
print("Locating posts from search results...")
posts = driver.find_elements(
    By.XPATH,
    "//a[contains(@href,'/posts/') or contains(@href,'/permalink/')]"
)

print("Posts found:", len(posts))

post_links = []
for p in posts:
    link = p.get_attribute("href")
    if link and link not in post_links:
        post_links.append(link)


# ---------------- PROCESS EACH POST ----------------
for post_url in post_links[:5]:   # limit to first 5 for safety
    print("\nOpening post:", post_url)
    driver.get(post_url)
    time.sleep(6)

    # scroll to load comments
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

    comments = driver.find_elements(
        By.XPATH,
        "//div[@aria-label='Comment']"
    )

    print("Comments found:", len(comments))

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
            print("User Profile:", user.get_attribute("href"))

        except Exception:
            continue


print("\nTest completed. Browser will stay open for 15 seconds.")
time.sleep(15)
driver.quit()
