"""Ranks/dedupes headlines using the Claude Code CLI (uses your Claude Pro
subscription login, not the paid API) via `claude -p`, run headlessly.

Falls back to a simple rule-based filter (keyword junk-drop + near-duplicate
collapse, no AI) if the CLI isn't installed/authenticated, so the pipeline
still runs either way.
"""
import json
import re
import shutil
import subprocess

CLAUDE_BIN = shutil.which("claude") or r"C:\Users\virat.arya\.local\bin\claude.exe"

SYSTEM_PROMPT = """You are curating a daily fundamentals news wire for a coffee and cocoa \
trading desk. You'll be given a JSON list of raw headline items (source, title, summary, \
date, link, commodity). Do the following:

1. Drop anything that is not relevant to coffee/cocoa trade fundamentals (price action, \
exports, weather, crop estimates, policy, logistics, certified stocks). Drop consumer \
lifestyle content, recipes, unrelated trivia, and near-duplicate stories (keep the best \
single version of a repeated story, e.g. if five outlets cover the same earthquake, keep \
the single best-sourced one).
2. For each surviving item, write TWO summaries, independent of the original headline's \
wording. Many of these items are a single headline with no article body, so you'll often \
have very little raw material, that's expected, work with it as follows:
   - "summary": a terse one-line version, no more than ~25 words, for quick scanning.
   - "detailed_summary": roughly 80-100 words, and MUST read as meaningfully longer and \
more useful than "summary", never a near-duplicate of it. Lead with whatever concrete \
specifics exist in the source (numbers, origin/country, dates). Then, always, add trading- \
desk context to fill it out: the mechanism behind why this would matter (e.g. why rain \
during harvest affects quality/timing, why a port delay affects near-term arrivals vs. \
supply itself), what a trader should watch next to confirm or discount the story, and \
relevant background (e.g. that country's/commodity's typical role in global supply). This \
added context must be genuinely relevant and defensible, not filler, but do not invent \
specific facts (numbers, dates, named events) that are not in the source material. If \
"summary" and "detailed_summary" would end up saying essentially the same thing, you have \
not added enough of this context, go back and add more.
3. Rate relevance as "High", "Medium", or "Low" based on how likely it is to move price or \
matter to a trading desk, not on how interesting it is generally.
4. Do not editorialize about direction (never say bullish/bearish).

Reply with ONLY a JSON array, no other text, no markdown fences, where each element has: \
source, summary, detailed_summary, relevance, date, link, commodity. Preserve the original \
link and date fields exactly."""


def _extract_json_array(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise ValueError("No JSON array found in CLI output")
    return json.loads(match.group(0))


def _via_cli(raw_items):
    prompt = SYSTEM_PROMPT + "\n\nHere is the JSON list:\n" + json.dumps(raw_items)
    result = subprocess.run(
        [CLAUDE_BIN, "-p", "--tools="],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=500,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:500]}")
    return _extract_json_array(result.stdout)


def _via_rules(raw_items):
    from summarize_rules import summarize as rules_summarize
    return rules_summarize(raw_items)


def summarize(raw_items):
    try:
        return _via_cli(raw_items)
    except Exception as exc:
        print(f"Claude CLI summarize failed ({exc}), falling back to rule-based filter")
        return _via_rules(raw_items)


if __name__ == "__main__":
    sample = [{
        "source": "Test", "title": "Test headline", "summary": "Test summary",
        "date": "Aug 12, 2026", "link": "https://example.com", "commodity": "coffee",
    }]
    print(json.dumps(summarize(sample), indent=2))
