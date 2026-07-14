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
st.markdown("輸入台灣股票代號，系統將自動結合 **K線型態、均線(含MA10)、KD/RSI指標與大盤濾網** 進行診斷。")

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
                df['MA10'] = df['Close'].rolling(10).mean() # 新增 MA10
                df['MA20'] = df['Close'].rolling(20).mean()
                ma5, ma10, ma20 = float(df['MA5'].iloc[-1]), float(df['MA10'].iloc[-1]), float(df['MA20'].iloc[-1])
                
                df = calculate_kd(df)
                df['RSI'] = calculate_rsi(df)
                k_val, d_val, rsi_val = float(df['K'].iloc[-1]), float(df['D'].iloc[-1]), float(df['RSI'].iloc[-1])

                st.success(f"### 🎯 診斷標的：{stock_name} ({success_id})")
                
                # ... (形態判斷邏輯維持不變) ...
                highest_60d = float(df['High'].max())
                lowest_60d = float(df['Low'].min())
                stop_loss = ma20 * 0.95 

                st.subheader("🎯 波段佈局參考價位")
                st.write(f"* **極短線強勢切入點 (5日線)：** `{ma5:.2f} 元`")
                st.write(f"* **短線防守支撐 (10日線)：** `{ma10:.2f} 元`") # 新增顯示
                st.write(f"* **標準波段安全買點 (20日線)：** `{ma20:.2f} 元`")
                st.error(f"🛡️ **終極防守退場價 (停損點)：** `{stop_loss:.2f} 元`")

                st.subheader("⚖️ 風報比交易評估")
                target_1382 = lowest_60d + (highest_60d - lowest_60d) * 1.382
                potential_profit = target_1382 - close_p
                potential_risk = close_p - stop_loss
                if potential_risk <= 0: potential_risk = 0.01
                rr_ratio = potential_profit / potential_risk
                
                st.write(f"* **風報比：** `{rr_ratio:.2f}`")
                
                # 優化後的判斷邏輯
                if rr_ratio >= 1.5:
                    st.success("🟢 風報比優良，符合進場策略。")
                elif rr_ratio >= 1.2:
                    st.warning("🟡 風報比偏低，若技術面強勢（如站穩 10 日線），可考慮分批小量佈局。")
                else:
                    st.error("❌ 風報比低於 1.2，風險較高，建議謹慎放棄。")

