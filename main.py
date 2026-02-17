import os
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = True  # テスト時はTrue、本番はFalse
# ==========================================

def get_kobayashi_sentiment():
    """JFX公式サイトからインサイトを安全に取得"""
    # 候補となるURLを複数設定（404回避のため）
    urls = [
        "https://www.jfx.co.jp/category/market/",              # 一覧ページ（推奨）
        "https://www.jfx.co.jp/category/market/market_shot/"  # 個別カテゴリ
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    last_error = ""
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # 記事タイトルやリストを取得（サイト構造に合わせ柔軟に検索）
                # 記事一覧の中から最初の項目を取得
                latest_post = soup.select_one('.market_shot_list li, .post_item, article') 
                
                if latest_post:
                    text = latest_post.text
                    if "買い" in text or "押し目" in text:
                        return 1.2, "🐂【社長インサイト】強気：買い方針"
                    elif "売り" in text or "戻り" in text:
                        return 0.8, "🐻【社長インサイト】弱気：売り方針"
                    return 1.0, "⚖️【社長インサイト】中立：様子見"
            
            last_error = f"{res.status_code} {res.reason} at {url}"
        except Exception as e:
            last_error = str(e)
            continue

    # すべてのURLで失敗した場合
    return None, f"🚨【要メンテナンス】URLエラー\n原因: {last_error}\n※JFXのサイト構成が変わった可能性があります。"

def get_demand_insight(dt):
    day, weekday = dt.day, dt.weekday()
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール）"
    if day == 5: return "🐂【強気】輸入企業ドル買い突出"
    if day == 30: return "🐻【警戒】輸出企業ドル売り強まる"
    return "⚖️【中立】通常のゴト日実需"

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
    
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_upper, bb_lower = get_technicals()
    if price is None: return

    sentiment_score, sentiment_msg = get_kobayashi_sentiment()
    demand_insight = get_demand_insight(now)
    msg, status = "", ""

    # テストモード時は即座に配信
    if FORCE_TEST_MODE:
        msg = f"🧪【テスト配信】\n需給: {demand_insight}\n{sentiment_msg}\n現在値: {price:.3f}円"
        status = "テスト実行"
    # 通常のゴトー日タイムライン
    elif "08:00" <= current_time <= "08:30":
        msg = f"📅 【ゴト日監視レポート】\n需給: {demand_insight}\n{sentiment_msg}\n現在値: {price:.3f}円"
        status = "監視開始"
    elif "09:50" <= current_time <= "10:10":
        msg = "🚨【全決済】9:55公示直前の撤退規律"
        status = "ポジション解消"

    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        color = 16711680 if "🚨" in msg or "🧪" in msg else 3066993
        payload = {"embeds": [{"title": "📊 実需・社長インサイト戦略", "description": msg, "color": color}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "インサイト連携", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
