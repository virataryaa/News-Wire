"""Rule-based dedupe + relevance ranking. No AI, used as a fallback if the
Claude Code CLI isn't available when summarize.py runs.
"""
import re

HIGH_KEYWORDS = [
    "export", "certified stock", "decert", "harvest", "crop", "earthquake",
    "drought", "frost", "tariff", "strike", "port", "shipment", "buyout",
    "bond market", "default", "quake", "supply chain", "logistics",
]
MEDIUM_KEYWORDS = [
    "price", "prices", "supply", "outlook", "forecast", "weather", "surplus",
    "deficit", "inventor", "stocks", "market",
]
JUNK_KEYWORDS = [
    "recipe", "ice cream", "cold brew", "flavor wheel", "how to brew",
    "health", "tourism", "visitor", "cold- or hot-brewed", "chocolate bar",
    "encyclopedia", "under construction", "podcast: 2023",
]

STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "to", "of", "and", "or", "for",
    "is", "as", "with", "by", "from", "coffee", "cocoa", "prices", "price",
}


def _tokens(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _relevance(text):
    lower = text.lower()
    if any(k in lower for k in JUNK_KEYWORDS):
        return None
    if any(k in lower for k in HIGH_KEYWORDS):
        return "High"
    if any(k in lower for k in MEDIUM_KEYWORDS):
        return "Medium"
    return "Low"


SOURCE_PRIORITY = {
    "Cecafe": 0, "Barchart": 1, "Hedgepoint": 1,
}


def _priority(item):
    source = item["source"]
    for name, score in SOURCE_PRIORITY.items():
        if name in source:
            return score
    major_outlets = ["Bloomberg", "Reuters", "Financial Times", "Barchart", "IntelliNews"]
    if any(o in source for o in major_outlets):
        return 1
    return 2


def summarize(raw_items):
    scored = []
    for item in raw_items:
        text = f"{item.get('title', '')} {item.get('summary', '')}"
        relevance = _relevance(text)
        if relevance is None:
            continue
        full_text = item["summary"]
        scored.append({
            **item,
            "relevance": relevance,
            "summary": full_text[:150],
            "detailed_summary": full_text[:600],
        })

    scored.sort(key=_priority)
    kept = []
    kept_tokens = []
    for item in scored:
        tokens = _tokens(item["title"])
        is_dup = False
        for i, existing_tokens in enumerate(kept_tokens):
            if kept[i]["commodity"] != item["commodity"]:
                continue
            overlap = len(tokens & existing_tokens) / max(1, len(tokens | existing_tokens))
            if overlap > 0.45:
                is_dup = True
                break
        if not is_dup:
            kept.append(item)
            kept_tokens.append(tokens)

    return kept
