import os
import requests
from datetime import datetime, timedelta, timezone
import yfinance as yf

def send_to_discord(embed):
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return
    payload = {"embeds": [embed]}
    requests.post(url, json=payload)

def get_market_data():
    """ドル円の現在値とボラティリティを取得"""
    try:
        ticker = yf.Ticker("USDJPY=X")
        df = ticker.history(period="2d")
        current_price = df['Close'].iloc[-1]
        
        # 1日の値動き幅（高値 - 安値）の平均を計算（目安）
        daily_range = df['High'].iloc[-1] - df['Low'].iloc[-1]
        return current_price, daily_range
    except:
        return None, None

def run_strategy():
    # 日本時間(JST)を設定
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # ゴトー日判定（5, 10, 15, 20, 25, 30日）
    if now.day % 5 != 0:
        print(f"本日({now.day}日)は対象外です。")
        return

    price, volatility = get_market_data()
    
    # Discordに送るカード（Embed）の設定
    embed = {
        "title": "🚀 【実需】ゴトー日・仲値トレード発動",
        "description": f"本日 **{now.month}/{now.day}** は実需のドル需要が高まるゴトー日です。",
        "color": 5814783, # 青色
        "fields": [
            {
                "name": "📈 戦略",
                "value": "09:00 **ロング（買い）**\n09:50 **全決済（利確・損切）**",
                "inline": False
            },
            {
                "name": "📊 現在レート",
                "value": f"**{price:.3f} 円**" if price else "取得失敗",
                "inline": True
            },
            {
                "name": "⚡ ボラティリティ",
                "value": f"約 {volatility*100:.1f} pips" if volatility else "取得失敗",
                "inline": True
            },
            {
                "name": "💡 アドバイス",
                "value": "9:50の仲値公示に向けて上昇しやすい傾向にあります。9:50を過ぎると急落のリスクがあるため、時間は厳守してください。",
                "inline": False
            }
        ],
        "footer": {
            "text": "FX Strategy Bot | 勝率 83.3% ロジック"
        },
        "timestamp": now.isoformat()
    }

    send_to_discord(embed)

if __name__ == "__main__":
    run_strategy()
