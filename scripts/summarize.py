"""Ranks/dedupes headlines. Three tiers, in order:

1. Ollama (qwen2.5:14b), running fully local on this machine, free, no
   subscription/API usage at all. Primary path now.
2. Claude Code CLI (`claude -p`), uses your Claude Pro subscription login,
   not the paid API. Falls back here only if Ollama isn't running/installed
   or fails on a given chunk.
3. Rule-based filter (keyword junk-drop + near-duplicate collapse, no AI).
   Final safety net so the pipeline always produces something.
"""
import json
import re
import shutil
import subprocess

import requests

CLAUDE_BIN = shutil.which("claude") or r"C:\Users\virat.arya\.local\bin\claude.exe"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:14b"

SYSTEM_PROMPT = """You are curating a daily fundamentals news wire for a soft commodities \
trading desk covering coffee, cocoa, sugar, and cotton. You'll be given a JSON array of raw \
headline items (source, title, summary, date, link, commodity), the "commodity" field tells \
you which of the four each item is about, use it, don't second-guess it. Do the following:

1. Drop anything that is not relevant to that item's trade fundamentals (price action, \
exports, weather, crop estimates, policy, logistics, certified/warehouse stocks). This \
applies equally across all four commodities, do not treat sugar or cotton items as lower \
priority just because there are fewer of them. Drop consumer lifestyle content, recipes, \
unrelated trivia, and near-duplicate stories (keep the best single version of a repeated \
story, e.g. if five outlets cover the same earthquake, keep the single best-sourced one).
2. For each surviving item, write TWO summaries, independent of the original headline's \
wording. Many of these items are a single headline with no article body, so you'll often \
have very little raw material, that's expected, work with it as follows:
   - "summary": a terse one-line version, no more than ~25 words, for quick scanning. Just \
the facts, no added context.
   - "detailed_summary": also short, average around 25 words (a bit shorter or longer is \
fine), but MUST still say something "summary" doesn't, never a near-duplicate of it. Since \
there's little room, pick the single most useful addition: either one added concrete fact \
if the source has one to spare, or one line of trading-desk context (the mechanism behind \
why this matters, or what to watch next). Do not invent specific facts (numbers, dates, \
named events) that are not in the source material. If "summary" and "detailed_summary" \
would end up saying essentially the same thing, cut something from "summary" to make room \
for the one added point in "detailed_summary" instead.
3. Rate relevance as "High", "Medium", or "Low" based on how likely it is to move price or \
matter to a trading desk, not on how interesting it is generally.
4. Do not editorialize about direction (never say bullish/bearish).

You MUST process every item in the input array, one output item per surviving input item, \
dropping only the ones filtered out in step 1. Reply with a JSON object of exactly this \
shape: {"items": [ <one object per surviving item> ]}, never a single bare object, always \
the "items" array, even if only one item survives, even if none do (empty array). Each \
object needs: source, summary, detailed_summary, relevance, date, link, commodity. Preserve \
the original link and date fields exactly, no other text, no markdown fences."""


def _extract_items(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("No JSON object found in model output")
    parsed = json.loads(match.group(0))
    if "items" not in parsed or not isinstance(parsed["items"], list):
        raise ValueError("Model output JSON has no 'items' array")
    return parsed["items"]


def _via_ollama(raw_items):
    prompt = SYSTEM_PROMPT + "\n\nInput array:\n" + json.dumps(raw_items)
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            # num_gpu: 0 forces CPU inference for this call specifically, this
            # is more reliable than CUDA_VISIBLE_DEVICES at the process/env
            # level, which has drifted back to GPU on its own after restarts.
            "options": {"temperature": 0.2, "num_gpu": 0},
        },
        timeout=900,
    )
    resp.raise_for_status()
    return _extract_items(resp.json().get("response", ""))


def _via_claude(raw_items):
    prompt = SYSTEM_PROMPT + "\n\nInput array:\n" + json.dumps(raw_items)
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
    return _extract_items(result.stdout)


def _via_rules(raw_items):
    from summarize_rules import summarize as rules_summarize
    return rules_summarize(raw_items)


# Ollama on CPU runs noticeably slower per item than the Claude CLI, so it
# gets a smaller chunk size to stay well under its own (longer) timeout.
OLLAMA_CHUNK_SIZE = 15
CLAUDE_CHUNK_SIZE = 35


def _summarize_chunk(chunk, chunk_label):
    try:
        return _via_ollama(chunk)
    except Exception as exc:
        print(f"Ollama summarize failed on {chunk_label} ({exc}), trying Claude CLI")
    try:
        return _via_claude(chunk)
    except Exception as exc:
        print(f"Claude CLI summarize also failed on {chunk_label} ({exc}), "
              f"falling back to rule-based filter for this chunk only")
        return _via_rules(chunk)


def summarize(raw_items):
    if not raw_items:
        return []

    results = []
    for i in range(0, len(raw_items), OLLAMA_CHUNK_SIZE):
        chunk = raw_items[i:i + OLLAMA_CHUNK_SIZE]
        results.extend(_summarize_chunk(chunk, f"chunk {i}-{i + len(chunk)}"))

    return results


if __name__ == "__main__":
    sample = [{
        "source": "Test", "title": "Test headline", "summary": "Test summary",
        "date": "Sep 10, 2026", "link": "https://example.com", "commodity": "coffee",
    }]
    print(json.dumps(summarize(sample), indent=2))
