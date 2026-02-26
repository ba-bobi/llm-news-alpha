import os
import json
import sqlite3
import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
import requests

KST = ZoneInfo("Asia/Seoul")
DB_PATH = os.path.join(os.path.dirname(__file__), "kiwoom_bot.db")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "kiwoom_bot_config.json")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        cfg = {
            "tickers": ["005930.KS", "000660.KS", "035420.KS", "105560.KS", "069500.KS"],
            "max_position_count": 3,
            "max_order_pct": 0.10,
            "daily_loss_limit_pct": 0.03,
            "starting_cash": 10000000,
            "simulate_only": True,
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio (
            ticker TEXT PRIMARY KEY,
            qty REAL NOT NULL,
            avg_price REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            reason_buy TEXT,
            reason_sell TEXT,
            source TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS account_state (
            k TEXT PRIMARY KEY,
            v TEXT NOT NULL
        )
        """
    )
    conn.commit()


def get_state(conn, k, default=None):
    row = conn.execute("SELECT v FROM account_state WHERE k=?", (k,)).fetchone()
    return row[0] if row else default


def set_state(conn, k, v):
    conn.execute("INSERT OR REPLACE INTO account_state(k,v) VALUES(?,?)", (k, str(v)))
    conn.commit()


def get_cash(conn, starting_cash):
    v = get_state(conn, "cash", None)
    if v is None:
        set_state(conn, "cash", starting_cash)
        return float(starting_cash)
    return float(v)


def set_cash(conn, cash):
    set_state(conn, "cash", cash)


def rsi(series: pd.Series, period=14):
    d = series.diff()
    up = d.clip(lower=0).rolling(period).mean()
    dn = (-d.clip(upper=0)).rolling(period).mean()
    rs = up / (dn + 1e-9)
    return 100 - 100 / (1 + rs)


def signal_for_ticker(ticker: str):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    close = df["Close"].dropna()
    if len(close) < 70:
        return None

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    r = rsi(close, 14)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    last = close.iloc[-1]
    score = 0
    reasons = []

    if last > ma20.iloc[-1] and ma20.iloc[-1] > ma60.iloc[-1]:
        score += 1
        reasons.append("추세 우상향(MA20>MA60, 현재가>MA20)")
    else:
        score -= 1
        reasons.append("추세 약화(MA 정렬 약함)")

    if macd.iloc[-1] > macd_signal.iloc[-1]:
        score += 1
        reasons.append("MACD 골든 방향")
    else:
        score -= 1
        reasons.append("MACD 데드 방향")

    if r.iloc[-1] <= 35:
        score += 1
        reasons.append("RSI 저점권(평균회귀 매수 우호)")
    elif r.iloc[-1] >= 70:
        score -= 1
        reasons.append("RSI 과열권(차익실현 우호)")

    side = "HOLD"
    if score >= 2:
        side = "BUY"
    elif score <= -2:
        side = "SELL"

    return {
        "ticker": ticker,
        "price": float(last),
        "score": score,
        "side": side,
        "reason": " / ".join(reasons),
    }


def place_order_mock_or_kiwoom(side, ticker, qty, price):
    token = os.getenv("KIWOOM_ACCESS_TOKEN", "")
    order_url = os.getenv("KIWOOM_ORDER_URL", "")

    if not token or not order_url:
        return {"source": "SIM", "status": "FILLED"}

    # 실제 키움 주문 엔드포인트/필드는 사용자 문서값으로 교체 필요
    payload = {
        "side": side,
        "ticker": ticker,
        "qty": qty,
        "price": price,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json;charset=UTF-8",
    }
    try:
        r = requests.post(order_url, json=payload, headers=headers, timeout=15)
        if r.status_code < 300:
            return {"source": "KIWOOM", "status": "FILLED", "raw": r.text[:200]}
        return {"source": "KIWOOM", "status": f"ERROR_{r.status_code}", "raw": r.text[:200]}
    except Exception as e:
        return {"source": "KIWOOM", "status": f"EXCEPTION:{e}"}


def run_once():
    cfg = load_config()
    now = dt.datetime.now(KST)
    today = now.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    cash = get_cash(conn, cfg["starting_cash"])
    max_order_amt = cash * float(cfg["max_order_pct"])

    # daily loss guard (simple realized PnL check)
    day_rows = conn.execute("SELECT side, amount FROM trades WHERE trade_date=?", (today,)).fetchall()
    realized = 0.0
    for s, amt in day_rows:
        if s == "SELL":
            realized += float(amt)
        elif s == "BUY":
            realized -= float(amt)
    if realized < -cfg["starting_cash"] * float(cfg["daily_loss_limit_pct"]):
        print("[GUARD] 일일 손실한도 초과로 거래 중지")
        return

    positions = {r[0]: {"qty": float(r[1]), "avg": float(r[2])} for r in conn.execute("SELECT ticker, qty, avg_price FROM portfolio").fetchall()}

    candidates = []
    for t in cfg["tickers"]:
        sig = signal_for_ticker(t)
        if sig:
            candidates.append(sig)

    # prioritize strongest signals
    candidates.sort(key=lambda x: abs(x["score"]), reverse=True)

    for sig in candidates:
        ticker, side, price = sig["ticker"], sig["side"], sig["price"]
        qty = int(max_order_amt // price)
        if qty <= 0:
            continue

        if side == "BUY":
            if ticker in positions:
                continue
            if len(positions) >= int(cfg["max_position_count"]):
                continue
            if cash < qty * price:
                continue

            res = place_order_mock_or_kiwoom("BUY", ticker, qty, price)
            if "FILLED" in res["status"]:
                cash -= qty * price
                positions[ticker] = {"qty": qty, "avg": price}
                conn.execute(
                    "INSERT INTO trades(ts,trade_date,ticker,side,qty,price,amount,reason_buy,reason_sell,source,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (now.strftime("%Y-%m-%d %H:%M:%S"), today, ticker, "BUY", qty, price, qty * price, sig["reason"], None, res["source"], res["status"]),
                )

        elif side == "SELL":
            if ticker not in positions:
                continue
            qty = int(positions[ticker]["qty"])
            if qty <= 0:
                continue

            buy_reason = sig["reason"]
            res = place_order_mock_or_kiwoom("SELL", ticker, qty, price)
            if "FILLED" in res["status"]:
                cash += qty * price
                conn.execute(
                    "INSERT INTO trades(ts,trade_date,ticker,side,qty,price,amount,reason_buy,reason_sell,source,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (now.strftime("%Y-%m-%d %H:%M:%S"), today, ticker, "SELL", qty, price, qty * price, None, buy_reason, res["source"], res["status"]),
                )
                del positions[ticker]

    conn.execute("DELETE FROM portfolio")
    for t, p in positions.items():
        conn.execute(
            "INSERT OR REPLACE INTO portfolio(ticker,qty,avg_price,updated_at) VALUES(?,?,?,?)",
            (t, p["qty"], p["avg"], now.strftime("%Y-%m-%d %H:%M:%S")),
        )

    set_cash(conn, cash)
    conn.commit()
    conn.close()
    print("bot run complete")


if __name__ == "__main__":
    run_once()
