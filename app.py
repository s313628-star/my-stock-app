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
st.markdown("輸入台灣股票代號，系統將自動結合 **K線型態、均線、KD/RSI指標共振與大盤濾網** 進行全方位診斷。")

stock_id = st.text_input("👉 請輸入台灣股票代號 (例如: 2330, 5351):", placeholder="請輸入4位數字代號").strip()

if st.button("🚀 開始智慧診斷", use_container_width=True):
    if not stock_id:
        st.error("❌ 請輸入有效的股票代號！")
    else:
        with st.spinner("🔍 正在下載數據並計算指標..."):
            is_market_bullish, m_close, m_ma20 = get_market_status()
            df = None
            success_id, stock_name = "", ""
            
            for suffix in [".TW", ".TWO"]:
                try:
                    target_id = f"{stock_id}{suffix}"
                    ticker = yf.Ticker(target_id)
                    df_test = ticker.history(period="60d")
                    if df_test is not None and not df_test.empty and len(df_test) >= 20:
                        df = df_test
                        success_id = target_id
                        try:
                            info = ticker.info
                            stock_name = info.get('longName', '') or info.get('shortName', '')
                        except:
                            stock_name = f"台股 {stock_id}"
                        break
                except:
                    continue
            
            if df is None:
                st.error(f"❌ 找不到代號「{stock_id}」的股票。")
            else:
                df = df.copy()
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(-1)
                
                close_p = float(df['Close'].iloc[-1])
                df['MA5'] = df['Close'].rolling(5).mean()
                df['MA10'] = df['Close'].rolling(10).mean() # 【加入MA10】
                df['MA20'] = df['Close'].rolling(20).mean()
                ma5, ma10, ma20 = float(df['MA5'].iloc[-1]), float(df['MA10'].iloc[-1]), float(df['MA20'].iloc[-1])
                
                df = calculate_kd(df)
                df['RSI'] = calculate_rsi(df)
                k_val, d_val, rsi_val = float(df['K'].iloc[-1]), float(df['D'].iloc[-1]), float(df['RSI'].iloc[-1])

                # (原本的形態判斷邏輯全部保留...)
                # ... [這裡省略你原本那些繁雜的 if buy_signals... 邏輯] ...
                
                # 為了節省空間，你在 GitHub 貼上時請確保原本形態判斷的 code 都有留著
                # 這裡僅顯示波段佈局區塊的修改：
                
                st.subheader("🎯 波段佈局參考價位")
                st.write(f"* **極短線強勢切入點 (5日線)：** `{ma5:.2f} 元`")
                st.write(f"* **短線強勢支撐 (10日線)：** `{ma10:.2f} 元`") # 【加入顯示MA10】
                st.write(f"* **標準波段安全買點 (20日線)：** `{ma20:.2f} 元`")
                # ... (後續風報比邏輯保持不變) ...
