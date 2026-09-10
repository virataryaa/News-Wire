"""Daily orchestrator: pulls every source, ranks only the genuinely new items,
and accumulates them into a running history file (old items stay, sorted by
date in the app, new ones just add on top).

Run manually with: python build.py
Task Scheduler runs this exact command once a day.
"""
import datetime
import json
import os
import subprocess
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from sources import (  # noqa: E402
    cecafe, barchart, hedgepoint, gnews, ecofin, confectionerynews,
    cocoapost, coffeegeography, fibre2fashion, chinimandi,
)
from summarize import summarize  # noqa: E402
from template import render  # noqa: E402

NEWS_ROOT = os.path.join(os.path.dirname(__file__), "..")
SHARED_OUTPUT = os.path.join(NEWS_ROOT, "output", "latest.html")
DATA_OUTPUT = os.path.join(NEWS_ROOT, "data", "latest.json")
LOG_DIR = os.path.join(NEWS_ROOT, "logs")

MAX_HISTORY_PER_COMMODITY = 500

COMMODITIES = ["coffee", "cocoa", "sugar", "cotton"]

SOURCES = [
    cecafe, barchart, hedgepoint, gnews, ecofin, confectionerynews,
    cocoapost, coffeegeography, fibre2fashion, chinimandi,
]


def log(message):
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(os.path.join(LOG_DIR, "build.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_history():
    if not os.path.exists(DATA_OUTPUT):
        return {c: [] for c in COMMODITIES}
    with open(DATA_OUTPUT, encoding="utf-8") as f:
        data = json.load(f)
    return {c: data.get(c, []) for c in COMMODITIES}


def _item_date(item):
    from dateutil import parser as dateparser
    try:
        parsed = dateparser.parse(item.get("date", ""), fuzzy=True)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except (ValueError, TypeError, OverflowError):
        return None


# If the automation was off for a few days, "genuinely new" can balloon into
# a multi-day backlog that takes a long time to summarize. Cap it to roughly
# the latest day's worth so a run stays quick; the rest just get picked up
# whenever the source still lists them on a later run (most do, for a while).
RECENCY_WINDOW = datetime.timedelta(hours=36)
MAX_NEW_ITEMS_PER_RUN = 20


def _limit_to_latest_day(new_items, log):
    dated = [(i, _item_date(i)) for i in new_items]
    known_dates = [d for _, d in dated if d is not None]
    if not known_dates:
        return new_items

    cutoff = max(known_dates) - RECENCY_WINDOW
    kept = [i for i, d in dated if d is None or d >= cutoff]
    dropped = len(new_items) - len(kept)
    if dropped:
        log(f"Dropped {dropped} backlog items older than ~36h before the newest one "
            f"(kept {len(kept)}), they'll be picked up later if their source still lists them")

    # Hard cap regardless of how big the backlog is, keeps a single run fast.
    if len(kept) > MAX_NEW_ITEMS_PER_RUN:
        kept_dated = sorted(
            ((i, d) for i, d in dated if i in kept),
            key=lambda pair: pair[1] or datetime.datetime.min,
            reverse=True,
        )
        kept = [i for i, _ in kept_dated[:MAX_NEW_ITEMS_PER_RUN]]
        log(f"Backlog still large after the recency window, capped to the newest "
            f"{MAX_NEW_ITEMS_PER_RUN} items")

    return kept


def trim(items):
    """Keeps the newest MAX_HISTORY_PER_COMMODITY items so the file doesn't grow forever."""
    from dateutil import parser as dateparser

    def sort_key(item):
        try:
            parsed = dateparser.parse(item.get("date", ""), fuzzy=True)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except (ValueError, TypeError, OverflowError):
            return datetime.datetime.min

    items.sort(key=sort_key, reverse=True)
    return items[:MAX_HISTORY_PER_COMMODITY]


def main():
    try:
        _run()
    except Exception:
        log("main() crashed, nothing was pushed. Full traceback:")
        log(traceback.format_exc())
        raise


def _run():
    raw_items = []
    for module in SOURCES:
        name = module.__name__.rsplit(".", 1)[-1]
        try:
            items = module.fetch()
            log(f"{name}: {len(items)} items")
            raw_items.extend(items)
        except Exception as exc:
            log(f"{name}: FAILED - {exc}")
            log(traceback.format_exc())

    if not raw_items:
        log("No items fetched from any source, aborting without overwriting output.")
        return

    history = load_history()
    known_links = {i["link"] for items in history.values() for i in items}
    new_items = [i for i in raw_items if i["link"] not in known_links]
    log(f"{len(new_items)} genuinely new items out of {len(raw_items)} fetched (rest already seen)")
    new_items = _limit_to_latest_day(new_items, log)

    if not new_items:
        log("Nothing new since last run, skipping email/output/push.")
        return

    ranked_new = summarize(new_items)
    log(f"After summarizing/ranking: {len(ranked_new)} new items kept")
    if not ranked_new:
        log("Everything new today was filtered out as irrelevant, skipping email/output/push.")
        return

    new_by_commodity = {
        c: [i for i in ranked_new if i.get("commodity") == c] for c in COMMODITIES
    }

    run_date = datetime.date.today().strftime("%d %b %Y")
    # Email/shared HTML: only today's new items, so the inbox doesn't repeat
    # the whole history every morning.
    html = render([(c.title(), new_by_commodity[c]) for c in COMMODITIES], run_date)

    os.makedirs(os.path.dirname(SHARED_OUTPUT), exist_ok=True)
    with open(SHARED_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"Wrote {SHARED_OUTPUT}")

    # Data file backing the Streamlit app: full accumulated history.
    all_items = {c: trim(history[c] + new_by_commodity[c]) for c in COMMODITIES}

    os.makedirs(os.path.dirname(DATA_OUTPUT), exist_ok=True)
    with open(DATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"run_date": run_date, **all_items}, f, indent=2)
    log(f"Wrote {DATA_OUTPUT}")

    push_to_github()


def push_to_github():
    """Commits data/latest.json and pushes, so Streamlit Cloud picks up the new run."""
    try:
        subprocess.run(["git", "add", "data/latest.json"], cwd=NEWS_ROOT, check=True, capture_output=True)
        commit = subprocess.run(
            ["git", "commit", "-m", f"Daily update {datetime.date.today().isoformat()}"],
            cwd=NEWS_ROOT, capture_output=True, text=True,
        )
        if commit.returncode != 0 and "nothing to commit" not in commit.stdout:
            log(f"git commit issue: {commit.stdout.strip()} {commit.stderr.strip()}")
            return
        push = subprocess.run(["git", "push"], cwd=NEWS_ROOT, capture_output=True, text=True)
        if push.returncode != 0:
            log(f"git push FAILED: {push.stderr.strip()}")
        else:
            log("Pushed to GitHub, Streamlit Cloud will redeploy")
    except Exception as exc:
        log(f"push_to_github FAILED: {exc}")


if __name__ == "__main__":
    main()
