import os
import time
import re
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ================= CONFIG =================
SOURCE = "FB"
KEYWORD = "PROBATE"

INPUT_EXCEL = "fb_probate_ALL_posts_20260210_115220.xlsx"
POST_URL_COLUMN = "Post URL"   # change ONLY if column name differs

COOKIE_FILE = os.path.join("cookies", "facebook_cookies.txt")

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(
    OUTPUT_DIR, f"fb_ALL_posts_comments_{TIMESTAMP}.xlsx"
)


# ================= DRIVER =================
def init_driver():
    options = Options()
    options.add_argument("--window-size=412,915")
    options.add_argument("--disable-notifications")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Linux; Android 10; SM-G960U) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.6099.224 Mobile Safari/537.36"
    )

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


# ================= COOKIES =================
def load_cookies(driver):
    driver.get("https://mbasic.facebook.com/")
    time.sleep(3)

    if not os.path.exists(COOKIE_FILE):
        return

    with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                p = line.strip().split("\t")
                if len(p) >= 7:
                    driver.add_cookie({
                        "name": p[5],
                        "value": p[6],
                        "domain": ".facebook.com"
                    })

    driver.refresh()
    time.sleep(4)


# ================= HELPERS =================
def to_mbasic(url):
    return url.replace("www.facebook.com", "mbasic.facebook.com").replace(
        "photo/?", "photo.php?"
    )


def is_timestamp(text):
    """Detect Facebook timestamp patterns like 'Jan 5, 2024' or '2h' or 'Just now'"""
    t = text.lower().strip()
    if re.match(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}", t
    ):
        return True
    if re.match(r"^\d+\s*(h|hr|hrs|min|mins|d|w|m|y)\b", t):
        return True
    if t in ("just now", "yesterday"):
        return True
    return False


def is_ui_noise(text):
    """Filter out Facebook UI chrome — buttons, icons, reaction counts, etc."""
    t = text.strip()

    # Pure symbols / numbers
    if re.match(r"^[\W_]+$", t):
        return True
    if re.match(r"^\d+$", t):
        return True

    # Reaction / action labels
    ui_words = {
        "like", "reply", "share", "watch", "follow", "send",
        "more", "see more", "view more", "load more",
        "write a comment", "comment", "reactions",
        "top comments", "most relevant", "newest", "all comments",
        "hide", "report", "unlike", "love", "haha", "wow", "sad", "angry",
    }
    if t.lower() in ui_words:
        return True

    # Private emoji-only lines
    if re.match(r"^[\uE000-\uF8FF\U0001F300-\U0001FAFF\s]+$", t):
        return True

    return False


def has_real_text(text):
    return bool(re.search(r"[A-Za-z]", text))


def looks_like_name(text):
    """
    Improved name detection:
    - 1–5 words
    - Each word starts with uppercase OR is a known lowercase particle
    - No sentence-ending punctuation (names don't end with periods, ?, !)
    - Not a known UI phrase
    """
    t = text.strip()

    if not has_real_text(t):
        return False

    # Names don't end with sentence punctuation
    if re.search(r"[.?!]$", t):
        return False

    words = t.split()
    if not (1 <= len(words) <= 5):
        return False

    # Allow particles like "de", "van", "la", "le", "el", "bin", "binti", "al"
    particles = {"de", "van", "la", "le", "el", "bin", "binti", "al", "da", "do", "del", "von"}

    for word in words:
        clean = re.sub(r"[^A-Za-z]", "", word)
        if not clean:
            continue
        if clean.lower() in particles:
            continue
        if not clean[0].isupper():
            return False

    return True


# ================= LOAD COMMENTS =================
def open_comment_section(driver):
    try:
        link = driver.find_element(
            By.XPATH, "//a[text()='Comment' or contains(text(),'Comment')]"
        )
        href = link.get_attribute("href")
        if href:
            driver.get(href)
            time.sleep(2)
    except:
        pass


def load_all_comments(driver):
    while True:
        try:
            more = driver.find_element(
                By.XPATH,
                "//a[contains(text(),'View more comments') or "
                "contains(text(),'See more comments') or "
                "contains(text(),'Load more comments')]"
            )
            href = more.get_attribute("href")
            if not href:
                break
            driver.get(href)
            time.sleep(2)
        except:
            break


# ================= IMPROVED STATEFUL PARSER =================
def parse_comments(body_text):
    """
    Improved parser:
    - Accumulates multi-line comment text (fixes truncated comments)
    - Broader name detection (handles particles, varied capitalisation)
    - Skips timestamps and UI noise before deciding name vs. comment
    """
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]

    results = []
    current_name = None
    comment_lines = []  # accumulate lines belonging to one comment

    def flush():
        """Save the buffered comment for the current name."""
        if current_name and comment_lines:
            full_comment = " ".join(comment_lines).strip()
            if has_real_text(full_comment):
                results.append((current_name, full_comment))

    for line in lines:
        # Always skip timestamps and UI noise
        if is_timestamp(line) or is_ui_noise(line):
            continue

        if looks_like_name(line):
            # Save whatever we buffered for the previous commenter
            flush()
            current_name = line
            comment_lines = []
        elif current_name:
            # Accumulate lines as part of the current comment
            comment_lines.append(line)
        # If no name detected yet, we skip (post body / header text)

    # Don't forget the last buffered comment
    flush()

    return results


# ================= READ POST URLS =================
def read_post_urls():
    wb = load_workbook(INPUT_EXCEL)
    ws = wb.active

    headers = [c.value for c in ws[1]]
    idx = headers.index(POST_URL_COLUMN)

    urls = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[idx]:
            urls.append(row[idx])

    return urls


# ================= MAIN =================
def run():
    post_urls = read_post_urls()
    print("Total posts:", len(post_urls))

    driver = init_driver()
    load_cookies(driver)

    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = "Comments"

    headers = ["Source", "Keyword", "Commentator", "Comment", "Post URL"]
    ws_out.append(headers)
    for c in ws_out[1]:
        c.font = Font(bold=True)

    total_comments = 0

    for idx, post_url in enumerate(post_urls, 1):
        print(f"[{idx}/{len(post_urls)}] Processing:", post_url)

        driver.get(to_mbasic(post_url))
        time.sleep(3)

        open_comment_section(driver)
        load_all_comments(driver)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        comments = parse_comments(body_text)

        if not comments:
            ws_out.append([SOURCE, KEYWORD, "NO_COMMENTS", "NO_COMMENTS", post_url])
            print("  -> No comments found")
            continue

        for name, comment in comments:
            ws_out.append([SOURCE, KEYWORD, name, comment, post_url])
            total_comments += 1

        print(f"  -> {len(comments)} comments captured")

    driver.quit()
    wb_out.save(OUTPUT_EXCEL)

    print("===================================")
    print("DONE")
    print("Total comments:", total_comments)
    print("Output Excel:", OUTPUT_EXCEL)
    print("===================================")


if __name__ == "__main__":
    run()
