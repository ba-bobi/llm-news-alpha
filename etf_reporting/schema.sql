-- ETF analytics SQLite schema
CREATE TABLE IF NOT EXISTS etf_daily (
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    avg_dollar_vol_30d REAL,
    rsi14 REAL,
    ma20 REAL,
    ma60 REAL,
    macd REAL,
    macd_signal REAL,
    pe_ratio REAL,
    expense_ratio REAL,
    ytd_return REAL,
    PRIMARY KEY (date, ticker)
);
