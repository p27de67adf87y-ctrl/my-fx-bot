import os
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = True  # テスト時のみ True にする
# ==========================================

def get_kobayashi_sentiment():
    """JFX公式サイトから小林社長の目線をスクレイピング"""
    url = "https://www.jfx.co.jp/category/market/market_shot/"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # 最新の記事リストから文言を抽出
        latest_post = soup.select_one('.market_shot_list li')
        if not latest_post:
            raise ValueError("サイト構造が変更された可能性があります（記事が見つかりません）。")
            
        text = latest_post.text
        if "買い" in text or "押し目" in text:
            return 1.2, "🐂【社長インサイト】強気：買い方針"
        elif "売り" in text or "戻り" in text:
            return 0.8, "🐻【社長インサイト】弱気：売り方針"
        return 1.0, "⚖️【社長インサイト】中立：様子見"
        
    except Exception as e:
        # スクレイピング失敗時のアラート用メッセージ
        error_alert = f"🚨【要メンテナンス】小林社長のインサイト取得に失敗\n理由: {str(e)}"
        return None, error_alert

def get_demand_insight(dt):
    """日付ベースの需給判定（マンデー・ルール対応）"""
    day, weekday = dt.day, dt.weekday()
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮された需要（マンデー・ルール）"
    if day == 5: return "🐂【強気】輸入企業のドル買い需要突出"
    if day == 30: return "🐻【警戒】輸出企業のドル売り強まる"
    return "⚖️【中立】通常のゴト日実需"

def is_gotobi(dt):
    """ゴトー日判定ロジック"""
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンド計算"""
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
    
    # 1. ゴトー日以外は即終了（通常日は沈黙）
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_upper, bb_lower = get_technicals()
    if price is None: return

    # 小林社長のセンチメントを取得
    sentiment_score, sentiment_msg = get_kobayashi_sentiment()
    
    # スクレイピング失敗時は警告を飛ばし、中立(1.0)として続行
    is_maintenance = False
    if sentiment_score is None:
        is_maintenance = True
        sentiment_score = 1.0

    demand_insight = get_demand_insight(now)
    msg, status = "", ""

    # 2. ゴトー日のタイムライン判定
    
    # 朝の総括 (08:00 - 08:30)
    if "08:00" <= current_time <= "08:30":
        msg = f"📅 【ゴト日監視レポート】\n需給: {demand_insight}\n{sentiment_msg}\n現在値: {price:.3f}円"
        status = "監視開始"

    # フェーズ1: ポジショニング (07:00台)
    elif "07:00" <= current_time < "08:00":
        # 社長が強気ならエントリー条件を少し緩和
        threshold = bb_lower * (1.0005 if sentiment_score > 1.0 else 1.0)
        if price <= threshold:
            msg = f"{demand_insight}\n{sentiment_msg}\n🚩【条件合致】押し目買い実行"
            status = "ロング実行"
        else:
            msg = f"{demand_insight}\n{sentiment_msg}\n⚖️【待機】価格が高いため見送り"
            status = "条件不一致"

    # フェーズ2: 加速・追随 (09:00 - 09:50)
    elif "09:00" <= current_time < "09:50":
        if price >= bb_upper:
            msg = f"⚠️【警戒】高値圏のため追随禁止\n{sentiment_msg}"
            status = "追随回避"
        else:
            msg = f"📈【加速】仲値公示へ向けた買いモメンタム\n{sentiment_msg}"
            status = "ロング追随"

    # フェーズ3: 決済 (09:50 - 10:10)
    elif "09:50" <= current_time <= "10:10":
        msg = "🚨【全決済】規律に従いポジションを解消します（9:55公示直前の撤退）"
        status = "ポジション解消"

    # スクレイピング失敗時はメッセージの先頭に警告を追加
    if is_maintenance and msg:
        msg = "⚠️【スクレイピング失敗中】\n" + msg

    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        color = 16711680 if "🚨" in msg or "⚠️" in msg else 3066993
        payload = {"embeds": [{"title": "📊 実需・社長インサイト戦略", "description": f"{msg}\n**Price:** {price:.3f}", "color": color}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "インサイト連携", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
