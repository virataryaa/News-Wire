"""Renders the ranked items into the same table design used for the sample."""

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Coffee Wire</title>
<style>
  :root {{
    --bg: #efece1; --bg-panel: #f8f6ef; --ink: #262218; --ink-soft: #59503f;
    --rule: #d8d2c0; --accent: #a8722f; --accent-soft: #c99a5c; --tag-bg: #e4dcc4;
    --tag-ink: #4b5842; --mono: #726a55; --row-alt: #f2efe4; --link: #8a5a24;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #1c1812; --bg-panel: #24201a; --ink: #ece5d5; --ink-soft: #b7ac95;
      --rule: #3a3427; --accent: #d9a455; --accent-soft: #b98748; --tag-bg: #332d20;
      --tag-ink: #b8c2a8; --mono: #93876c; --row-alt: #201c16; --link: #e0ac63;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #1c1812; --bg-panel: #24201a; --ink: #ece5d5; --ink-soft: #b7ac95;
    --rule: #3a3427; --accent: #d9a455; --accent-soft: #b98748; --tag-bg: #332d20;
    --tag-ink: #b8c2a8; --mono: #93876c; --row-alt: #201c16; --link: #e0ac63;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg); color: var(--ink); margin: 0; padding: 40px 16px 80px;
    font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
    -webkit-font-smoothing: antialiased;
  }}
  .sheet {{ max-width: 980px; margin: 0 auto; background: var(--bg-panel); border: 1px solid var(--rule); }}
  .masthead {{ padding: 24px 28px 18px; border-bottom: 3px solid var(--ink); }}
  .masthead-row {{
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: 11px;
    letter-spacing: 0.06em; text-transform: uppercase; color: var(--mono); margin-bottom: 8px;
  }}
  .masthead h1 {{
    margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.01em;
    text-wrap: balance; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .commodity-label {{
    margin: 22px 28px 10px; font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 15px; font-weight: 700; color: var(--ink); padding-bottom: 6px;
    border-bottom: 2px solid var(--accent-soft);
  }}
  .table-wrap {{ overflow-x: auto; }}
  table.wire {{
    width: 100%; border-collapse: collapse;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 13px;
  }}
  table.wire th {{
    padding: 10px 14px; text-align: left; font-size: 10.5px; letter-spacing: 0.07em;
    text-transform: uppercase; color: var(--mono); font-weight: 700; background: var(--tag-bg);
    border-bottom: 2px solid var(--ink); white-space: nowrap;
  }}
  table.wire td {{ padding: 11px 14px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--rule); line-height: 1.45; }}
  table.wire tbody tr:nth-child(even) {{ background: var(--row-alt); }}
  table.wire tbody tr:last-child td {{ border-bottom: none; }}
  td.source-cell {{ font-weight: 700; color: var(--accent); white-space: nowrap; }}
  td.date-cell {{ font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: 11.5px; color: var(--mono); white-space: nowrap; font-variant-numeric: tabular-nums; }}
  td.link-cell {{ white-space: nowrap; }}
  td.link-cell a {{ color: var(--link); text-decoration: none; font-size: 12px; font-weight: 600; border-bottom: 1px solid var(--accent-soft); }}
  .relevance {{ display: inline-block; padding: 2px 8px; border-radius: 2px; font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: 10.5px; letter-spacing: 0.04em; text-transform: uppercase; white-space: nowrap; }}
  .relevance.high {{ background: var(--tag-bg); color: var(--accent); border: 1px solid var(--accent-soft); }}
  .relevance.medium {{ background: var(--tag-bg); color: var(--tag-ink); border: 1px solid var(--rule); }}
  .relevance.low {{ color: var(--mono); border: 1px solid var(--rule); }}
  .footer {{ padding: 16px 28px 24px; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 11.5px; line-height: 1.6; color: var(--ink-soft); border-top: 1px solid var(--rule); }}
</style>
</head>
<body>
<div class="sheet">
  <div class="masthead">
    <div class="masthead-row"><span>Coffee Wire</span><span>{run_date}</span></div>
    <h1>Source Table</h1>
  </div>
  {coffee_section}
  {cocoa_section}
</div>
</body>
</html>
"""

SECTION_TEMPLATE = """
  <div class="commodity-label">{label}</div>
  <div class="table-wrap">
    <table class="wire">
      <thead><tr><th>Source</th><th>Summary</th><th>Detailed Summary</th><th>Relevance</th><th>Date</th><th>Link</th></tr></thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
  <div class="footer">{footer}</div>
"""

ROW_TEMPLATE = """        <tr>
          <td class="source-cell">{source}</td>
          <td>{summary}</td>
          <td>{detailed_summary}</td>
          <td><span class="relevance {relevance_class}">{relevance}</span></td>
          <td class="date-cell">{date}</td>
          <td class="link-cell"><a href="{link}" target="_blank" rel="noopener">Open &#8599;</a></td>
        </tr>"""


def render(coffee_items, cocoa_items, run_date):
    def rows_for(items):
        items = sorted(items, key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x.get("relevance", "Medium"), 1))
        return "\n".join(
            ROW_TEMPLATE.format(
                source=item["source"],
                summary=item["summary"],
                detailed_summary=item.get("detailed_summary", item["summary"]),
                relevance=item.get("relevance", "Medium"),
                relevance_class=item.get("relevance", "Medium").lower(),
                date=item.get("date", ""),
                link=item.get("link", "#"),
            )
            for item in items
        )

    coffee_section = SECTION_TEMPLATE.format(
        label="Coffee", rows=rows_for(coffee_items),
        footer=f"{len(coffee_items)} items.",
    )
    cocoa_section = SECTION_TEMPLATE.format(
        label="Cocoa", rows=rows_for(cocoa_items),
        footer=f"{len(cocoa_items)} items.",
    )

    return PAGE_TEMPLATE.format(
        run_date=run_date, coffee_section=coffee_section, cocoa_section=cocoa_section,
    )
