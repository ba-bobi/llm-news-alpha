# ETF Daily Reporting

- DB: SQLite (`etf_analytics.db`)
- Table: `etf_daily`
- Universe: liquid US ETFs candidate set, top 10 selected by 30-day average dollar volume
- Metrics:
  - OHLCV
  - Technical: RSI14, MA20, MA60, MACD, MACD Signal
  - Valuation/Fundamental proxy: trailing PE, expense ratio, YTD return
- Output PPT: `ETF 비교분석.pptx`

## Run
```bash
pip install -r ../requirements.txt
python etf_daily_report.py
```
