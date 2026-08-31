"""Fibre2Fashion cotton news: dedicated ICE cotton price-action and trade
fundamentals. Real dates shown on the listing page.
"""
import re
import requests

URL = "https://www.fibre2fashion.com/news/cotton-news/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()

    pattern = re.compile(
        r'<a href="([^"]+newsdetails\.htm)" class="blocktitle" target="_blank">([^<]{10,150})</a>'
        r'.*?<div class="latest-news-date">\s*([^<]+?)\s*</div>',
        re.S,
    )

    for match in pattern.finditer(html):
        link, title, date_text = match.groups()
        title = re.sub(r"&#\d+;|&nbsp;", "'", title).strip()
        if link in seen_links:
            continue
        seen_links.add(link)

        items.append({
            "source": "Fibre2Fashion",
            "title": title,
            "summary": title,
            "date": date_text.strip(),
            "link": link,
            "commodity": "cotton",
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
