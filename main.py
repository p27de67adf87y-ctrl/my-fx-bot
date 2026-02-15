import os
import requests
from datetime import datetime, timedelta, timezone
import yfinance as yf

# 【最重要】GitHubの金庫からURLを受け取る設定
GAS_URL = os.getenv("GAS_URL")
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_to_discord(price, indicator_msg):
    """Discordに豪華なカードを送る"""
    if not DISCORD_URL: return
    
    now = datetime.now(timezone(timedelta(hours=9)))
    embed = {
        "title": "🚀 【実需】ゴトー日・仲値トレード",
        "description": f"本日 {now.month}/{now.day} の戦略データです。",
        "color": 3066993,
        "fields": [
            {"name": "📈 戦略", "value": "09:00 **ロング** ➔ 09:50 **全決済**"},
            {"name": "📊 現在価格", "value": f"**{price:.3f} 円**", "inline": True},
            {"name": "🚩 指標", "value": indicator_msg, "inline": False}
        ]
    }
    requests.post(DISCORD_URL, json={"embeds": [embed]})

def log_to_sheets(price):
    """スプレッドシート(GAS)に記録を送る"""
    if not GAS_URL:
        print("エラー: GAS_URLが設定されていません")
        return
        
    now = datetime.now(timezone(timedelta(hours=9)))
    data = {
        "date": now.strftime("%Y/%m/%d"),
        "strategy": "ゴトー日ロング",
        "price": round(price, 3)
    }
    
    try:
        res = requests.post(GAS_URL, json=data)
        print(f"GAS記録結果: {res.text}")
    except Exception as e:
        print(f"GAS送信失敗: {e}")

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # テストのために判定を一時的にコメントアウトしたい場合は、下の行の先頭に # を入れてください
    if now.day % 5 != 0: 
        print(f"今日は{now.day}日のため、実行をスキップしました。")
        return

    # ドル円レート取得
    try:
        ticker = yf.Ticker("USDJPY=X")
        price = ticker.history(period="1d")['Close'].iloc[-1]
    except:
        price = 0

    # 1. Discordに送る
    send_to_discord(price, "通常通り")
    
    # 2. スプレッドシートに記録する
    log_to_sheets(price)

if __name__ == "__main__":
    run_strategy()
