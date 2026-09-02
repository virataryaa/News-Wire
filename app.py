import json
import os

import streamlit as st
from dateutil import parser as dateparser

st.set_page_config(page_title="Commodity Wire", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "latest.json")

CUSTOM_CSS = """
<style>
    .block-container {padding-top: 2rem; max-width: 1500px;}
    .wire-title {
        font-size: 2.2rem; font-weight: 700; letter-spacing: -0.01em;
        margin-bottom: 0.1rem; color: #1c2128;
    }
    .wire-date {
        font-family: ui-monospace, "SF Mono", Consolas, monospace;
        font-size: 0.85rem; letter-spacing: 0.06em; text-transform: uppercase;
        color: #6b7280; margin-bottom: 1.6rem;
    }
    a.wire-link {color: #1a56c4; text-decoration: none; font-weight: 600; font-size: 0.85rem;}
    .relevance-pill {
        display: inline-block; padding: 2px 9px; border-radius: 3px;
        font-family: ui-monospace, "SF Mono", Consolas, monospace;
        font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .relevance-high {background: #e6f4ea; color: #1a7f37; border: 1px solid #b7ddc3;}
    .relevance-medium {background: #eaf1fb; color: #2563a8; border: 1px solid #c3d9f0;}
    .relevance-low {background: #f1f2f4; color: #6b7280; border: 1px solid #dde0e5;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

SOURCES_INFO = [
    {
        "name": "Cecafe",
        "covers": "Coffee",
        "description": "Brazil's coffee exporters council. Monthly export report: bags shipped, crop-year comparison, FX revenue.",
        "cadence": "Monthly",
        "link": "https://www.cecafe.com.br/en/publications/monthly-exports-report/",
    },
    {
        "name": "Barchart",
        "covers": "Coffee, Cocoa, Sugar & Cotton",
        "description": "Same-day price-action headlines for ICE futures across all four softs.",
        "cadence": "Daily",
        "link": "https://www.barchart.com/futures/quotes/KCU26/news",
    },
    {
        "name": "Hedgepoint",
        "covers": "Coffee, Cocoa, Sugar & Cotton",
        "description": "Trade-house market commentary and crop/supply analysis.",
        "cadence": "Weekly-ish",
        "link": "https://hedgepointglobal.com/en/blog/tag/coffee",
    },
    {
        "name": "Google News",
        "covers": "Coffee, Cocoa, Sugar & Cotton",
        "description": "Catch-all search feed, surfaces Bloomberg/Reuters/FT/trade-press coverage that can't be reached directly (paywalls, bot-blocks).",
        "cadence": "Daily",
        "link": "https://news.google.com/",
    },
    {
        "name": "Ecofin Agency",
        "covers": "Coffee, Cocoa, Sugar & Cotton",
        "description": "African agriculture news, origin-country coverage (Ivory Coast, Ghana, Uganda, Nigeria, etc).",
        "cadence": "Daily",
        "link": "https://www.ecofinagency.com/ea-agriculture",
    },
    {
        "name": "ConfectioneryNews",
        "covers": "Cocoa",
        "description": "Covers major cocoa processors (Barry Callebaut, Cargill, Nestle) and chocolate-industry supply news.",
        "cadence": "Daily",
        "link": "https://www.confectionerynews.com/Sectors/Cocoa/",
    },
    {
        "name": "The Cocoa Post",
        "covers": "Cocoa",
        "description": "Ghana-based cocoa/chocolate trade press. Strong on origin-country fundamentals: producer pricing, farmgate prices, buyer/exporter disputes.",
        "cadence": "Daily",
        "link": "https://thecocoapost.com/category/news/",
    },
    {
        "name": "Coffee Geography",
        "covers": "Coffee",
        "description": "Dedicated coffee-origin coverage: export/import shifts, tariffs, major roaster investment moves.",
        "cadence": "Daily",
        "link": "https://coffeegeography.com/",
    },
    {
        "name": "Fibre2Fashion",
        "covers": "Cotton",
        "description": "Dedicated ICE cotton price-action and trade fundamentals (shipments, stocks, demand).",
        "cadence": "Daily",
        "link": "https://www.fibre2fashion.com/news/cotton-news/",
    },
    {
        "name": "ChiniMandi",
        "covers": "Sugar",
        "description": "India sugar industry trade press: mill quotas, cane pricing, ethanol policy. India is a top-3 global producer/exporter.",
        "cadence": "Daily",
        "link": "https://www.chinimandi.com/",
    },
]


@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def sort_key(item):
    import datetime
    try:
        parsed = dateparser.parse(item.get("date", ""), fuzzy=True)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except (ValueError, TypeError, OverflowError):
        return datetime.datetime.min


def render_table(items, relevance_filter):
    filtered = [i for i in items if i.get("relevance", "Medium") in relevance_filter]
    filtered.sort(key=sort_key, reverse=True)

    if not filtered:
        st.caption("No items match the current filter.")
        return

    rows = []
    for item in filtered:
        pill_class = f"relevance-{item.get('relevance', 'Medium').lower()}"
        detailed = item.get("detailed_summary", item["summary"])
        rows.append(
            f"""<tr>
                <td style="font-weight:600;color:#2563a8;white-space:nowrap;">{item['source']}</td>
                <td style="white-space:nowrap;"><a class="wire-link" href="{item.get('link', '#')}" target="_blank">Open &#8599;</a></td>
                <td style="font-family:ui-monospace,monospace;font-size:0.78rem;color:#6b7280;white-space:nowrap;">{item.get('date', '')}</td>
                <td><span class="relevance-pill {pill_class}">{item.get('relevance', 'Medium')}</span></td>
                <td style="min-width:220px;">{item['summary']}</td>
                <td style="min-width:340px;color:#3a4150;">{detailed}</td>
            </tr>"""
        )

    table_html = f"""
    <div style="overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
        <thead>
            <tr style="border-bottom:2px solid #d8dce3;">
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Source</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Link</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Date</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Relevance</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Summary</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Detailed Summary</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


data = load_data()

st.markdown('<div class="wire-title">Commodity Wire</div>', unsafe_allow_html=True)

if not data:
    st.warning("No data yet. This dashboard reads data/latest.json, which the daily automation writes after its first run.")
    st.stop()

st.markdown(f'<div class="wire-date">Last updated &middot; {data.get("run_date", "")}</div>', unsafe_allow_html=True)

COMMODITIES = ["coffee", "cocoa", "sugar", "cotton"]

relevance_filter = st.multiselect(
    "Relevance", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"],
)

tabs = st.tabs([c.title() for c in COMMODITIES] + ["Sources"])

for commodity, tab in zip(COMMODITIES, tabs):
    with tab:
        render_table(data.get(commodity, []), relevance_filter)

with tabs[-1]:
    rows = "".join(
        f"""<tr>
            <td style="font-weight:600;color:#2563a8;white-space:nowrap;">{s['name']}</td>
            <td style="white-space:nowrap;">{s['covers']}</td>
            <td>{s['description']}</td>
            <td style="white-space:nowrap;color:#6b7280;">{s['cadence']}</td>
            <td><a class="wire-link" href="{s['link']}" target="_blank">Visit &#8599;</a></td>
        </tr>"""
        for s in SOURCES_INFO
    )
    st.markdown(
        f"""
        <table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
            <thead>
                <tr style="border-bottom:2px solid #d8dce3;">
                    <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Source</th>
                    <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Covers</th>
                    <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Description</th>
                    <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Cadence</th>
                    <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Link</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
