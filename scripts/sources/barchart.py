"""Barchart softs news feed: the news list ships as a JSON blob in the page HTML."""
import html
import json
import re
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

PAGES = {
    "coffee": "https://www.barchart.com/futures/quotes/KCU26/news",
    "cocoa": "https://www.barchart.com/futures/quotes/CCU26/news",
}

KEYWORDS = {
    "coffee": ["coffee", "arabica", "robusta"],
    "cocoa": ["cocoa"],
}


def fetch():
    items = []
    seen_ids = set()
    for commodity, url in PAGES.items():
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        raw = resp.text

        match = re.search(r"data-feed-items='(\[.*?\])'", raw)
        if not match:
            continue

        feed = json.loads(html.unescape(match.group(1)))
        keywords = KEYWORDS[commodity]

        for entry in feed:
            title = entry.get("title", "")
            if entry["id"] in seen_ids:
                continue
            if not any(k in title.lower() for k in keywords):
                continue
            seen_ids.add(entry["id"])
            items.append({
                "source": "Barchart",
                "title": title,
                "summary": title,
                "date": entry.get("published", ""),
                "link": f"https://www.barchart.com/story/news/{entry['id']}/{entry['slug']}",
                "commodity": commodity,
            })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
