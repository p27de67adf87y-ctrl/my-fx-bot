import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 【テスト用設定】ここを True にすると、今すぐDiscordに通知が飛びます
# 確認が終わったら False に戻すと、明日の朝から本番稼働します
FORCE_TEST_MODE = True 
# ==========================================

def is_gotobi(dt):
    """レポートの「マンデー・ルール」判定 """
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0: # 月曜日の振替判定
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンド計算（レポート推奨 [cite: 27]）"""
    try:
        df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
        if len(df) < 20: return None, None, None
        sma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        return df['Close'].iloc[-1], sma.iloc[-1] + (2 * std.iloc[-1]), sma.iloc[-1] - (2 * std.iloc[-1])
    except:
        return None, None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    price, bb_upper, bb_lower = get_technicals()
    
    msg = ""
    status = "待機中"

    # --- 判定開始 ---
    if FORCE_TEST_MODE:
        msg = "🧪 【接続テスト】全ルールを無視して送信中（成功です！）"
        status = "テスト成功"
    
    elif is_gotobi(now):
        # レポートに基づく時間別フェーズ [cite: 19, 20, 21]
        if "07:00" <= current_time < "08:00":
            if price <= bb_lower:
                msg = "🚩【ポジショニング】絶好の押し目ロング（実需先読み） [cite: 19, 27]"
                status = "押し目買い"
        elif "09:00" <= current_time < "09:55":
            if price >= bb_upper:
                msg = "⚠️【警戒】オーバーシュートにつき飛び乗り禁止 [cite: 20, 27]"
                status = "追随回避"
            else:
                msg = "📈【加速・追随】仲値に向けたドル買い優勢 [cite: 20]"
                status = "ロング追随"
        elif "09:55" <= current_time <= "10:10":
            msg = "🚨【全決済】流動性の真空による急落を回避 "
            status = "ポジション解消"

    # 送信処理
    if msg:
        send_data(price, msg, status)
    else:
        print(f"現在は規律ある待機時間です（{current_time}）。通知は送りません。 ")

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        payload = {"embeds": [{"title": "📊 需給戦略シグナル", "description": f"{msg}\n価格: {price:.3f} 円", "color": 3066993}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "需給分析", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
