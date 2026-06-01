#!/usr/bin/env python3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from pathlib import Path
import statistics

# Read CSV
df = pd.read_csv('data/stock_data.csv')
df['Date'] = pd.to_datetime(df['Date'])

# Get latest date
latest_date = df['Date'].max()
print(f"Latest date in data: {latest_date.date()}")

# Calculate metrics for last 30 days
cutoff_date = latest_date - timedelta(days=30)
df_30d = df[df['Date'] >= cutoff_date].copy()

metrics = {}
tickers = sorted(df['Ticker'].unique())

for ticker in tickers:
    ticker_data = df[df['Ticker'] == ticker].sort_values('Date')
    ticker_data_30d = df_30d[df_30d['Ticker'] == ticker].sort_values('Date')

    if len(ticker_data) == 0:
        continue

    # Return (all time)
    first_close = ticker_data['Close'].iloc[0]
    last_close = ticker_data['Close'].iloc[-1]
    return_all = ((last_close - first_close) / first_close) * 100

    # Return 30D
    if len(ticker_data_30d) > 0:
        first_close_30d = ticker_data_30d['Close'].iloc[0]
        last_close_30d = ticker_data_30d['Close'].iloc[-1]
        return_30d = ((last_close_30d - first_close_30d) / first_close_30d) * 100
    else:
        return_30d = 0

    # Daily returns for volatility (30D)
    if len(ticker_data_30d) > 1:
        daily_returns = []
        for i in range(1, len(ticker_data_30d)):
            ret = (ticker_data_30d['Close'].iloc[i] - ticker_data_30d['Close'].iloc[i-1]) / ticker_data_30d['Close'].iloc[i-1] * 100
            daily_returns.append(ret)
        volatility = np.std(daily_returns) if daily_returns else 0
    else:
        volatility = 0

    # Trend (linear regression on 30D)
    if len(ticker_data_30d) > 1:
        x = np.arange(len(ticker_data_30d))
        y = ticker_data_30d['Close'].values
        z = np.polyfit(x, y, 1)
        trend_slope = z[0]
        if trend_slope > 0.1:
            trend = "Tăng ↑"
        elif trend_slope < -0.1:
            trend = "Giảm ↓"
        else:
            trend = "Sideway →"
    else:
        trend = "N/A"

    # Volume trend (last 7 days vs all)
    if len(ticker_data_30d) >= 7:
        vol_7d_avg = ticker_data_30d['Volume'].tail(7).mean()
        vol_all_avg = ticker_data_30d['Volume'].mean()
        vol_trend = (vol_7d_avg / vol_all_avg - 1) * 100 if vol_all_avg > 0 else 0
    else:
        vol_trend = 0

    metrics[ticker] = {
        'return_all': round(return_all, 2),
        'return_30d': round(return_30d, 2),
        'volatility': round(volatility, 2),
        'trend': trend,
        'volume_trend': round(vol_trend, 2),
        'latest_close': round(last_close, 2),
        'latest_date': latest_date.strftime('%Y-%m-%d')
    }

# Save metrics
Path('data/pipeline').mkdir(parents=True, exist_ok=True)
with open('data/pipeline/stock_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("✓ Metrics saved to data/pipeline/stock_metrics.json")

# Ranking: score based on return_30d (70%), trend (20%), volatility inverse (10%)
scores = {}
for ticker, m in metrics.items():
    # Normalize return_30d: scale to 0-100
    return_score = max(0, min(100, (m['return_30d'] + 20) * 2.5))

    # Trend score
    trend_score = 30 if "Tăng" in m['trend'] else (10 if "Sideway" in m['trend'] else 0)

    # Volatility score (lower is better)
    vol_score = max(0, 50 - m['volatility'] * 2)

    # Combined score
    score = return_score * 0.6 + trend_score * 0.3 + vol_score * 0.1
    scores[ticker] = score

# Sort by score
ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

print("\n📊 Ranking:")
for i, (ticker, score) in enumerate(ranked, 1):
    m = metrics[ticker]
    print(f"{i}. {ticker:5} | Score: {score:6.1f} | Return 30D: {m['return_30d']:7.2f}% | Vol: {m['volatility']:5.2f}% | {m['trend']}")

# Classification
top_3 = [t[0] for t in ranked[:3]]
mid = [t[0] for t in ranked[3:7]]
bottom = [t[0] for t in ranked[7:]]

print(f"\n✅ Nên xem xét: {', '.join(top_3)}")
print(f"⚠️  Theo dõi thêm: {', '.join(mid)}")
print(f"❌ Tránh / chờ: {', '.join(bottom)}")

# Create HTML report
html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Daily Briefing</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.4;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a1a1a;
            font-size: 28px;
            margin-bottom: 10px;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        .date {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13px;
        }}
        .summary-table th {{
            background: #f0f0f0;
            color: #333;
            font-weight: 600;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #ddd;
        }}
        .summary-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .summary-table tr:hover {{
            background: #fafafa;
        }}
        .ticker {{
            font-weight: 600;
            color: #0066cc;
        }}
        .positive {{
            color: #22ab94;
            font-weight: 500;
        }}
        .negative {{
            color: #e74c3c;
            font-weight: 500;
        }}
        .neutral {{
            color: #7f8c8d;
        }}
        .section {{
            margin: 25px 0;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .picks {{
            display: grid;
            gap: 15px;
        }}
        .pick-item {{
            background: #f9f9f9;
            padding: 15px;
            border-left: 4px solid #0066cc;
            border-radius: 4px;
        }}
        .pick-item.top {{
            border-left-color: #22ab94;
            background: #f0fdf9;
        }}
        .pick-item.mid {{
            border-left-color: #f39c12;
            background: #fef9f0;
        }}
        .pick-item.bottom {{
            border-left-color: #e74c3c;
            background: #fef0f0;
        }}
        .pick-title {{
            font-weight: 700;
            font-size: 16px;
            margin-bottom: 6px;
            color: #1a1a1a;
        }}
        .pick-desc {{
            font-size: 13px;
            color: #555;
            line-height: 1.5;
        }}
        .legend {{
            display: flex;
            gap: 20px;
            font-size: 12px;
            margin-top: 15px;
            padding: 12px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 2px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #999;
            text-align: right;
        }}
        @media print {{
            body {{ padding: 0; }}
            .container {{ max-width: 100%; box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 VN Stock Daily Briefing</h1>
        <div class="date">Ngày {latest_date.strftime('%d/%m/%Y')} (Dữ liệu: {latest_date.strftime('%Y-%m-%d')})</div>

        <div class="section">
            <div class="section-title">Bảng tóm tắt 10 mã</div>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Mã</th>
                        <th>Return 30D</th>
                        <th>Volatility</th>
                        <th>Trend</th>
                        <th>Vol Trend</th>
                        <th>Giá</th>
                    </tr>
                </thead>
                <tbody>
"""

# Add all stocks to summary table
for ticker, score in ranked:
    m = metrics[ticker]
    ret_class = "positive" if m['return_30d'] > 0 else "negative" if m['return_30d'] < 0 else "neutral"
    vol_class = "positive" if m['volume_trend'] > 0 else "negative"

    html_content += f"""                    <tr>
                        <td><span class="ticker">{ticker}</span></td>
                        <td><span class="{ret_class}">{m['return_30d']:+.2f}%</span></td>
                        <td>{m['volatility']:.2f}%</td>
                        <td>{m['trend']}</td>
                        <td><span class="{vol_class}">{m['volume_trend']:+.1f}%</span></td>
                        <td>{m['latest_close']:,.0f}</td>
                    </tr>
"""

html_content += """                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">🎯 Top picks hôm nay</div>
            <div class="picks">
"""

# Top 3 picks
for i, ticker in enumerate(top_3, 1):
    m = metrics[ticker]
    reason = f"Return 30D: {m['return_30d']:+.1f}%, Trend: {m['trend']}, Volatility: {m['volatility']:.1f}%"
    html_content += f"""                <div class="pick-item top">
                    <div class="pick-title">#{i} {ticker} — Nên xem xét</div>
                    <div class="pick-desc">{reason}</div>
                </div>
"""

html_content += """            </div>
        </div>

        <div class="section">
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #22ab94;"></div>
                    <span><strong>Tăng ↑:</strong> Xu hướng tích cực</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f39c12;"></div>
                    <span><strong>Sideway →:</strong> Dao động ngang</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e74c3c;"></div>
                    <span><strong>Giảm ↓:</strong> Xu hướng tiêu cực</span>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>Lưu ý: Báo cáo này chỉ mang tính chất tham khảo. Không phải lời khuyên đầu tư. Vui lòng tự kiểm tra trước khi quyết định.</p>
            <p>Cập nhật: {datetime.now().strftime('%H:%M:%S')} | Dữ liệu: 30 ngày gần nhất</p>
        </div>
    </div>
</body>
</html>"""

# Save HTML report
Path('data/reports').mkdir(parents=True, exist_ok=True)
report_path = f"data/reports/stock_report_{latest_date.strftime('%Y-%m-%d')}.html"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ HTML report saved to {report_path}")

# Save last analyzed date
Path('logs').mkdir(parents=True, exist_ok=True)
with open('logs/last_analyzed.txt', 'w') as f:
    f.write(latest_date.strftime('%Y-%m-%d'))

print(f"✓ Last analyzed date saved: {latest_date.strftime('%Y-%m-%d')}")
print("\n✅ Pipeline complete!")
