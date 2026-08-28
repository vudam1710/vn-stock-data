#!/usr/bin/env python3
"""Tính metrics 30 ngày gần nhất cho từng ticker trong config.yaml.

Chỉ dùng stdlib (không có pandas trong runner).
Output: data/pipeline/stock_metrics.json
"""

import csv
import json
import os
import re
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "stock_data.csv")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
OUT_PATH = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")

WINDOW = 30  # số phiên gần nhất


def read_tickers(path):
    """Đọc danh sách tickers từ config.yaml mà không cần PyYAML."""
    tickers = []
    in_block = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^tickers\s*:", line):
                in_block = True
                continue
            if in_block:
                m = re.match(r"^\s+-\s*([A-Za-z0-9.]+)", line)
                if m:
                    tickers.append(m.group(1))
                elif line.strip() and not line.strip().startswith("#"):
                    break
    return tickers


def slope(values):
    """Least-squares slope trên index 0..n-1."""
    n = len(values)
    xm = (n - 1) / 2
    ym = sum(values) / n
    num = sum((i - xm) * (v - ym) for i, v in enumerate(values))
    den = sum((i - xm) ** 2 for i in range(n))
    return num / den if den else 0.0


def main():
    tickers = read_tickers(CONFIG_PATH)

    rows = defaultdict(list)
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                close = float(r["Close"])
                vol = float(r["Volume"])
            except (TypeError, ValueError):
                continue  # bỏ qua dòng thiếu data
            rows[r["Ticker"]].append((r["Date"], close, vol))

    all_dates = sorted({d for t in rows.values() for d, _, _ in t})
    latest_date = all_dates[-1]
    window_dates = all_dates[-WINDOW:]

    metrics = {}
    missing = []

    for tk in tickers:
        series = sorted(rows.get(tk, []))
        series = [s for s in series if s[0] >= window_dates[0]]
        if len(series) < 5:
            missing.append(tk)
            continue

        closes = [c for _, c, _ in series]
        vols = [v for _, _, v in series]

        rets = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
        vol_pct = statistics.stdev(rets) if len(rets) > 1 else 0.0
        ret_30d = (closes[-1] / closes[0] - 1) * 100

        sl = slope(closes)
        sl_pct = sl / statistics.mean(closes) * 100  # %/phiên, chuẩn hoá theo giá
        if sl_pct > 0.1:
            trend = "tăng"
        elif sl_pct < -0.1:
            trend = "giảm"
        else:
            trend = "sideway"

        avg_all = statistics.mean(vols)
        avg_7 = statistics.mean(vols[-7:]) if len(vols) >= 7 else avg_all
        vol_trend = (avg_7 / avg_all - 1) * 100 if avg_all else 0.0

        metrics[tk] = {
            "ticker": tk,
            "sessions": len(series),
            "first_date": series[0][0],
            "last_date": series[-1][0],
            "last_close": round(closes[-1], 2),
            "return_30d_pct": round(ret_30d, 2),
            "volatility_pct": round(vol_pct, 2),
            "trend": trend,
            "trend_slope_pct_per_session": round(sl_pct, 3),
            "volume_trend_pct": round(vol_trend, 1),
            "risk_adjusted": round(ret_30d / vol_pct, 2) if vol_pct else 0.0,
            "closes": [round(c, 2) for c in closes],
            "dates": [d for d, _, _ in series],
        }

    # Xếp hạng: risk-adjusted return là trục chính, cộng thưởng cho trend tăng
    def score(m):
        bonus = {"tăng": 0.5, "sideway": 0.0, "giảm": -0.5}[m["trend"]]
        return m["risk_adjusted"] + bonus

    ranked = sorted(metrics.values(), key=score, reverse=True)
    for i, m in enumerate(ranked):
        m["rank"] = i + 1
        m["score"] = round(score(m), 2)
        m["group"] = "buy" if i < 3 else ("watch" if i < 7 else "avoid")

    out = {
        "generated_for_data_date": latest_date,
        "window_sessions": len(window_dates),
        "window_start": window_dates[0],
        "missing_tickers": missing,
        "ranking": [m["ticker"] for m in ranked],
        "metrics": {m["ticker"]: m for m in ranked},
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"latest_date={latest_date} window={window_dates[0]}..{latest_date} missing={missing}")
    for m in ranked:
        print(
            f"{m['rank']:2d}. {m['ticker']:4s} ret={m['return_30d_pct']:7.2f}% "
            f"vol={m['volatility_pct']:5.2f}% trend={m['trend']:8s} "
            f"volΔ={m['volume_trend_pct']:6.1f}% RA={m['risk_adjusted']:6.2f} -> {m['group']}"
        )


if __name__ == "__main__":
    main()
