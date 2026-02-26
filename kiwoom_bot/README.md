# Kiwoom Mock Trading Bot (Hybrid Strategy)

- Strategy: hybrid (trend + mean reversion)
- Universe: configurable in `kiwoom_bot_config.json`
- Risk: daily loss cap 3%, max position count and max order size configurable
- Journal: uploads daily close trading diary to Notion page

## Files
- `kiwoom_mixed_bot.py`: intraday decision engine
- `kiwoom_daily_journal_notion.py`: daily journal uploader

## Notes
- Current order function uses SIM mode unless `KIWOOM_ACCESS_TOKEN` and `KIWOOM_ORDER_URL` are set.
- Token endpoint verified for mock: `https://mockapi.kiwoom.com/oauth2/token`.
