"""ConfectioneryNews: covers major cocoa processors (Barry Callebaut, Cargill,
Nestle) and chocolate-industry supply news. Mixed with consumer/brand content,
filtered to cocoa-relevant keywords. Date comes straight from the URL path.
"""
import datetime
import re
import requests

URL = "https://www.confectionerynews.com/Sectors/Cocoa/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

KEYWORDS = [
    "cocoa", "cacao", "supply", "price", "harvest", "crop", "export",
    "el nino", "shortage", "tariff", "farmer", "sustainab", "deforestation",
]


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()

    for match in re.finditer(
        r'href="(/Article/(\d{4})/(\d{2})/(\d{2})/[a-z0-9\-]+)/?"[^>]*>\s*([^<]{15,150})</a>',
        html,
    ):
        path, year, month, day, title = match.groups()
        title = re.sub(r"&#\d+;|&nbsp;", "'", title).strip()
        link = "https://www.confectionerynews.com" + path
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
            "source": "ConfectioneryNews",
            "title": title,
            "summary": title,
            "date": date_str,
            "link": link,
            "commodity": "cocoa",
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
