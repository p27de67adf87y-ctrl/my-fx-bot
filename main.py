import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

# ==========================================
# 設定エリア
FORCE_TEST_MODE = False  # テスト時のみ True
# ==========================================

def get_demand_insight(dt):
    """需給判定ロジック"""
    day, weekday = dt.day, dt.weekday()
    if weekday == 0:
        sun, sat = dt - timedelta(days=1), dt - timedelta(days=2)
        if sun.day % 5 == 0 or sat.day % 5 == 0:
            return "🔥【特強気】週末分が凝縮（マンデー・ルール適用）"
    if day == 5: return "🐂【強気】輸入企業ドル買い突出"
    if day == 30: return "🐻【警戒】輸出企業ドル売り強まる"
    return "⚖️【中立】通常のゴト日実需"

def is_gotobi(dt):
    """ゴトー日判定（マンデー・ルール含む）"""
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
    
    # --- 1. ゴトー日以外は即終了（通常日の生存確認を廃止） ---
    if not is_gotobi(now) and not FORCE_TEST_MODE:
        return 

    price, bb_upper, bb_lower = get_technicals()
    if price is None: return

    insight = get_demand_insight(now)
    msg, status = "", ""

    # --- 2. ゴトー日の配信ロジック（条件不一致でも配信） ---
    
    # 08:00台：ゴトー日の状況報告（必ず配信）
    if "08:00" <= current_time <= "08:30":
        msg = f"📅 【ゴト日・朝の報告】\n状況: {insight}\n現在値: {price:.3f}円\n※本日はゴト日のため監視を強化します。"
        status = "ゴト日監視開始"

    # 07:00台：ポジショニング判定
    elif "07:00" <= current_time < "08:00":
        if price <= bb_lower:
            msg = f"{insight}\n🚩【ポジショニング】条件合致：押し目買い好機"
            status = "条件合致・ロング"
        else:
            # 条件に合わない場合も配信
            msg = f"{insight}\n⚖️【待機】ポジショニング：価格が高いため見送り\n(現在値がBB-2σより上にあります)"
            status = "条件不一致・見送り"

    # 09:00台：加速フェーズ判定
    elif "09:00" <= current_time < "09:50":
        if price >= bb_upper:
            msg = f"{insight}\n⚠️【回避】追随：高値警戒圏のため見送り"
            status = "高値警戒・見送り"
        else:
            msg = f"{insight}\n📈【加速】仲値公示へ向けた買いモメンタム継続"
            status = "ロング追随"

    # 09:50：決済規律（必ず配信）
    elif "09:50" <= current_time <= "10:10":
        msg = "🚨【全決済】9:55公示前の撤退規律（流動性の真空を回避）"
        status = "ポジション解消"

    if msg: send_data(price, msg, status)

def send_data(price, msg, status):
    gas_url = os.getenv("GAS_URL")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        payload = {"embeds": [{"title": "📊 需給戦略レポート (ゴト日専用)", "description": f"{msg}\n**Price:** {price:.3f}", "color": 16711680 if "🚩" in msg else 3066993}]}
        requests.post(discord_url, json=payload)
    if gas_url:
        data = {"date": datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M"), "strategy": "ゴト日分析", "price": price, "status": status}
        requests.post(gas_url, json=data)

if __name__ == "__main__":
    run_strategy()
