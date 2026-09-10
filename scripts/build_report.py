#!/usr/bin/env python3
"""Render report HTML 1 trang từ data/pipeline/stock_metrics.json.

Output: data/reports/stock_report_{YYYY-MM-DD}.html
"""

import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")
REPORT_DIR = os.path.join(ROOT, "data", "reports")

GROUP_LABEL = {
    "buy": ("✅", "Nên xem xét", "buy"),
    "watch": ("⚠️", "Theo dõi thêm", "watch"),
    "avoid": ("❌", "Tránh / chờ", "avoid"),
}

# Lý do cho top picks — do story-builder viết mỗi ngày vào
# data/pipeline/picks_notes.json (key theo ticker). Thiếu file thì để trống.
NOTES_PATH = os.path.join(ROOT, "data", "pipeline", "picks_notes.json")


def load_pick_notes():
    try:
        with open(NOTES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def build_chart(metrics, tickers, width=820, height=260):
    """SVG line chart: Close normalized về 100 tại phiên đầu của cửa sổ."""
    pad_l, pad_r, pad_t, pad_b = 34, 8, 12, 22
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    series = []
    for tk in tickers:
        closes = metrics[tk]["closes"]
        base = closes[0]
        series.append((tk, [c / base * 100 for c in closes]))

    ys = [v for _, s in series for v in s]
    lo, hi = min(ys), max(ys)
    span = max(hi - lo, 1e-6)
    lo -= span * 0.08
    hi += span * 0.08

    n = len(series[0][1])

    def px(i):
        return pad_l + plot_w * i / max(n - 1, 1)

    def py(v):
        return pad_t + plot_h * (1 - (v - lo) / (hi - lo))

    colors = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c",
              "#0891b2", "#ca8a04", "#db2777", "#4b5563", "#65a30d"]

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Diễn biến giá chuẩn hoá về 100">']

    # gridlines + trục y
    for frac in (0, 0.25, 0.5, 0.75, 1):
        v = lo + (hi - lo) * frac
        y = py(v)
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" '
                     f'class="grid"/>')
        parts.append(f'<text x="{pad_l - 6}" y="{y + 3.5:.1f}" class="axis" '
                     f'text-anchor="end">{v:.0f}</text>')

    # baseline 100
    if lo < 100 < hi:
        parts.append(f'<line x1="{pad_l}" y1="{py(100):.1f}" x2="{width - pad_r}" '
                     f'y2="{py(100):.1f}" class="baseline"/>')

    for idx, (tk, vals) in enumerate(series):
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{px(i):.1f} {py(v):.1f}" for i, v in enumerate(vals)
        )
        parts.append(f'<path d="{d}" fill="none" stroke="{colors[idx % len(colors)]}" '
                     f'stroke-width="1.7" stroke-linejoin="round"/>')

    dates = metrics[tickers[0]]["dates"]
    for i in (0, n // 2, n - 1):
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        parts.append(f'<text x="{px(i):.1f}" y="{height - 6}" class="axis" '
                     f'text-anchor="{anchor}">{dates[i][5:]}</text>')

    parts.append("</svg>")

    legend = "".join(
        f'<span class="lg"><i style="background:{colors[i % len(colors)]}"></i>{tk}</span>'
        for i, (tk, _) in enumerate(series)
    )
    return "".join(parts), legend


def main():
    with open(METRICS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    metrics = data["metrics"]
    ranking = data["ranking"]
    data_date = data["generated_for_data_date"]
    today = datetime.date.today().isoformat()

    pick_notes = load_pick_notes()

    chart_svg, legend = build_chart(metrics, ranking)

    rows = []
    for tk in ranking:
        m = metrics[tk]
        icon, label, cls = GROUP_LABEL[m["group"]]
        ret_cls = "pos" if m["return_30d_pct"] >= 0 else "neg"
        vt = m["volume_trend_pct"]
        vt_txt = f"{vt:+.0f}%"
        rows.append(
            f'<tr class="r-{cls}">'
            f'<td class="tk">{tk}</td>'
            f'<td class="num">{m["last_close"]:.2f}</td>'
            f'<td class="num {ret_cls}">{m["return_30d_pct"]:+.2f}%</td>'
            f'<td class="num">{m["volatility_pct"]:.2f}%</td>'
            f'<td>{m["trend"]}</td>'
            f'<td class="num">{vt_txt}</td>'
            f'<td class="num strong">{m["risk_adjusted"]:.2f}</td>'
            f'<td class="rec {cls}">{icon} {label}</td>'
            f"</tr>"
        )

    picks = []
    for tk in ranking[:3]:
        m = metrics[tk]
        picks.append(
            f'<div class="pick">'
            f'<div class="pick-h"><span class="pick-tk">{tk}</span>'
            f'<span class="pick-m">{m["return_30d_pct"]:+.2f}% · vol {m["volatility_pct"]:.2f}% '
            f'· RA {m["risk_adjusted"]:.2f}</span></div>'
            f'<p>{pick_notes.get(tk, "")}</p>'
            f"</div>"
        )

    missing = data.get("missing_tickers") or []
    missing_note = (
        f'<p class="note">⚠️ Thiếu data, không xếp hạng: {", ".join(missing)}.</p>'
        if missing else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VN Stock Daily Briefing — {today}</title>
<style>
  :root {{
    --bg:#f7f8fa; --card:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb;
    --pos:#15803d; --neg:#b91c1c; --buy:#15803d; --watch:#b45309; --avoid:#9ca3af;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; }}
  .wrap {{ max-width:1000px; margin:0 auto; padding:18px 20px 26px; }}
  header {{ display:flex; align-items:baseline; justify-content:space-between;
    gap:12px; flex-wrap:wrap; border-bottom:2px solid var(--ink); padding-bottom:8px; }}
  h1 {{ font-size:20px; margin:0; letter-spacing:-.2px; }}
  .sub {{ color:var(--muted); font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:1.35fr 1fr; gap:16px; margin-top:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:8px;
    padding:12px 14px; }}
  h2 {{ font-size:12px; text-transform:uppercase; letter-spacing:.6px;
    color:var(--muted); margin:0 0 8px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th {{ text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.4px;
    color:var(--muted); font-weight:600; padding:0 6px 5px; border-bottom:1px solid var(--line); }}
  td {{ padding:4.5px 6px; border-bottom:1px solid #f1f2f4; }}
  tr:last-child td {{ border-bottom:none; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .tk {{ font-weight:700; }}
  .strong {{ font-weight:600; }}
  .pos {{ color:var(--pos); }} .neg {{ color:var(--neg); }}
  .rec {{ white-space:nowrap; font-size:11.5px; }}
  .rec.buy {{ color:var(--buy); font-weight:600; }}
  .rec.watch {{ color:var(--watch); }}
  .rec.avoid {{ color:var(--avoid); }}
  .r-buy td {{ background:#f0fdf4; }}
  svg {{ width:100%; height:auto; display:block; }}
  .grid line.grid {{ stroke:#eceef1; stroke-width:1; }}
  line.grid {{ stroke:#eceef1; stroke-width:1; }}
  line.baseline {{ stroke:#9ca3af; stroke-width:1; stroke-dasharray:3 3; }}
  text.axis {{ font-size:9px; fill:var(--muted); }}
  .legend {{ display:flex; flex-wrap:wrap; gap:4px 12px; margin-top:6px; font-size:10.5px;
    color:var(--muted); }}
  .lg i {{ display:inline-block; width:9px; height:2.5px; border-radius:2px;
    margin-right:4px; vertical-align:middle; }}
  .pick {{ padding:8px 0; border-bottom:1px dashed var(--line); }}
  .pick:last-child {{ border-bottom:none; padding-bottom:0; }}
  .pick-h {{ display:flex; align-items:baseline; gap:8px; }}
  .pick-tk {{ font-weight:700; font-size:14px; }}
  .pick-m {{ font-size:10.5px; color:var(--muted); font-variant-numeric:tabular-nums; }}
  .pick p {{ margin:3px 0 0; font-size:12px; }}
  .note {{ font-size:11px; color:var(--muted); margin:8px 0 0; }}
  footer {{ margin-top:14px; font-size:10.5px; color:var(--muted);
    border-top:1px solid var(--line); padding-top:8px; }}
  @media (max-width:820px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>VN Stock Daily Briefing — {today}</h1>
    <div class="sub">Data đến {data_date} · cửa sổ {data["window_start"]} →
      {data_date} ({data["window_sessions"]} phiên)</div>
  </header>

  <div class="grid">
    <div class="card">
      <h2>Diễn biến giá — chuẩn hoá về 100 tại {data["window_start"]}</h2>
      {chart_svg}
      <div class="legend">{legend}</div>
    </div>
    <div class="card">
      <h2>Top picks hôm nay</h2>
      {"".join(picks)}
    </div>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>Bảng tóm tắt 10 mã — xếp theo return đã điều chỉnh rủi ro</h2>
    <table>
      <thead><tr>
        <th>Mã</th><th class="num">Giá</th><th class="num">Return 30D</th>
        <th class="num">Volatility</th><th>Trend</th><th class="num">Volume 7D</th>
        <th class="num">RA</th><th>Khuyến nghị</th>
      </tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    {missing_note}
  </div>

  <footer>
    RA = Return 30D / Volatility (return trên mỗi đơn vị rủi ro). Volume 7D = KLGD trung bình
    7 phiên cuối so với trung bình cả cửa sổ. Trend = độ dốc hồi quy của giá đóng cửa
    (ngưỡng ±0.1%/phiên). Báo cáo mang tính mô tả dữ liệu lịch sử, không phải khuyến nghị
    đầu tư — không có yếu tố dự báo.
  </footer>
</div>
</body>
</html>
"""

    os.makedirs(REPORT_DIR, exist_ok=True)
    out = os.path.join(REPORT_DIR, f"stock_report_{today}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(out)


if __name__ == "__main__":
    main()
