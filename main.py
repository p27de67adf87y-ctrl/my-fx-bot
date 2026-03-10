import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = False  
# ==========================================

def get_demand_insight(dt):
    day, weekday = dt.day, dt.weekday()
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール適用日）"
    if day % 5 == 0: return "🐂【強気】ゴト日のドル買い需要"
    return "⚖️【中立】通常の実需（仲値に向けた動き）"

def is_gotobi(dt):
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    try:
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
    
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_lower = get_technicals()
    if price is None: return
    insight = get_demand_insight(now)
    msg, status = "", "監視中"

    # --- 判定ロジック（遅延に超強い設定） ---

    # 1. 監視開始：10:00より前で、まだ何も届いていない時間帯
    # 07:45から「09:30」まで判定幅を広げました。これで大遅刻しても挨拶が届きます。
    if "07:45" <= current_time <= "09:30":
        # 最初の挨拶（スプレッドシートへの記録なし、Discord通知のみ）
        msg = f"📅 【監視開始レポート】\n需給: {insight}\n現在値: {price:.3f}円\n※GitHubの遅延に関わらず、本日の監視を継続中です。"
        status = "監視開始"
        
        # もし安値なら、挨拶を「赤旗」に上書きする
        if price <= bb_lower:
            msg = f"🚩【条件合致】押し目買い実行\n現在値: {price:.3f}円\n⚠️ 10枚注文 ＋ 損切り(-20pips)をセット！"
            status = "ロング実行"

    # 2. 決済：09:45 〜 11:30 の間
    elif "09:45" <= current_time <= "11:30":
        msg = "🚨【全決済】仲値公示後のステータス更新\n本日のトレード時間を終了しました。"
        status = "ポジション解消"

    if msg:
        send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if discord_url:
        color = 3066993 if "📅" in msg else 16711680 if "🚨" in msg or "🚩" in msg else 3447003
        payload = {"embeds": [{"title": "📊 Gotobi Bot", "description": msg, "color": color}]}
        requests.post(discord_url, json=payload)
    
    # チャンス（旗）または決済（アラート）の時だけ、スプレッドシートに書く
    if gas_url and ("🚩" in msg or "🚨" in msg):
        data = {
            "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
            "strategy": "実需・期間10モデル",
            "price": price,
            "status": status
        }
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
