import os
import requests
from datetime import datetime, timedelta, timezone
import yfinance as yf

# GitHubの「金庫(Secrets)」から情報を受け取る設定
# 名前が一文字でも違うと「空」になるので注意してください
GAS_URL = os.getenv("GAS_URL")
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL")

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # 【テスト用】もし今日(15日)以外でも動かしたい場合は 下の2行の先頭に # を入れてください
    if now.day % 5 != 0:
        print(f"今日は{now.day}日。ゴトー日ではないため終了します。")
        return

    # ドル円の最新レート取得
    try:
        ticker = yf.Ticker("USDJPY=X")
        price = ticker.history(period="1d")['Close'].iloc[-1]
        price = round(price, 3)
    except:
        price = 0

    # --- 1. Discord への通知 ---
    if DISCORD_URL:
        embed = {
            "title": "🚀 ゴトー日・仲値トレード通知",
            "description": f"本日 {now.month}/{now.day} の実需シグナルです。",
            "color": 3066993,
            "fields": [
                {"name": "📈 戦略", "value": "09:00 **ロング** ➔ 09:50 **全決済**"},
                {"name": "📊 現在レート", "value": f"**{price} 円**", "inline": True}
            ]
        }
        requests.post(DISCORD_URL, json={"embeds": [embed]})
    else:
        print("警告: DISCORD_WEBHOOK_URL が空です")

    # --- 2. スプレッドシート(GAS) への記録 ---
    if GAS_URL:
        data = {
            "date": now.strftime("%Y/%m/%d"),
            "strategy": "ゴトー日ロング",
            "price": price
        }
        try:
            res = requests.post(GAS_URL, json=data)
            print(f"GAS記録結果: {res.text}")
        except Exception as e:
            print(f"GAS送信エラー: {e}")
    else:
        print("エラー: GAS_URL が空です。GitHubのSecretsを確認してください。")

if __name__ == "__main__":
    run_strategy()
