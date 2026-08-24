import json
import os

import streamlit as st
from dateutil import parser as dateparser

st.set_page_config(page_title="Coffee Wire", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "latest.json")

CUSTOM_CSS = """
<style>
    .block-container {padding-top: 2rem; max-width: 1100px;}
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
        rows.append(
            f"""<tr>
                <td style="font-weight:600;color:#2563a8;white-space:nowrap;">{item['source']}</td>
                <td>{item['summary']}</td>
                <td><span class="relevance-pill {pill_class}">{item.get('relevance', 'Medium')}</span></td>
                <td style="font-family:ui-monospace,monospace;font-size:0.78rem;color:#6b7280;white-space:nowrap;">{item.get('date', '')}</td>
                <td><a class="wire-link" href="{item.get('link', '#')}" target="_blank">Open &#8599;</a></td>
            </tr>"""
        )

    table_html = f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
        <thead>
            <tr style="border-bottom:2px solid #d8dce3;">
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Source</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Summary</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Relevance</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Date</th>
                <th style="text-align:left;padding:8px 10px;color:#6b7280;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Link</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)


data = load_data()

st.markdown('<div class="wire-title">Coffee Wire</div>', unsafe_allow_html=True)

if not data:
    st.warning("No data yet. This dashboard reads data/latest.json, which the daily automation writes after its first run.")
    st.stop()

st.markdown(f'<div class="wire-date">Last updated &middot; {data.get("run_date", "")}</div>', unsafe_allow_html=True)

coffee_items = data.get("coffee", [])
cocoa_items = data.get("cocoa", [])

relevance_filter = st.multiselect(
    "Relevance", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"],
)

tab_coffee, tab_cocoa = st.tabs(["Coffee", "Cocoa"])

with tab_coffee:
    render_table(coffee_items, relevance_filter)

with tab_cocoa:
    render_table(cocoa_items, relevance_filter)
