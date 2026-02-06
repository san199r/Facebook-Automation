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

wait = WebDriverWait(driver, 30)


# ---------------- OPEN PAGE ----------------
print("Opening Facebook page...")
driver.get(PAGE_URL)
time.sleep(8)


# ---------------- CLICK SEARCH (YOUR XPATH) ----------------
print("Clicking Search using provided XPath...")

try:
    search_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div/div[2]//span[text()='Search']")
        )
    )
    search_button.click()
    time.sleep(3)
    print("Search button clicked")

except Exception as e:
    print("Search button NOT found using provided XPath")
    print(e)
    driver.quit()
    exit(1)


# ---------------- ENTER KEYWORD ----------------
print("Entering keyword:", KEYWORD)

try:
    search_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@aria-label='Search this Page']")
        )
    )

    search_input.clear()
    search_input.send_keys(KEYWORD)
    search_input.send_keys(Keys.ENTER)
    time.sleep(8)

except Exception as e:
    print("Search input not found")
    print(e)
    driver.quit()
    exit(1)


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

print("Posts found:", len(post_links))


# ---------------- PROCESS POSTS ----------------
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
            print("User Profile URL:", user.get_attribute("href"))

        except Exception:
            continue


print("\nTest finished. Browser will stay open for 15 seconds.")
time.sleep(15)
driver.quit()
