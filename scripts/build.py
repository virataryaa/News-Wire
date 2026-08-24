"""Daily orchestrator: pulls every source, ranks with a rule-based filter (no API,
no cost), writes the shared HTML file.

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

from sources import cecafe, barchart, hedgepoint, gnews  # noqa: E402
from summarize import summarize  # noqa: E402
from template import render  # noqa: E402

NEWS_ROOT = os.path.join(os.path.dirname(__file__), "..")
SHARED_OUTPUT = os.path.join(NEWS_ROOT, "output", "latest.html")
DATA_OUTPUT = os.path.join(NEWS_ROOT, "data", "latest.json")
LOG_DIR = os.path.join(NEWS_ROOT, "logs")

SOURCES = [cecafe, barchart, hedgepoint, gnews]


def log(message):
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line)
    with open(os.path.join(LOG_DIR, "build.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
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

    ranked = summarize(raw_items)
    log(f"After summarizing/ranking: {len(ranked)} items kept")

    coffee_items = [i for i in ranked if i.get("commodity") == "coffee"]
    cocoa_items = [i for i in ranked if i.get("commodity") == "cocoa"]

    run_date = datetime.date.today().strftime("%d %b %Y")
    html = render(coffee_items, cocoa_items, run_date)

    os.makedirs(os.path.dirname(SHARED_OUTPUT), exist_ok=True)
    with open(SHARED_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"Wrote {SHARED_OUTPUT}")

    os.makedirs(os.path.dirname(DATA_OUTPUT), exist_ok=True)
    with open(DATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"run_date": run_date, "coffee": coffee_items, "cocoa": cocoa_items}, f, indent=2)
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
