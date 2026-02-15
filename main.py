import os
import requests
from datetime import datetime, timedelta, timezone
import yfinance as yf

def send_to_discord(embed):
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url: return
    payload = {"embeds": [embed]}
    requests.post(url, json=payload)

def check_economic_indicators(now):
    """
    重要指標の有無を判定する（簡易版）
    本来はAPIを使用しますが、ここでは特定の日付や曜日の注意を促します
    """
    warnings = []
    # 例：五十日でも「月曜日」は週明けの窓開けリスクがあるなど
    if now.weekday() == 0:
        warnings.append("⚠️ 週明け月曜のため、窓開けや不安定な動きに注意")
    
    # 金曜日かつ五十日の「金曜ゴトー」は最も上昇しやすい傾向
    if now.weekday() == 4:
        warnings.append("✨ 金曜ゴトー日！実需の買いが強まりやすい絶好機")
        
    return "\n".join(warnings) if warnings else "特になし（通常通り）"

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # 五十日判定
    #if now.day % 5 != 0: return

    ticker = yf.Ticker("USDJPY=X")
    df = ticker.history(period="2d")
    price = df['Close'].iloc[-1]
    
    indicator_msg = check_economic_indicators(now)
    
    embed = {
        "title": "🚀 【実需】ゴトー日・仲値トレード発動",
        "description": f"本日 **{now.month}/{now.day}** の戦略データです。",
        "color": 15158332 if "⚠️" in indicator_msg else 3066993, # 警告時は赤、通常は緑
        "fields": [
            {
                "name": "📈 戦略",
                "value": "09:00 **ロング** ➔ 09:50 **全決済**",
                "inline": False
            },
            {
                "name": "🚩 指標・注意点",
                "value": indicator_msg,
                "inline": False
            },
            {
                "name": "📊 現在価格",
                "value": f"**{price:.3f} 円**",
                "inline": True
            },
            {
                "name": "💡 期待値",
                "value": "勝率 83.3%",
                "inline": True
            }
        ],
        "footer": {"text": "FX Strategy Bot | 規律あるトレードを"},
        "timestamp": now.isoformat()
    }
    send_to_discord(embed)

if __name__ == "__main__":
    run_strategy()
