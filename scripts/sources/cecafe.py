"""Cecafe monthly exports report: scrapes the plain-text summary embedded on the page."""
import re
import requests

URL = "https://www.cecafe.com.br/en/publications/monthly-exports-report/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    heading = re.search(r"<h2>Monthly exports report</h2>\s*<h3>([^<]+)</h3>", html)
    summary = re.search(r"<h3>[^<]+</h3>\s*<p>(.*?)</p>", html, re.S)

    if not heading or not summary:
        return []

    month = heading.group(1).strip()
    text = re.sub(r"<[^>]+>", "", summary.group(1)).strip()

    return [{
        "source": "Cecafe",
        "title": f"Brazil coffee exports report, {month}",
        "summary": text,
        "date": month,
        "link": URL,
        "commodity": "coffee",
    }]


if __name__ == "__main__":
    for item in fetch():
        print(item)
