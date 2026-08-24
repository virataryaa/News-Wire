"""Coffee Geography Magazine: dedicated coffee-origin coverage, crop reports,
trade/tariff shifts, and major roaster investment moves. Date is in the URL.
"""
import datetime
import re
import requests

URL = "https://coffeegeography.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

KEYWORDS = [
    "export", "price", "tariff", "import", "production", "harvest", "crop",
    "supply", "invest", "acquisition", "shortage", "roaster", "trade",
]


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()

    for match in re.finditer(
        r'href="(https://coffeegeography\.com/(\d{4})/(\d{2})/(\d{2})/[a-z0-9\-]+)/?"[^>]*>([^<]{15,150})</a>',
        html,
    ):
        link, year, month, day, title = match.groups()
        title = re.sub(r"&#\d+;|&nbsp;", "'", title).strip()
        if link in seen_links:
            continue
        if not any(k in title.lower() for k in KEYWORDS):
            continue

        seen_links.add(link)
        try:
            date_str = datetime.date(int(year), int(month), int(day)).strftime("%d %b %Y")
        except ValueError:
            date_str = f"{day} {month} {year}"

        items.append({
            "source": "Coffee Geography",
            "title": title,
            "summary": title,
            "date": date_str,
            "link": link,
            "commodity": "coffee",
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
