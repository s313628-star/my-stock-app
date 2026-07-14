import streamlit as st
import pandas as pd
import yfinance as yf
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="台股個股形態智慧診斷系統", page_icon="📊", layout="centered")

# --- 核心運算函數 ---
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
        if not market.empty:
            if isinstance(market.columns, pd.MultiIndex): market.columns = market.columns.get_level_values(-1)
            ma20 = market['Close'].rolling(20).mean()
            return (float(market['Close'].iloc[-1]) >= float(ma20.iloc[-1])), float(market['Close'].iloc[-1]), float(ma20.iloc[-1])
    except: pass
    return True, 0.0, 0.0

# --- 主程式 ---
st.title("📊 台股個股形態智慧診斷系統")
stock_id = st.text_input("👉 請輸入台灣股票代號 (例如: 2330, 5351):", placeholder="請輸入4位數字代號").strip()

if st.button("🚀 開始智慧診斷", use_container_width=True):
    if not stock_id:
        st.error("❌ 請輸入有效的股票代號！")
    else:
        with st.spinner("🔍 正在下載數據並深度分析..."):
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
                        break
                except: continue
            
            if df is None:
                st.error("❌ 找不到此股票或數據不足。")
            else:
                # 數據處理
                df = df.dropna()
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA10'] = df['Close'].rolling(10).mean()
                df['MA20'] = df['Close'].rolling(20).mean()
                df = calculate_kd(df)
                df['RSI'] = calculate_rsi(df)

                def get_val(col, idx=-1): return float(df[col].iloc[idx])
                
                c, o = get_val('Close'), get_val('Open')
                p_c, p_o = get_val('Close', -2), get_val('Open', -2)
                p2_c, p2_o = get_val('Close', -3), get_val('Open', -3)
                ma5, ma10, ma20 = get_val('MA5'), get_val('MA10'), get_val('MA20')
                k, d, rsi = get_val('K'), get_val('D'), get_val('RSI')
                
                # --- 形態判斷 ---
                body, abs_body = c - o, abs(c - o)
                p_body = p_c - p_o
                total_range = get_val('High') - get_val('Low')
                
                buy_signals, sell_signals = [], []
                if abs_body <= (total_range * 0.1): buy_signals.append("十字星（多空平局，趨勢可能變天）")
                if p_body < 0 and body > 0 and c > p_o and o < p_c: buy_signals.append("看漲吞沒（強烈反轉訊號）")
                if p_body > 0 and body < 0 and c < p_o and o > p_c: sell_signals.append("看跌吞沒（空頭反撲）")
                
                # --- 顯示報告 ---
                st.success(f"### 🎯 診斷標的：{stock_name}")
                col1, col2, col3 = st.columns(3)
                col1.metric("收盤價", f"{c:.2f}")
                col2.metric("RSI", f"{rsi:.1f}")
                col3.metric("K/D", f"{k:.1f}/{d:.1f}")
                
                st.subheader("💡 系統策略建議")
                if buy_signals:
                    for sig in buy_signals: st.write(f"✅ {sig}")
                    st.success("🔥 建議：偏多操作，留意進場點")
                elif sell_signals:
                    for sig in sell_signals: st.write(f"❌ {sig}")
                    st.error("🚨 建議：保守觀望或減碼")
                else:
                    st.info("⏳ 目前無明顯轉折形態，建議以均線趨勢為主。")

                st.divider()
                st.subheader("🎯 風報比與目標價")
                lowest_60d = float(df['Low'].min())
                stop_loss = ma20 * 0.95
                potential_risk = c - stop_loss
                st.write(f"🛡️ **停損參考：** {stop_loss:.2f} 元")
                st.write(f"⚠️ **勝算評估：** 根據月線與前波低點進行風險控管。")
                st.caption("📢 聲明：本工具僅供參考，投資請審慎決策。")
