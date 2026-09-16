"""Ranks/dedupes headlines. Four tiers, in order:

1. Groq (openai/gpt-oss-20b), free-tier cloud API, dedicated fast inference
   hardware, ~1-2s per chunk. Primary path now. Needs GROQ_API_KEY in the
   local .env file (gitignored, this repo is public, never commit that key).
2. Ollama (qwen2.5:14b), running fully local on this machine, free, no
   subscription/API usage at all. Falls back here if Groq is down/rate-limited
   or the key isn't configured.
3. Claude Code CLI (`claude -p`), uses your Claude Pro subscription login,
   not the paid API. Falls back here only if both of the above fail.
4. Rule-based filter (keyword junk-drop + near-duplicate collapse, no AI).
   Final safety net so the pipeline always produces something.
"""
import json
import os
import re
import shutil
import subprocess

import requests

CLAUDE_BIN = shutil.which("claude") or r"C:\Users\virat.arya\.local\bin\claude.exe"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:14b"
GROQ_MODEL = "openai/gpt-oss-20b"

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def _load_env_var(name):
    if name in os.environ:
        return os.environ[name]
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{name}="):
                    return line.strip().split("=", 1)[1]
    return None


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
fine), but MUST still say something "summary" doesn't, never a near-duplicate of it. Add \
factual detail and context only: additional concrete facts from the source (numbers, \
dates, named parties) if there are any to spare, plus relevant background that explains the \
story (e.g. why rain during harvest affects quality/timing, what role this country/company \
normally plays in the market, how this compares to the prior period). Do NOT tell the \
reader what to watch for, monitor, or confirm, and do NOT suggest or imply any trading \
action or recommendation, purely descriptive, additional information only. Do not invent \
specific facts (numbers, dates, named events) that are not in the source material. If \
"summary" and "detailed_summary" would end up saying essentially the same thing, cut \
something from "summary" to make room for the one added point in "detailed_summary" instead.
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


GROQ_MAX_RETRIES = 5


def _via_groq(raw_items):
    api_key = _load_env_var("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set (checked env and .env)")

    import re as _re
    import time as _time
    from groq import Groq, RateLimitError

    client = Groq(api_key=api_key)

    for attempt in range(GROQ_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "Input array:\n" + json.dumps(raw_items)},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return _extract_items(resp.choices[0].message.content)
        except RateLimitError as exc:
            # Free-tier per-minute limits are tight but reset fast (seconds,
            # not minutes), a short wait-and-retry beats falling back to a
            # slower/heavier tier for what's usually a transient hiccup.
            retry_after = None
            header_val = exc.response.headers.get("retry-after") if exc.response else None
            if header_val:
                try:
                    retry_after = float(header_val)
                except ValueError:
                    pass
            if retry_after is None:
                match = _re.search(r"try again in ([\d.]+)s", str(exc))
                retry_after = float(match.group(1)) if match else 10.0

            wait = retry_after + 0.5
            print(f"Groq rate-limited, waiting {wait:.1f}s and retrying "
                  f"(attempt {attempt + 1}/{GROQ_MAX_RETRIES})")
            _time.sleep(wait)

    raise RuntimeError(f"Groq still rate-limited after {GROQ_MAX_RETRIES} retries")


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


# Small enough to stay comfortably under Groq's free-tier 6,000 tokens/minute
# limit per request (a chunk this size runs ~1,500-2,000 tokens all in).
CHUNK_SIZE = 8


def _summarize_chunk(chunk, chunk_label):
    try:
        return _via_groq(chunk)
    except Exception as exc:
        print(f"Groq summarize failed on {chunk_label} ({exc}), trying Ollama")
    try:
        return _via_ollama(chunk)
    except Exception as exc:
        print(f"Ollama summarize also failed on {chunk_label} ({exc}), trying Claude CLI")
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
    for i in range(0, len(raw_items), CHUNK_SIZE):
        chunk = raw_items[i:i + CHUNK_SIZE]
        results.extend(_summarize_chunk(chunk, f"chunk {i}-{i + len(chunk)}"))

    return results


if __name__ == "__main__":
    sample = [{
        "source": "Test", "title": "Test headline", "summary": "Test summary",
        "date": "Sep 16, 2026", "link": "https://example.com", "commodity": "coffee",
    }]
    print(json.dumps(summarize(sample), indent=2))
