import os
import sqlite3
import datetime as dt
from zoneinfo import ZoneInfo
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "kiwoom_bot.db")
PAGE_ID = "30f74643-ea79-800e-8202-c4bb44404676"
TOKEN = os.getenv("NOTION_TOKEN", "")
KST = ZoneInfo("Asia/Seoul")


def to_blocks(today, trades):
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"모의투자 일지 - {today} 장마감"}}]},
        }
    ]

    if not trades:
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "오늘 체결 내역 없음(관망)."}}]},
            }
        )
        return blocks

    for tr in trades:
        ts, ticker, side, qty, price, amount, reason_buy, reason_sell, source, status = tr
        reason = reason_buy if side == "BUY" else reason_sell
        line = f"[{ts}] {ticker} {side} {int(qty)}주 @ {price:.0f} (금액 {amount:.0f}) | {source}/{status}"
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line}}]},
        })
        if reason:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"- 근거: {reason}"}}]},
            })

    return blocks


def main():
    if not TOKEN:
        raise RuntimeError("NOTION_TOKEN missing")

    today = dt.datetime.now(KST).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ts,ticker,side,qty,price,amount,reason_buy,reason_sell,source,status FROM trades WHERE trade_date=? ORDER BY ts",
        (today,),
    ).fetchall()
    conn.close()

    blocks = to_blocks(today, rows)
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    r = requests.patch(
        f"https://api.notion.com/v1/blocks/{PAGE_ID}/children",
        headers=headers,
        json={"children": blocks},
        timeout=30,
    )
    print(r.status_code)
    print(r.text[:200])


if __name__ == "__main__":
    main()
