import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

FORCE_TEST_MODE = False

def get_demand_insight(dt):
    day, weekday = dt.day, dt.weekday()
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮された爆発的需要（マンデー・ルール適用日）"
    if day == 5: return "🐂【強気】輸入企業のドル買い需要が突出する日"
    if day == 30: return "🐻【警戒】輸出企業の決済（ドル売り）が強まる日"
    return "⚖️【中立】通常のゴト日実需（ドル買い優勢 70%）"

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
        price = df['Close'].iloc[-1]
        upper = sma.iloc[-1] + (2 * std.iloc[-1])
        lower = sma.iloc[-1] - (2 * std.iloc[-1])
        return price, upper, lower
    except: return None, None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    price, bb_upper, bb_lower = get_technicals()
    if price is None: return
    insight = get_demand_insight(now)
    msg, status = "", "待機中"

    if "08:00" <= current_time <= "08:30":
        msg = f"🌅 【生存確認】システム稼働中\n判定: {'ゴト日' if is_gotobi(now) else '通常日'}\n状況: {insight}\n現在値: {price:.3f}円"
        status = "システム点検"
    elif FORCE_TEST_MODE:
        msg, status = f"{insight}\n🧪 接続テスト中", "テスト成功"
    elif is_gotobi(now):
        if "07:00" <= current_time < "08:00":
            if price <= bb_lower:
                msg = f"{insight}\n🚩【ポジショニング】押し目買い好機 (BB -2σ)"
                status = "押し目買い"
        elif "09:00" <= current_time < "09:50":
            if price >= bb_upper:
                msg = f"{insight}\n⚠️【警戒】オーバーシュートにつき飛び乗り禁止"
                status = "追随回避"
            else:
                msg = f"{insight}\n📈【加速フェーズ】仲値へ向けたドル買いモメンタム"
                status = "ロング追随"
        elif "09:50" <= current_time <= "10:10":
            msg = "🚨【全決済】リバーストレード回避（9:55公示前の撤退）"
            status = "ポジション解消"
    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        payload = {"embeds": [{"title": "📊 Gotobi Strategy Report", "description": f"{msg}\n**Price:** {price:.3f}", "color": 3066993}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "需給分析", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
