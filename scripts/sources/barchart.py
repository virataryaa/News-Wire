"""Barchart softs news feed: the news list ships as a JSON blob in the page HTML."""
import datetime
import html
import json
import re
import requests

RELATIVE_PATTERN = re.compile(
    r"^(?:(\d+)\s*(minute|hour|day)s?\s*ago|(yesterday))$", re.I
)


def _resolve_published(raw):
    """Barchart gives absolute timestamps for older items but relative ones
    ("15 minutes ago", "Yesterday") for very fresh items. A relative string
    goes stale the instant it's stored, so resolve it to an absolute
    timestamp right now, at fetch time, while "now" is still accurate."""
    match = RELATIVE_PATTERN.match(raw.strip())
    if not match:
        return raw

    amount, unit, yesterday = match.groups()
    now = datetime.datetime.now()
    if yesterday:
        resolved = now - datetime.timedelta(days=1)
    else:
        amount = int(amount)
        delta = {"minute": "minutes", "hour": "hours", "day": "days"}[unit.lower()]
        resolved = now - datetime.timedelta(**{delta: amount})

    return resolved.strftime("%d %b %Y %H:%M")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# The softs news feed is shared across every futures symbol page, one fetch
# is enough, but hitting two pages doubles the chance of catching everything
# in a given feed refresh window.
PAGES = [
    "https://www.barchart.com/futures/quotes/KCU26/news",
    "https://www.barchart.com/futures/quotes/CTZ26/news",
]

# Checked in order, first match wins, so more specific terms go first.
KEYWORDS = [
    ("coffee", ["coffee", "arabica", "robusta"]),
    ("cocoa", ["cocoa"]),
    ("cotton", ["cotton"]),
    ("sugar", ["sugar"]),
]


def fetch():
    items = []
    seen_ids = set()
    for url in PAGES:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        raw = resp.text

        match = re.search(r"data-feed-items='(\[.*?\])'", raw)
        if not match:
            continue

        feed = json.loads(html.unescape(match.group(1)))

        for entry in feed:
            title = entry.get("title", "")
            if entry["id"] in seen_ids:
                continue

            commodity = next(
                (name for name, keywords in KEYWORDS if any(k in title.lower() for k in keywords)),
                None,
            )
            if commodity is None:
                continue

            seen_ids.add(entry["id"])
            items.append({
                "source": "Barchart",
                "title": title,
                "summary": title,
                "date": _resolve_published(entry.get("published", "")),
                "link": f"https://www.barchart.com/story/news/{entry['id']}/{entry['slug']}",
                "commodity": commodity,
            })

    return items


if __name__ == "__main__":
    for item in fetch():
        print(item)
