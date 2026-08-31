"""ChiniMandi: India sugar industry news. India is a top-3 global sugar
producer/exporter, this is the dedicated trade press for it. General India
business/politics news mixed in, filtered to sugar-relevant keywords.
"""
import re
import requests

URL = "https://www.chinimandi.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

KEYWORDS = [
    "sugar", "cane", "ethanol", "mill", "quota", "export", "import",
    "production", "crop",
]


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    items = []
    seen_links = set()

    pattern = re.compile(
        r'<h3 class="entry-title td-module-title"><a href="([^"]+)"[^>]*title="([^"]{10,150})">'
        r'.*?datetime="[^"]+"\s*>([^<]+)</time>',
        re.S,
    )

    for match in pattern.finditer(html):
        link, title, date_text = match.groups()
        title = re.sub(r"&#\d+;|&nbsp;", "'", title).strip()
        if link in seen_links:
            continue
        if not any(k in title.lower() for k in KEYWORDS):
            continue
        seen_links.add(link)

        items.append({
            "source": "ChiniMandi",
            "title": title,
            "summary": title,
            "date": date_text.strip(),
            "link": link,
            "commodity": "sugar",
        })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
