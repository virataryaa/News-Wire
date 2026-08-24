"""Google News RSS: broad catch-all search feed, plain XML."""
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

QUERIES = {
    "coffee": "coffee (Brazil OR Vietnam OR Colombia OR export OR frost OR drought) when:2d",
    "cocoa": "cocoa (Ivory Coast OR Ghana OR Ecuador OR export OR COCOBOD) when:2d",
}


def fetch():
    items = []
    for commodity, query in QUERIES.items():
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source_name = source_el.text if source_el is not None else "Google News"

            items.append({
                "source": f"{source_name} (via Google News)",
                "title": title,
                "summary": title,
                "date": pub,
                "link": link,
                "commodity": commodity,
            })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item["commodity"], "|", item["date"], "|", item["title"])
