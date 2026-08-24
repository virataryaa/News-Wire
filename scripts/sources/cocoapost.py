"""The Cocoa Post: dedicated cocoa/chocolate trade news out of Accra, Ghana.
Strong on origin-country fundamentals (producer pricing, farmgate prices,
buyer/exporter disputes). Real publish dates in the HTML.
"""
import re
import requests

URL = "https://thecocoapost.com/category/news/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()

    for match in re.finditer(
        r'<h[23][^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]{10,150})</a>.*?'
        r'datetime="([^"]+)">([^<]+)</time>',
        html,
        re.S,
    ):
        link, title, _iso_date, date_text = match.groups()
        title = re.sub(r"&#\d+;|&nbsp;", "'", title).strip()
        if link in seen_links:
            continue
        seen_links.add(link)

        items.append({
            "source": "The Cocoa Post",
            "title": title,
            "summary": title,
            "date": date_text.strip(),
            "link": link,
            "commodity": "cocoa",
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
