"""Hedgepoint blog: plain HTML article cards, one per tag page."""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

PAGES = {
    "coffee": "https://hedgepointglobal.com/en/blog/tag/coffee",
    "cocoa": "https://hedgepointglobal.com/en/blog/tag/cocoa",
}


def fetch():
    items = []
    for commodity, url in PAGES.items():
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for article in soup.select("article.ac-blog__post"):
            heading = article.select_one("h6.ac-blog__heading a")
            date_el = article.select_one(".ac-blog__publish-date")
            desc_el = article.select_one(".ac-blog__description")
            if not heading:
                continue

            summary = ""
            if desc_el:
                summary = re.sub(r"\s+", " ", desc_el.get_text(strip=True))

            items.append({
                "source": "Hedgepoint",
                "title": heading.get_text(strip=True),
                "summary": summary or heading.get_text(strip=True),
                "date": date_el.get_text(strip=True) if date_el else "",
                "link": heading.get("href", url),
                "commodity": commodity,
            })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
