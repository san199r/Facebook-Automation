import requests
import re
import json
from datetime import datetime

# ================= CONFIG =================
PAGE_URL = "https://www.facebook.com/nytimes/"   # CHANGE THIS
OUTPUT_FILE = f"fb_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ================= FETCH HTML =================
def fetch_page(url):
    print(f"Fetching: {url}")
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        raise Exception("Failed to fetch page")
    return response.text


# ================= EXTRACT POSTS =================
def extract_posts(html):
    posts = []

    # Find post blocks
    post_ids = re.findall(r'"post_id":"(\d+)"', html)

    for pid in set(post_ids):
        post_data = {}

        post_data["post_id"] = pid
        post_data["post_url"] = f"https://www.facebook.com/{pid}"

        # Extract reactions
        likes_match = re.search(rf'"post_id":"{pid}".*?"reaction_count":(\d+)', html)
        comments_match = re.search(rf'"post_id":"{pid}".*?"comment_count":(\d+)', html)
        shares_match = re.search(rf'"post_id":"{pid}".*?"share_count":(\d+)', html)

        post_data["likes"] = int(likes_match.group(1)) if likes_match else 0
        post_data["comments"] = int(comments_match.group(1)) if comments_match else 0
        post_data["shares"] = int(shares_match.group(1)) if shares_match else 0

        posts.append(post_data)

    return posts


# ================= SAVE JSON =================
def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Saved {len(data)} posts to {OUTPUT_FILE}")


# ================= MAIN =================
def run():
    html = fetch_page(PAGE_URL)
    posts = extract_posts(html)
    save_json(posts)


if __name__ == "__main__":
    run()
