import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = False  # テスト時のみTrueにする
# ==========================================

def get_demand_insight(dt):
    """日付から実需の強さを判定"""
    day, weekday = dt.day, dt.weekday()
    if weekday == 0: # 月曜日の場合、土日の分も考慮
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール適用日）"
    if day % 5 == 0: return "🐂【強気】ゴト日のドル買い需要"
    return "⚖️【中立】通常の実需（仲値に向けた動き）"

def is_gotobi(dt):
    """ゴトー日判定ロジック"""
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンドの計算（期間10）"""
    try:
        # スプレッドが落ち着いたレートを取得するため5分足を使用
        df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
        if len(df) < 10: return None, None
        sma = df['Close'].rolling(window=10).mean()
        std = df['Close'].rolling(window=10).std()
        price = df['Close'].iloc[-1]
        lower = sma.iloc[-1] - (2 * std.iloc[-1])
        return price, lower
    except: return None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    
    # ゴトー日でない、かつテストモードでない場合は終了
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_lower = get_technicals()
    if price is None: return

    insight = get_demand_insight(now)
    msg, status = "", "監視中"

    # --- 判定ロジック（遅延対策・幅を持たせた判定） ---

    if FORCE_TEST_MODE:
        msg = f"🧪【テスト配信】\n判定: {insight}\n現在値: {price:.3f}円\n※動作確認用メッセージです。"
        status = "テスト成功"

    # 1. 監視開始：07:45 〜 08:10 の間に起動した場合
    elif "07:45" <= current_time <= "08:10":
        msg = f"📅 【監視開始レポート】\n需給: {insight
