import requests
import re
import json
from datetime import datetime

PAGE_URL = "https://mbasic.facebook.com/nytimes"
OUTPUT_FILE = f"fb_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
}

def fetch_page(url):
    print(f"Fetching: {url}")
    response = requests.get(url, headers=HEADERS)
    return response.text


def extract_posts(html):
    posts = []

    # Extract post links
    matches = re.findall(r'href="(/story\.php\?story_fbid=\d+&amp;id=\d+)"', html)

    for link in matches:
        clean_link = link.replace("&amp;", "&")
        full_url = "https://mbasic.facebook.com" + clean_link

        post = {
            "post_url": full_url
        }

        posts.append(post)

    return posts


def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Saved {len(data)} posts to {OUTPUT_FILE}")


def run():
    html = fetch_page(PAGE_URL)
    posts = extract_posts(html)
    save_json(posts)


if __name__ == "__main__":
    run()
