import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# 1. 判定ロジック：ゴトー日 & マンデー・ルール
def is_gotobi(dt):
    """5, 10...の日、または土日の場合は月曜日にスライド """
    day = dt.day
    weekday = dt.weekday() # 0:月 ... 6:日
    # 当日が5の倍数かつ平日
    if day % 5 == 0 and weekday < 5: return True
    # 月曜日の場合、土日が5の倍数だったかチェック
    if weekday == 0:
        sun = dt - timedelta(days=1)
        sat = dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンドの計算 """
    df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
    if len(df) < 20: return None, None
    sma = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    return df['Close'].iloc[-1], upper.iloc[-1], lower.iloc[-1]

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # ゴトー日判定
    if not is_gotobi(now): return

    price, bb_upper, bb_lower = get_technicals()
    if not price: return

    msg = ""
    # タイムラインによる戦略 [cite: 19, 20, 21]
    current_time = now.strftime("%H:%M")

    # フェーズ1: 07:00-08:00 押し目買い [cite: 19, 27]
    if "07:00" <= current_time < "08:00":
        if price <= bb_lower:
            msg = "🚩【絶好の押し目】実需の先読みロング検討"
    
    # フェーズ2: 09:00-09:55 加速・追随 [cite: 20, 27]
    elif "09:00" <= current_time < "09:55":
        if price >= bb_upper:
            msg = "⚠️【警戒】オーバーシュート（飛び乗り厳禁）"
        else:
            msg = "📈【加速フェーズ】仲値公示に向けたドル買い優勢"

    # フェーズ3: 09:55以降 逆回転回避 [cite: 21, 23]
    elif "09:55" <= current_time <= "10:10":
        msg = "🚨【全決済】流動性の真空による急落リスク回避"

    if msg:
        send_signals(price, msg)

def send_signals(price, msg):
    # Discord & GAS への送信（以前のコードと同様）
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if discord_url:
        payload = {"embeds": [{"title": "📊 需給分析レポートに基づく判定", "description": f"{msg}\n現在値: {price:.3f}円", "color": 16776960}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        requests.post(gas_url, json={"strategy": "レポート戦略判定", "price": price, "status": msg})

if __name__ == "__main__":
    run_strategy()
