#!/usr/bin/env python3
"""Tính metrics mô tả cho từng ticker từ 30 phiên gần nhất trong data/stock_data.csv."""

import csv
import json
import os
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "stock_data.csv")
OUT_PATH = os.path.join(ROOT, "data", "pipeline", "stock_metrics.json")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")

WINDOW = 30
VOL_RECENT = 7


def load_tickers():
    """Đọc danh sách tickers từ config.yaml (không hardcode)."""
    tickers, in_block = [], False
    with open(CONFIG_PATH, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("tickers:"):
                in_block = True
                continue
            if in_block:
                if stripped.startswith("- "):
                    tickers.append(stripped[2:].strip())
                elif stripped and not stripped.startswith("#"):
                    break
    return tickers


def slope(values):
    """Slope của linear regression theo index, chuẩn hoá thành %/phiên."""
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    if den == 0 or mean_y == 0:
        return 0.0
    return (num / den) / mean_y * 100


def classify_trend(slope_pct):
    if slope_pct > 0.15:
        return "tăng"
    if slope_pct < -0.15:
        return "giảm"
    return "sideway"


def main():
    tickers = load_tickers()
    rows_by_ticker = defaultdict(list)
    all_dates = set()

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            all_dates.add(row["Date"])
            rows_by_ticker[row["Ticker"]].append(row)

    dates = sorted(all_dates)
    window_dates = set(dates[-WINDOW:])
    latest_date = dates[-1]

    metrics, missing = [], []

    for ticker in tickers:
        rows = sorted(
            (r for r in rows_by_ticker.get(ticker, []) if r["Date"] in window_dates),
            key=lambda r: r["Date"],
        )
        if len(rows) < 3:
            missing.append(ticker)
            continue

        closes = [float(r["Close"]) for r in rows]
        volumes = [float(r["Volume"]) for r in rows]

        ret = (closes[-1] / closes[0] - 1) * 100
        daily = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
        vol = statistics.pstdev(daily) if len(daily) > 1 else 0.0
        sl = slope(closes)

        recent_vol = volumes[-VOL_RECENT:]
        avg_recent = sum(recent_vol) / len(recent_vol)
        avg_all = sum(volumes) / len(volumes)
        vol_trend = (avg_recent / avg_all - 1) * 100 if avg_all else 0.0

        metrics.append({
            "ticker": ticker,
            "sessions": len(rows),
            "first_date": rows[0]["Date"],
            "last_date": rows[-1]["Date"],
            "close_first": round(closes[0], 2),
            "close_last": round(closes[-1], 2),
            "return_30d_pct": round(ret, 2),
            "volatility_pct": round(vol, 2),
            "trend_slope_pct_per_session": round(sl, 3),
            "trend": classify_trend(sl),
            "volume_trend_pct": round(vol_trend, 1),
            "avg_volume": int(avg_all),
            "closes": [round(c, 2) for c in closes],
            "dates": [r["Date"] for r in rows],
        })

    # Điểm risk-adjusted: return / rủi ro, cộng thêm điểm trend
    for m in metrics:
        risk = max(m["volatility_pct"], 0.3)
        m["score"] = round(m["return_30d_pct"] / risk + m["trend_slope_pct_per_session"] * 2, 3)

    metrics.sort(key=lambda m: m["score"], reverse=True)

    n = len(metrics)
    top_n = 3
    bottom_n = 3 if n >= 8 else max(1, n // 3)
    for i, m in enumerate(metrics):
        m["rank"] = i + 1
        if i < top_n:
            m["group"] = "nen_xem_xet"
        elif i >= n - bottom_n:
            m["group"] = "tranh_cho"
        else:
            m["group"] = "theo_doi_them"

    out = {
        "generated_for_data_date": latest_date,
        "window_sessions": len(dates[-WINDOW:]),
        "window_start": dates[-WINDOW:][0],
        "window_end": latest_date,
        "total_dates_in_file": len(dates),
        "missing_tickers": missing,
        "metrics": metrics,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps({k: v for k, v in out.items() if k != "metrics"}, ensure_ascii=False))
    for m in metrics:
        print(f"{m['rank']:2d} {m['ticker']:4s} ret={m['return_30d_pct']:7.2f}% "
              f"vol={m['volatility_pct']:5.2f}% trend={m['trend']:8s} "
              f"volΔ={m['volume_trend_pct']:7.1f}% score={m['score']:7.2f} [{m['group']}]")


if __name__ == "__main__":
    main()
