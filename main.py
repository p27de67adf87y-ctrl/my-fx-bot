import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
# 2月20日の本番に向けて False に設定済みです
FORCE_TEST_MODE = False  
# ==========================================

def get_demand_insight(dt):
    """日付と曜日から実需の強さを判定（需給インサイト）"""
    day, weekday = dt.day, dt.weekday()
    # マンデー・ルール判定
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール適用日）"
    
    if day == 5: return "🐂【強気】5日の輸入企業決済（ドル買い優勢）"
    if day == 30: return "🐻【警戒】末日の輸出企業決済（ドル売り交錯）"
    return "⚖️【中立】通常のゴト日実需（仲値に向けた買い）"

def is_gotobi(dt):
    """ゴトー日判定ロジック"""
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0: # 月曜日の振替判定
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンドの計算（バックテスト最適化済み：期間10）"""
    try:
        df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
        if len(df) < 10: return None, None
        # パラメータ: 期間10, 標準偏差2
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
    
    # 1. ゴトー日以外は沈黙
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_lower = get_technicals()
    if price is None: return

    insight = get_demand_insight(now)
    msg, status = "", "監視中"

    # --- 配信ロジック（ミニマル構成） ---

    # テストモード実行時
    if FORCE_TEST_MODE:
        msg = f"🧪【テスト配信】\n判定: {insight}\n現在値: {price:.3f}円"
        status = "テスト成功"

    # 朝の定時レポート (08:00台)
    elif "08:00" <= current_time <= "08:30":
        msg = f"📅 【ゴト日・朝の監視レポート】\n需給: {insight}\n現在値: {price:.3f}円"
        status = "監視開始"

    # 押し目買い判定 (07:00台)
    elif "07:00" <= current_time < "08:00":
        if price <= bb_lower:
            msg = f"🚩【条件合致】押し目買い実行\n需給: {insight}"
            status = "ロング実行"

    # 決済報告 (09:50)
    elif "09:50" <= current_time <= "10:10":
        msg = "🚨【全決済】仲値公示前の撤退規律"
        status = "ポジション解消"

    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        # 役職や緊急度に応じたカラーコード設定
        color = 3066993 if "📅" in msg else 16711680 if "🚨" in msg else 3447003
        payload = {"embeds": [{"title": "📊 Gotobi Bot (Optimized)", "description": msg, "color": color}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {
            "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
            "strategy": "実需・期間10モデル",
            "price": price,
            "status": status
        }
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
