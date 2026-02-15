import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

FORCE_TEST_MODE = False # テストが終わったらFalseにしてください

def get_demand_insight(dt):
    """
    JFX小林社長のインサイトに基づく需給の質を判定 
    """
    day = dt.day
    weekday = dt.weekday()
    
    # 明日2月16日のような「マンデー・ルール」適用時 
    if weekday == 0:
        sun = dt - timedelta(days=1)
        sat = dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮された爆発的需要に注意" # 

    if day == 5:
        return "🐂【強気】輸入企業のドル買い需要が突出する日" # 
    elif day == 30:
        return "🐻【警戒】輸出企業の決済（ドル売り）が強まる傾向" # 
    else:
        return "⚖️【中立】通常のゴトー日実需（ドル買い優勢 70%）" # 

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
        if len(df) < 20: return None, None, None
        sma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        return df['Close'].iloc[-1], sma.iloc[-1] + (2 * std.iloc[-1]), sma.iloc[-1] - (2 * std.iloc[-1])
    except: return None, None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    price, bb_upper, bb_lower = get_technicals()
    
    # 小林社長のインサイトを取得
    insight = get_demand_insight(now)
    msg = ""
    status = "待機中"

    if FORCE_TEST_MODE:
        msg = f"{insight}\n🧪 接続テスト中"
        status = "テスト成功"
    elif is_gotobi(now):
        if "07:00" <= current_time < "08:00":
            if price <= bb_lower:
                msg = f"{insight}\n🚩【ポジショニング】押し目買い好機 [cite: 19, 27]"
                status = "押し目買い"
        elif "09:00" <= current_time < "09:55":
            if price >= bb_upper:
                msg = f"{insight}\n⚠️【警戒】オーバーシュートにつき飛び乗り禁止 [cite: 27]"
                status = "追随回避"
            else:
                msg = f"{insight}\n📈【加速・追随】仲値へ向けたドル買い優勢 [cite: 11, 20]"
                status = "ロング追随"
        elif "09:55" <= current_time <= "10:10":
            msg = "🚨【全決済】10:00の流動性の真空を回避せよ [cite: 21, 23]"
            status = "ポジション解消"

    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        payload = {"embeds": [{"title": "📊 需給・インサイト判定", "description": f"{msg}\n**現在値:** {price:.3f} 円", "color": 16711680 if "特強気" in msg else 3066993}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "インサイト戦略", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
