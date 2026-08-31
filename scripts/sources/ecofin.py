"""Ecofin Agency: African agriculture news, covers coffee and cocoa origin
countries (Ivory Coast, Ghana, Uganda, Nigeria, etc). Date is encoded in the
article URL as DDMM, current year assumed (this is a rolling news feed).
"""
import datetime
import re
import requests

URL = "https://www.ecofinagency.com/ea-agriculture"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

KEYWORDS = {
    "coffee": ["coffee", "arabica", "robusta"],
    "cocoa": ["cocoa", "cacao"],
    "sugar": ["sugar", "sugarcane", "ethanol"],
    "cotton": ["cotton"],
}


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()
    year = datetime.date.today().year

    for match in re.finditer(
        r'href="(/news-agriculture/(\d{2})(\d{2})-\d+-[a-z0-9\-]+)"[^>]*>\s*([^<]{15,150})</a>',
        html,
    ):
        path, day, month, title = match.groups()
        title = re.sub(r"&nbsp;|&#\d+;", " ", title).strip()
        link = "https://www.ecofinagency.com" + path
        if link in seen_links:
            continue

        lower_title = title.lower()
        commodity = None
        for name, keywords in KEYWORDS.items():
            if any(k in lower_title for k in keywords):
                commodity = name
                break
        if commodity is None:
            continue

        seen_links.add(link)
        try:
            date_str = datetime.date(year, int(month), int(day)).strftime("%d %b %Y")
        except ValueError:
            date_str = ""

        items.append({
            "source": "Ecofin Agency",
            "title": title,
            "summary": title,
            "date": date_str,
            "link": link,
            "commodity": commodity,
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
