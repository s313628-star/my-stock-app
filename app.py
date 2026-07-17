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
        with st.spinner("🔍 正在連線市場下載數據並計算指標，請稍候..."):
            is_market_bullish, m_close, m_ma20 = get_market_status()
            df = None
            success_id, stock_name, industry = "", "", "未知產業"
            
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
                            industry = info.get('industry', '未知產業')
                        except:
                            stock_name = f"台股 {stock_id}"
                        break
                except:
                    continue
            
            if df is None:
                st.error(f"❌ 找不到代號「{stock_id}」的股票。請確認代號是否正確、該股是否已上市櫃。")
            else:
                try:
                    df = df.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(-1)
                    
                    df = df.dropna()
                    df['MA5'] = df['Close'].rolling(5).mean()
                    df['MA10'] = df['Close'].rolling(10).mean()
                    df['MA20'] = df['Close'].rolling(20).mean()
                    
                    df = calculate_kd(df)
                    df['RSI'] = calculate_rsi(df)
                    
                    def safe_float(val):
                        return float(val) if pd.notna(val) else 0.0

                    close_p = safe_float(df['Close'].iloc[-1])
                    open_p = safe_float(df['Open'].iloc[-1])
                    high_p = safe_float(df['High'].iloc[-1])
                    low_p = safe_float(df['Low'].iloc[-1])
                    volume = safe_float(df['Volume'].iloc[-1])
                    
                    p_close, p_open = safe_float(df['Close'].iloc[-2]), safe_float(df['Open'].iloc[-2])
                    p2_close, p2_open = safe_float(df['Close'].iloc[-3]), safe_float(df['Open'].iloc[-3])
                    p_high, p_low = safe_float(df['High'].iloc[-2]), safe_float(df['Low'].iloc[-2])
                    
                    ma5, ma10, ma20 = safe_float(df['MA5'].iloc[-1]), safe_float(df['MA10'].iloc[-1]), safe_float(df['MA20'].iloc[-1])
                    k_val, d_val, rsi_val = safe_float(df['K'].iloc[-1]), safe_float(df['D'].iloc[-1]), safe_float(df['RSI'].iloc[-1])
                except Exception as e:
                    st.error(f"❌ 數據格式解析異常: {e}")
                    st.stop()

                body = close_p - open_p
                abs_body = abs(body)
                p_body = p_close - p_open
                abs_p_body = abs(p_body)
                p2_body = p2_close - p2_open
                lower_shadow = min(open_p, close_p) - low_p
                upper_shadow = high_p - max(open_p, close_p)
                total_range = high_p - low_p if (high_p - low_p) > 0 else 1
                
                avg_volume_5d = float(df['Volume'].iloc[-6:-1].mean())
                is_volume_breakout = volume > (avg_volume_5d * 1.5) if avg_volume_5d > 0 else False
                vol_ratio = volume / avg_volume_5d if avg_volume_5d > 0 else 1.0

                buy_signals, sell_signals = [], []
                
                if abs_body <= (total_range * 0.1): buy_signals.append("十字星（多空平局，趨勢可能變天）")
                if lower_shadow > (abs_body * 2) and upper_shadow < (abs_body * 0.5) and close_p < ma20: buy_signals.append("錘子線（長下影線強烈支撐，可能觸底）")
                if upper_shadow > (abs_body * 2) and lower_shadow < (abs_body * 0.5) and close_p > ma20: sell_signals.append("射擊之星（長上影線見頂預警）")
                if p_body < 0 and body > 0 and close_p > p_open and open_p < p_close: buy_signals.append("看漲吞沒（強烈反轉訊號）")
                if p_body > 0 and body < 0 and close_p < p_open and open_p > p_close: sell_signals.append("看跌吞沒（空頭反撲）")
                if p_body < 0 and body > 0 and open_p < p_low and close_p > (p_open + p_close)/2: buy_signals.append("穿刺線（多頭強力反擊）")
                if p_body > 0 and body < 0 and open_p > p_high and close_p < (p_open + p_close)/2: sell_signals.append("烏雲蓋頂（趨勢要拐頭）")
                if p2_body < 0 and abs_p_body < abs(p2_body)*0.3 and body > 0 and close_p > (p2_open + p2_c)/2: buy_signals.append("晨星（經典底部看漲）")
                if p2_body > 0 and abs_p_body < abs(p2_body)*0.3 and body < 0 and close_p < (p2_open + p2_close)/2: sell_signals.append("黃昏星（經典頂部看跌）")
                
                recent_max = df['Close'].tail(40).max()
                if close_p >= (recent_max * 0.96) and p_close < (recent_max * 0.95): buy_signals.append("W 底 / 杯柄形態突破（上漲續力）")

                highest_60d, lowest_60d = float(df['High'].max()), float(df['Low'].min())
                wave_range = highest_60d - lowest_60d if (highest_60d - lowest_60d) > 0 else 1
                target_1382 = lowest_60d + (wave_range * 1.382)
                target_1618 = lowest_60d + (wave_range * 1.618)
                stop_loss = ma20 * 0.95 if close_p > ma20 else lowest_60d * 0.95

                st.success(f"### 🎯 診斷標的：{stock_name} ({success_id})")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("當前收盤價", f"{close_p:.2f} 元", f"{'🔴 紅K' if body >= 0 else '🟢 綠K'}")
                col2.metric("今日成交量", f"{volume/1000:,.0f} 張", f"均量 {vol_ratio:.1f} 倍")
                col3.metric("技術指標", f"RSI: {rsi_val:.1f}", f"K/D: {k_val:.1f}/{d_val:.1f}")
                
                # --- [新增] 老王分析師技術邏輯 ---
                st.subheader("🎙️ 老王邏輯技術觀察")
                wa_score = 0
                if close_p > ma20: wa_score += 2 # 站上月線
                if k_val > d_val: wa_score += 1 # KD黃金交叉
                if vol_ratio > 1.2: wa_score += 1 # 量能增溫
                
                if wa_score >= 3: st.success("老王觀點：『目前處於多頭攻擊態勢，月線不破，偏多操作。』")
                elif wa_score >= 1: st.warning("老王觀點：『多空震盪，嚴守月線支撐，破線即出場。』")
                else: st.error("老王觀點：『空頭排列，量縮下跌，場外觀望才是最高指導原則。』")
                # ----------------------------

                if not is_market_bullish:
                    st.warning(f"⚠️ **大盤結構偏空**：加權指數目前收在月線之下。即使個股有買點，也請嚴格控制資金部位！")
                else:
                    st.info(f"🟢 **大盤環境安全**：加權指數處於月線之上，適合多頭操作。")
                
                st.divider()
                st.subheader("💡 系統策略建議")
                is_bullish = False
                if buy_signals and not sell_signals:
                    is_bullish = True
                    if rsi_val > 80 or k_val > 80:
                        st.warning("⚠️ **形態看漲，但「指標過熱」，請勿在此追高！**")
                        for sig in buy_signals: st.write(f"* ✅ {sig}")
                    elif rsi_val < 35 or k_val < 25:
                        st.balloons()
                        st.success("🔥🔥 **☆☆☆☆☆ 五星級底部黃金共振買點！** 🔥🔥")
                        for sig in buy_signals: st.write(f"* ✅ {sig}")
                    else:
                        st.success("🔥 **建議：可以分批進場 / 偏多操作**")
                        for sig in buy_signals: st.write(f"* ✅ {sig}")
                        if is_volume_breakout: st.write(f"👉 爆量確認：今日成交量放大至 5 日均量的 {vol_ratio:.1f} 倍，訊號真實！")
                elif sell_signals and not buy_signals:
                    st.error("🚨 **建議：分批賣出 / 出場觀望**")
                    for sig in sell_signals: st.write(f"* ❌ {sig}")
                elif buy_signals and sell_signals:
                    st.info("🔄 **多空交戰中**：買賣形態同時並存，建議暫時觀望。")
                else:
                    if close_p > ma5 and ma5 > ma20:
                        st.success("📈 **多頭排列（趨勢向上）**：持股可續抱。")
                        is_bullish = True
                    elif close_p < ma5 and ma5 < ma20:
                        st.error("📉 **空頭排列（持續下探）**：不建議進場，持股請考慮減碼。")
                    else:
                        st.info("⏳ **橫盤整理中**：目前無明顯趨勢，建議先不急著進出場。")

                st.divider()
                st.subheader("🎯 波段佈局參考價位")
                if is_bullish or close_p >= ma20:
                    st.write(f"* **極短線強勢切入點 (5日線)：** `{ma5:.2f} 元`")
                    st.write(f"* **短線強勢支撐 (10日線)：** `{ma10:.2f} 元`")
                    st.write(f"* **標準波段安全買點 (20日線)：** `{ma20:.2f} 元`")
                else:
                    st.write(f"* **偏保守安全買點 (60天低點)：** `{lowest_60d:.2f} 元`")
                st.error(f"🛡️ **終極防守退場價 (停損點)：** `{stop_loss:.2f} 元`")

                st.divider()
                st.subheader("⚖️ 風報比交易評估")
                potential_profit = target_1382 - close_p
                potential_risk = close_p - stop_loss
                if potential_risk <= 0: potential_risk = 0.01
                rr_ratio = potential_profit / potential_risk
                st.write(f"* **預估潛在利潤：** `+{potential_profit:.2f} 元` | **承擔潛在風險：** `-{potential_risk:.2f} 元`")
                st.write(f"* **當前交易風報比：** `{rr_ratio:.2f}`")

                if is_bullish and rr_ratio < 1.5:
                    st.warning("💡 **策略提醒：形態看漲但風報比不佳**，建議掛單在均線附近再切入。")
                
                if is_market_bullish:
                    if rr_ratio >= 2.0: st.success("🟢 **高勝算交易：風報比 > 2.0**")
                    elif rr_ratio >= 1.5: st.warning("🟡 **中等交易：風報比 1.5 ~ 2.0**")
                    elif rr_ratio < 1.5 and not is_bullish: st.error("❌ **不合算交易：風險過高**")

                st.divider()
                st.subheader("🔮 未來上漲目標預估")
                st.write(f"* **近 60 天波段大魔王：** `{highest_60d:.2f} 元`")
                st.write(f"* **黃金波段第一目標價：** `{target_1382:.2f} 元`")
                st.write(f"* **黃金波段第二目標價：** `{target_1618:.2f} 元`")
                st.caption("⚠️ 聲明：本網頁僅供技術分析討論，不構成投資與買賣建議。")
