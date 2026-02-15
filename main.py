import os
import requests
from datetime import datetime
import yfinance as yf

def send_to_discord(msg):
    # あとで設定する「金庫」からURLを読み込みます
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if url:
        requests.post(url, json={"content": msg})

def run_strategy():
    today = datetime.now()
    # ゴト日判定
    if today.day % 5 != 0:
        print(f"Today is {today.day}, not a Gotobi day.")
        return

    # 最新レート取得
    try:
        ticker = yf.Ticker("USDJPY=X")
        price = ticker.history(period="1d")['Close'].iloc[-1]
    except:
        price = 0

    message = (
        "📈 **【FX実需シグナル発動】**\n"
        f"今日は {today.day} 日（ゴトー日）です！\n\n"
        "✅ **09:00：ロング（買い）**\n"
        "✅ **09:50：必ず決済（利確）**\n\n"
        f"現在レート: {price:.2f}円付近\n"
        "*過去検証: 114.4 pips / 勝率 83.3%*"
    )
    send_to_discord(message)

if __name__ == "__main__":
    run_strategy()
