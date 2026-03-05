import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = False  # テスト時のみTrueにする
# ==========================================

def get_demand_insight(dt):
    """日付から実需の強さを判定"""
    day, weekday = dt.day, dt.weekday()
    if weekday == 0: # 月曜日の場合、土日の分も考慮
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール適用日）"
    if day % 5 == 0: return "🐂【強気】ゴト日のドル買い需要"
    return "⚖️【中立】通常の実需（仲値に向けた動き）"

def is_gotobi(dt):
    """ゴトー日判定ロジック"""
    day, weekday = dt.day, dt.weekday()
    if day % 5 == 0 and weekday < 5: return True
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0: return True
    return False

def get_technicals():
    """ボリンジャーバンドの計算（期間10）"""
    try:
        # スプレッドが落ち着いたレートを取得するため5分足を使用
        df = yf.Ticker("USDJPY=X").history(period="1d", interval="5m")
        if len(df) < 10: return None, None
        sma = df['Close'].rolling(window=10).mean()
        std = df['Close'].rolling(window=10).std()
        price = df['Close'].iloc[-1]
        lower = sma.iloc[-1] - (2 * std.iloc[-1])
        return price, lower
    except: return None, None

def run_strategy():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    current_time = now.strftime("%H:%M")
    
    # ゴトー日でない、かつテストモードでない場合は終了
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_lower = get_technicals()
    if price is None: return

    insight = get_demand_insight(now)
    msg, status = "", "監視中"

    # --- 判定ロジック（遅延対策・幅を持たせた判定） ---

    if FORCE_TEST_MODE:
        msg = f"🧪【テスト配信】\n判定: {insight}\n現在値: {price:.3f}円\n※動作確認用メッセージです。"
        status = "テスト成功"

    # 1. 監視開始：07:45 〜 08:10 の間に起動した場合
    elif "07:45" <= current_time <= "08:10":
        msg = f"📅 【監視開始レポート】\n需給: {insight}\n現在値: {price:.3f}円\nスプレッド安定後の監視を開始しました。"
        status = "監視開始"
        # この時点で安値ならエントリー指示
        if price <= bb_lower:
            msg += "\n\n🚩【条件合致】現在安値圏です！\n10枚ロング ＋ 損切り(-20pips)推奨"
            status = "ロング実行"

    # 2. 押し目監視：08:11 〜 09:40 の間（条件が合った時だけ赤旗を出す）
    elif "08:11" <= current_time <= "09:40":
        if price <= bb_lower:
            msg = f"🚩【条件合致】押し目買い実行\n現在値: {price:.3f}円\n⚠️ 10枚注文 ＋ 損切り(-20pips)をセット！"
            status = "ロング実行"

    # 3. 決済：09:45 〜 11:30 の間に起動した場合
    elif "09:45" <= current_time <= "11:30":
        msg = "🚨【全決済】仲値公示後のステータス更新\n本日のトレード時間を終了しました。お疲れ様でした！"
        status = "ポジション解消"

    # メッセージがある場合のみ送信
    if msg:
        send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Discord送信
    if discord_url:
        color = 3066993 if "📅" in msg else 16711680 if "🚨" in msg or "🚩" in msg else 3447003
        payload = {"embeds": [{"title": "📊 Gotobi Bot", "description": msg, "color": color}]}
        requests.post(discord_url, json=payload)
    
    # Google Apps Script(GAS)送信
    if gas_url:
        data = {
            "date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"),
            "strategy": "実需・期間10モデル",
            "price": price,
            "status": status
        }
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
