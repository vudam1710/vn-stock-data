#!/usr/bin/env python3
"""Render HTML report 1 trang từ data/pipeline/stock_metrics.json."""

import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")

PALETTE = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed",
           "#0891b2", "#db2777", "#65a30d", "#475569", "#ea580c"]

GROUP_LABEL = {
    "nen_xem_xet": ("✅ Nên xem xét", "buy"),
    "theo_doi_them": ("⚠️ Theo dõi thêm", "watch"),
    "tranh_cho": ("❌ Tránh / chờ", "avoid"),
}

CSS = """
  :root {
    --bg:#f7f8fa; --card:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb;
    --pos:#15803d; --neg:#b91c1c; --buy:#15803d; --watch:#b45309; --avoid:#9ca3af;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif; }
  .wrap { max-width:1000px; margin:0 auto; padding:18px 20px 26px; }
  header { display:flex; align-items:baseline; justify-content:space-between;
    gap:12px; flex-wrap:wrap; border-bottom:2px solid var(--ink); padding-bottom:8px; }
  h1 { font-size:20px; margin:0; letter-spacing:-.2px; }
  .sub { color:var(--muted); font-size:12px; }
  .grid { display:grid; grid-template-columns:1.35fr 1fr; gap:16px; margin-top:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:8px;
    padding:12px 14px; }
  h2 { font-size:12px; text-transform:uppercase; letter-spacing:.6px;
    color:var(--muted); margin:0 0 8px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; }
  th { text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.4px;
    color:var(--muted); font-weight:600; padding:0 6px 5px; border-bottom:1px solid var(--line); }
  td { padding:4.5px 6px; border-bottom:1px solid #f1f2f4; }
  tr:last-child td { border-bottom:none; }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .tk { font-weight:700; }
  .pos { color:var(--pos); } .neg { color:var(--neg); }
  .rec { white-space:nowrap; font-size:11.5px; }
  .rec.buy { color:var(--buy); font-weight:600; }
  .rec.watch { color:var(--watch); }
  .rec.avoid { color:var(--avoid); }
  .r-buy td { background:#f0fdf4; }
  svg { width:100%; height:auto; display:block; }
  line.grid { stroke:#eceef1; stroke-width:1; }
  line.baseline { stroke:#9ca3af; stroke-width:1; stroke-dasharray:3 3; }
  text.axis { font-size:9px; fill:var(--muted); }
  .legend { display:flex; flex-wrap:wrap; gap:4px 12px; margin-top:6px; font-size:10.5px;
    color:var(--muted); }
  .lg i { display:inline-block; width:9px; height:2.5px; border-radius:2px;
    margin-right:4px; vertical-align:middle; }
  .pick { padding:8px 0; border-bottom:1px dashed var(--line); }
  .pick:last-child { border-bottom:none; padding-bottom:0; }
  .pick-h { display:flex; align-items:baseline; gap:8px; }
  .pick-tk { font-weight:700; font-size:14px; }
  .pick-m { font-size:10.5px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .pick p { margin:3px 0 0; font-size:12px; }
  .note { font-size:11px; color:var(--muted); margin:8px 0 0; }
  footer { margin-top:14px; font-size:10.5px; color:var(--muted);
    border-top:1px solid var(--line); padding-top:8px; }
  @media (max-width:820px) { .grid { grid-template-columns:1fr; } }
"""


def sign(v, digits=2, suffix="%"):
    cls = "pos" if v > 0 else ("neg" if v < 0 else "")
    return f'<span class="{cls}">{v:+.{digits}f}{suffix}</span>'


def build_chart(metrics, w=560, h=250):
    pad_l, pad_r, pad_t, pad_b = 34, 8, 10, 20
    n = max(len(m["closes"]) for m in metrics)
    series = []
    for i, m in enumerate(sorted(metrics, key=lambda x: x["rank"])):
        base = m["closes"][0]
        series.append((m["ticker"], [c / base * 100 for c in m["closes"]], PALETTE[i % len(PALETTE)]))

    ys = [v for _, vals, _ in series for v in vals]
    lo, hi = min(ys), max(ys)
    span = max(hi - lo, 1)
    lo, hi = lo - span * 0.08, hi + span * 0.08

    def px(i, total):
        return pad_l + (w - pad_l - pad_r) * (i / max(total - 1, 1))

    def py(v):
        return pad_t + (h - pad_t - pad_b) * (1 - (v - lo) / (hi - lo))

    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Hiệu suất chuẩn hoá về 100">']
    step = 5 if (hi - lo) < 35 else 10
    tick = int(lo // step) * step
    while tick <= hi:
        if tick >= lo:
            y = py(tick)
            cls = "baseline" if tick == 100 else "grid"
            parts.append(f'<line class="{cls}" x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}"/>')
            parts.append(f'<text class="axis" x="{pad_l-5:.0f}" y="{y+3:.1f}" text-anchor="end">{tick}</text>')
        tick += step

    for ticker, vals, color in series:
        pts = " ".join(f"{px(i, len(vals)):.1f},{py(v):.1f}" for i, v in enumerate(vals))
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.6" '
                     f'stroke-linejoin="round" points="{pts}"/>')
        parts.append(f'<circle cx="{px(len(vals)-1, len(vals)):.1f}" cy="{py(vals[-1]):.1f}" '
                     f'r="2.2" fill="{color}"/>')

    dates = sorted(metrics, key=lambda m: m["rank"])[0]["dates"]
    for i in (0, len(dates) // 2, len(dates) - 1):
        anchor = "start" if i == 0 else ("end" if i == len(dates) - 1 else "middle")
        parts.append(f'<text class="axis" x="{px(i, len(dates)):.1f}" y="{h-6}" '
                     f'text-anchor="{anchor}">{dates[i][5:]}</text>')

    parts.append("</svg>")
    legend = " ".join(
        f'<span class="lg"><i style="background:{c}"></i>{t}</span>' for t, _, c in series
    )
    parts.append(f'<div class="legend">{legend}</div>')
    return "\n".join(parts)


def main():
    with open(METRICS, encoding="utf-8") as f:
        data = json.load(f)

    metrics = data["metrics"]
    picks_text = json.load(open(os.path.join(ROOT, "data", "pipeline", "picks.json"), encoding="utf-8"))
    today = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    rows = []
    for m in metrics:
        label, cls = GROUP_LABEL[m["group"]]
        tr_cls = ' class="r-buy"' if m["group"] == "nen_xem_xet" else ""
        rows.append(
            f"<tr{tr_cls}>"
            f'<td class="num" style="color:var(--muted)">{m["rank"]}</td>'
            f'<td class="tk">{m["ticker"]}</td>'
            f'<td class="num">{m["close_last"]:.1f}</td>'
            f'<td class="num">{sign(m["return_30d_pct"])}</td>'
            f'<td class="num">{m["volatility_pct"]:.2f}%</td>'
            f'<td>{m["trend"]}</td>'
            f'<td class="num">{sign(m["volume_trend_pct"], 0)}</td>'
            f'<td class="rec {cls}">{label}</td>'
            "</tr>"
        )

    by_ticker = {m["ticker"]: m for m in metrics}
    picks = []
    for tk in picks_text["order"]:
        m = by_ticker[tk]
        picks.append(
            f'<div class="pick"><div class="pick-h"><span class="pick-tk">{tk}</span>'
            f'<span class="pick-m">{m["return_30d_pct"]:+.2f}% · vol {m["volatility_pct"]:.2f}% '
            f'· {m["trend"]}</span></div><p>{picks_text["notes"][tk]}</p></div>'
        )

    missing = data.get("missing_tickers") or []
    missing_note = (
        f'<p class="note">Thiếu data: {", ".join(missing)} — đã loại khỏi xếp hạng.</p>'
        if missing else
        '<p class="note">Đủ data cho cả 10 mã trong cửa sổ quan sát.</p>'
    )

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VN Stock Daily Briefing — {today}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>VN Stock Daily Briefing — {today}</h1>
  <div class="sub">Data đến {data['window_end']} · {data['window_sessions']} phiên
    ({data['window_start']} → {data['window_end']})</div>
</header>

<div class="grid">
  <section class="card">
    <h2>Tóm tắt 10 mã theo dõi</h2>
    <table>
      <thead><tr>
        <th class="num">#</th><th>Mã</th><th class="num">Close</th>
        <th class="num">Return 30D</th><th class="num">Volatility</th>
        <th>Trend</th><th class="num">Volume 7D</th><th>Khuyến nghị</th>
      </tr></thead>
      <tbody>
        {chr(10).join(rows)}
      </tbody>
    </table>
    {missing_note}
  </section>

  <section class="card">
    <h2>Top picks hôm nay</h2>
    {chr(10).join(picks)}
  </section>
</div>

<section class="card" style="margin-top:16px">
  <h2>Hiệu suất so sánh — Close chuẩn hoá về 100 tại {data['window_start']}</h2>
  {build_chart(metrics)}
</section>

<footer>
  Xếp hạng theo risk-adjusted score = Return 30D / Volatility + 2 × slope(%/phiên).
  Volatility = độ lệch chuẩn daily return. Volume 7D = TB 7 phiên cuối so với TB cả kỳ.
  Báo cáo mang tính mô tả, không phải khuyến nghị đầu tư.
</footer>
</div>
</body>
</html>
"""

    out_dir = os.path.join(ROOT, "data", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"stock_report_{today}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(out_path)


if __name__ == "__main__":
    main()
