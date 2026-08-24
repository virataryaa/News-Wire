import json
import os

import streamlit as st

st.set_page_config(page_title="Coffee Wire", layout="wide")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "latest.json")

CUSTOM_CSS = """
<style>
    .block-container {padding-top: 2rem; max-width: 1100px;}
    .wire-title {
        font-size: 2.2rem; font-weight: 700; letter-spacing: -0.01em;
        margin-bottom: 0.1rem;
    }
    .wire-date {
        font-family: ui-monospace, "SF Mono", Consolas, monospace;
        font-size: 0.85rem; letter-spacing: 0.06em; text-transform: uppercase;
        color: #8a93a6; margin-bottom: 1.4rem;
    }
    .kpi-row {display: flex; gap: 14px; margin-bottom: 1.6rem; flex-wrap: wrap;}
    .kpi-card {
        flex: 1; min-width: 150px; background: #171c26; border: 1px solid #262c3a;
        border-radius: 8px; padding: 14px 16px;
    }
    .kpi-value {font-size: 1.6rem; font-weight: 700; color: #e8ecf3;}
    .kpi-label {
        font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase;
        color: #8a93a6; margin-top: 2px;
    }
    .kpi-desc {font-size: 0.75rem; color: #5f6779; margin-top: 4px;}
    .section-label {
        font-size: 0.95rem; font-weight: 700; letter-spacing: 0.02em;
        border-bottom: 2px solid #3a4a63; padding-bottom: 6px; margin: 1.6rem 0 0.8rem;
    }
    a.wire-link {color: #6fa8dc; text-decoration: none; font-weight: 600; font-size: 0.85rem;}
    .relevance-pill {
        display: inline-block; padding: 2px 9px; border-radius: 3px;
        font-family: ui-monospace, "SF Mono", Consolas, monospace;
        font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .relevance-high {background: #1f3a2e; color: #7fd9a0; border: 1px solid #2e5540;}
    .relevance-medium {background: #26314a; color: #8fa8d9; border: 1px solid #34456b;}
    .relevance-low {background: #1c2130; color: #6b7488; border: 1px solid #2a2f40;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def kpi_card(value, label, desc):
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-desc">{desc}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_table(items, relevance_filter):
    filtered = [i for i in items if i.get("relevance", "Medium") in relevance_filter]
    order = {"High": 0, "Medium": 1, "Low": 2}
    filtered.sort(key=lambda i: order.get(i.get("relevance", "Medium"), 1))

    if not filtered:
        st.caption("No items match the current filter.")
        return

    rows = []
    for item in filtered:
        pill_class = f"relevance-{item.get('relevance', 'Medium').lower()}"
        rows.append(
            f"""<tr>
                <td style="font-weight:600;color:#8fa8d9;white-space:nowrap;">{item['source']}</td>
                <td>{item['summary']}</td>
                <td><span class="relevance-pill {pill_class}">{item.get('relevance', 'Medium')}</span></td>
                <td style="font-family:ui-monospace,monospace;font-size:0.78rem;color:#8a93a6;white-space:nowrap;">{item.get('date', '')}</td>
                <td><a class="wire-link" href="{item.get('link', '#')}" target="_blank">Open &#8599;</a></td>
            </tr>"""
        )

    table_html = f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
        <thead>
            <tr style="border-bottom:2px solid #3a4a63;">
                <th style="text-align:left;padding:8px 10px;color:#8a93a6;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Source</th>
                <th style="text-align:left;padding:8px 10px;color:#8a93a6;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Summary</th>
                <th style="text-align:left;padding:8px 10px;color:#8a93a6;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Relevance</th>
                <th style="text-align:left;padding:8px 10px;color:#8a93a6;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Date</th>
                <th style="text-align:left;padding:8px 10px;color:#8a93a6;font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;">Link</th>
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
all_items = coffee_items + cocoa_items
high_count = sum(1 for i in all_items if i.get("relevance") == "High")
sources = {i["source"] for i in all_items}

st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    kpi_card(len(all_items), "Total Items", "Coffee + Cocoa combined")
with col2:
    kpi_card(high_count, "High Relevance", "Likely to move price")
with col3:
    kpi_card(len(sources), "Sources", "Cecafe, Barchart, Hedgepoint, Google News")
with col4:
    kpi_card(len(coffee_items), "Coffee", f"{len(cocoa_items)} Cocoa items separately")
st.markdown('</div>', unsafe_allow_html=True)

relevance_filter = st.multiselect(
    "Relevance", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"],
)

st.markdown('<div class="section-label">Coffee</div>', unsafe_allow_html=True)
render_table(coffee_items, relevance_filter)

st.markdown('<div class="section-label">Cocoa</div>', unsafe_allow_html=True)
render_table(cocoa_items, relevance_filter)
