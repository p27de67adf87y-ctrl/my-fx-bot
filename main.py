import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# --- 設定エリア ---
# テストしたい時はここを True にすると、日付や時間の判定を無視して即座に送信されます
DEBUG_MODE = False 

def is_gotobi(dt):
    """
    レポートの「マンデー・ルール」を適用 
    5, 10...の日、または土日の場合は月曜日に需要がスライドする判定
    """
    day = dt.day
    weekday = dt.weekday()  # 0:月 ... 6:日

    # 1. 当日が5の倍数かつ平日の場合
    if day % 5 == 0 and weekday < 5:
        return True
    
    # 2. 月曜日の場合、土日が5の倍数だったかチェック（需要の凝縮） 
    if weekday == 0:
        sun = dt - timedelta(days=1)
        sat = dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return True
            
    return False

def get_technicals():
    """
    ボリンジャーバンド(±2σ)を計算 
    """
    try:
        df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
        if len(df) < 20: return None, None, None
        
        # 20期間の移動平均と標準偏差
        sma = df['Close'].rolling(window=20).mean()
        std = df['Close'].rolling(window=20).std()
        
        price = df['Close'].iloc[-1]
        upper = sma.iloc[-1] + (2 * std.iloc[-1])
        lower = sma.iloc[-1] - (2 * std.iloc[-1])
        return price, upper, lower
    except Exception as e:
        print(f"価格取得エラー: {e}")
        return None, None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    
    # 1. ゴトー日判定（DEBUGモード時は無視）
    if not DEBUG_MODE and not is_gotobi(now):
        print(f"本日は実需の動きがないため待機します（{now.strftime('%Y/%m/%d')}）")
        return

    # 2. テクニカル指標の取得
    price, bb_upper, bb_lower = get_technicals()
    if price is None: return

    msg = ""
    status_for_gas = "待機中"

    # 3. タイムライン別戦略 
    if DEBUG_MODE:
        msg = "🧪 接続テスト（全条件を無視して送信中）"
        status_for_gas = "テスト実行"
    
    # フェーズ1: 07:00-08:00（ポジショニング）[cite: 19]
    elif "07:00" <= current_time < "08:00":
        if price <= bb_lower:
            msg = "🚩【絶好の押し目】実需の先読みロング検討（BB -2σ到達）"
            status_for_gas = "押し目買い好機"
    
    # フェーズ2: 09:00-09:55（加速・追随）[cite: 20]
    elif "09:00" <= current_time < "09:55":
        if price >= bb_upper:
            msg = "⚠️【警戒】オーバーシュート（飛び乗り禁止・BB +2σ超え）" [cite: 27]
            status_for_gas = "追随見送り"
        else:
            msg = "📈【加速フェーズ】仲値公示に向けたドル買い優勢" [cite: 11]
            status_for_gas = "ロング追随"

    # フェーズ3: 09:55-10:10（逆回転回避）[cite: 21]
    elif "09:55" <= current_time <= "10:10":
        msg = "🚨【全決済】流動性の真空による急落リスクを回避せよ" [cite: 23]
        status_for_gas = "ポジション解消"

    # メッセージがある場合のみ送信
    if msg:
        send_signals(price, msg, status_for_gas)
    else:
        print(f"現在時刻 {current_time}: レポートの規定時間外のため通知しません。")

def send_signals(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Discord送信
    if discord_url:
        payload = {
            "embeds": [{
                "title": "📊 需給分析に基づく判定シグナル",
                "description": f"**判定:** {msg}\n**現在値:** {price:.3f} 円",
                "color": 16776960 if "⚠️" in msg else 3066993
            }]
        }
        requests.post(discord_url, json=payload)

    # GAS(スプレッドシート)記録
    if gas_url:
        data = {
            "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
            "strategy": "レポート戦略",
            "price": price,
            "status": status
        }
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
