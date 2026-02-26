@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\bobi\.openclaw\workspace"
python kiwoom_daily_journal_notion.py
