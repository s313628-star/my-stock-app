import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="台股個股形態智慧診斷系統", page_icon="📊", layout="centered")

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calculate_kd(df, period=9):
    low_min = df['Low'].rolling(window=period).min()
    high_max = df['High'].rolling(window=period).max()
    rsv = ((df['Close'] - low_min) / (high_max - low_min + 1e-9)) * 100
    k, d = [50.0] * len(df), [50.0] * len(df)
    for i in range(1, len(df)):
        current_rsv = rsv.iloc[i] if not pd.isna(rsv.iloc[i]) else 50.0
        k[i] = (2/3) * k[i-1] + (1/3) * current_rsv
        d[i] = (2/3) * d[i-1] + (1/3) * k[i]
    df['K'], df['D'] = k, d
    return df

def get_market_status():
    try:
        market = yf.download("^TWII", period="40d", progress=False)
        if market is not None and not market.empty:
            if isinstance(market.columns, pd.MultiIndex):
                market.columns = market.columns.get_level_values(-1)
            market['MA20'] = market['Close'].rolling(20).mean()
            m_close = float(market['Close'].iloc[-1])
            m_ma20 = float(market['MA20'].iloc[-1])
            return (m_close >= m_ma20), m_close, m_ma20
    except:
        pass
    return True, 0.0, 0.0

st.title("📊 台股個股形態智慧診斷系統")
stock_id = st.text_input("👉 請輸入台灣股票代號:", placeholder="2330").strip()

if st.button("🚀 開始智慧診斷", use_container_width=True):
    if not stock_id:
        st.error("❌ 請輸入代號")
    else:
        with st.spinner("🔍 運算中..."):
            is_market_bullish, m_close, m_ma20 = get_market_status()
            df = None
            success_id, stock_name = "", f"台股 {stock_id}"
            
            for suffix in [".TW", ".TWO"]:
                try:
                    ticker = yf.Ticker(f"{stock_id}{suffix}")
                    df_test = ticker.history(period="60d")
                    if len(df_test) >= 20:
                        df = df_test
                        success_id = f"{stock_id}{suffix}"
                        try:
                            info = ticker.info
                            stock_name = info.get('longName', '') or info.get('shortName', '')
                        except: pass
                        break
                except: continue
            
            if df is None:
                st.error("❌ 找不到資料。")
            else:
                df = df.dropna()
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA10'] = df['Close'].rolling(10).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df = calculate_kd(df)
                df['RSI'] = calculate_rsi(df)

                def get_v(col, i=-1): return float(df[col].iloc[i])
                
                c, o, h, l = get_v('Close'), get_v('Open'), get_v('High'), get_v('Low')
                p_c, p_o, p_h, p_l = get_v('Close', -2), get_v('Open', -2), get_v('High', -2), get_v('Low', -2)
                p2_c, p2_o = get_v('Close', -3), get_v('Open', -3)
                ma5, ma10, ma20 = get_v('MA5'), get_v('MA10'), get_v('MA20')
                k, d, rsi = get_v('K'), get_v('D'), get_v('RSI')
                
                body, p_body, p2_body = c - o, p_c - p_o, p2_c - p2_o
                abs_body, abs_p_body = abs(body), abs(p_body)
                total_range = h - l if (h - l) > 0 else 1
                lower_shadow, upper_shadow = min(o, c) - l, h - max(o, c)
                
                buy_signals, sell_signals = [], []
                if abs_body <= (total_range * 0.1): buy_signals.append("十字星（多空平局，趨勢可能變天）")
                if lower_shadow > (abs_body * 2) and upper_shadow < (abs_body * 0.5) and c < ma20: buy_signals.append("錘子線（長下影線強烈支撐，可能觸底）")
                if upper_shadow > (abs_body * 2) and lower_shadow < (abs_body * 0.5) and c > ma20: sell_signals.append("射擊之星（長上影線見頂預警）")
                if p_body < 0 and body > 0 and c > p_o and o < p_c: buy_signals.append("看漲吞沒（強烈反轉訊號）")
                if p_body > 0 and body < 0 and c < p_o and o > p_c: sell_signals.append("看跌吞沒（空頭反撲）")
                if p2_body < 0 and abs_p_body < abs(p2_body)*0.3 and body > 0 and c > (p2_o + p2_c)/2: buy_signals.append("晨星（經典底部看漲）")
                
                st.success(f"### 🎯 診斷標的：{stock_name}")
                col1, col2, col3 = st.columns(3)
                col1.metric("當前收盤", f"{c:.2f}")
                col2.metric("RSI", f"{rsi:.1f}")
                col3.metric("K/D", f"{k:.1f}/{d:.1f}")

                # --- 新增：明日走勢智慧預測 ---
                score = 0
                if body > 0: # 紅K
                    if lower_shadow > abs_body: score += 2 # 先跌後漲
                    elif upper_shadow < abs_body * 0.5: score += 3 # 漲勢強
                    else: score += 1 # 空方減弱
                elif body < 0: score -= 2 # 綠K
                
                if c > ma20: score += 2
                if ma5 > ma20: score += 1
                if k > d: score += 1
                if rsi > 50: score += 1
                if is_market_bullish: score += 2
                else: score -= 2

                st.subheader("🔮 明日走勢預測 (綜合模型)")
                if score >= 6: st.success(f"📈 **強勢多頭 (得分 {score})：** 明日看漲機率較高。")
                elif score >= 2: st.info(f"⚖️ **盤整偏多 (得分 {score})：** 多方力道尚可，注意支撐。")
                elif score >= -2: st.warning(f"⚠️ **多空不明 (得分 {score})：** 方向不明，建議觀望。")
                else: st.error(f"📉 **弱勢空頭 (得分 {score})：** 明日看跌機率較高。")
                # ---------------------------
                
                st.subheader("💡 系統策略建議")
                if buy_signals:
                    for s in buy_signals: st.write(f"✅ {s}")
                if sell_signals:
                    for s in sell_signals: st.write(f"❌ {s}")
                
                st.divider()
                st.subheader("🛡️ 停損與風報比")
                stop_loss = ma20 * 0.95 if c > ma20 else get_v('Low', -40) * 0.95
                st.write(f"* **停損參考價：** `{stop_loss:.2f} 元`")
                st.caption("📢 聲明：以上僅為技術模型推算，不構成投資建議。")
