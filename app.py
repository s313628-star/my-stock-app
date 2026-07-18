import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import warnings
import twstock


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
st.markdown("輸入代號或中文名稱，系統將自動結合 **K線型態、均線、KD/RSI指標共振與大盤濾網** 進行全方位診斷。")

# 自動抓取證交所股票清單作為對照庫
# --- [改進] 智慧搜尋引擎 (不依賴外部檔案，由 yfinance 自動搜尋) ---
user_input = st.text_input("👉 請輸入代號或中文名稱:", placeholder="請輸入代號或名稱").strip()

def get_stock_id_smart(query):
    # 如果使用者直接輸入數字，直接回傳
    if query.isdigit():
        return query
    
    # 嘗試用 twstock 進行中文名稱轉代號
    try:
        for code, info in twstock.codes.items():
            if query == info.name:
                return code
    except:
        pass
        
    return query


stock_id = get_stock_id_smart(user_input)
# -------------------------------------------------------------


if st.button("🚀 開始智慧診斷", use_container_width=True):
    if not stock_id:
        st.error("❌ 請輸入有效的股票代號！")
    else:
        with st.spinner("🔍 正在連線市場下載數據並計算指標，請稍候..."):
            is_market_bullish, m_close, m_ma20 = get_market_status()
            df = None
            success_id, stock_name, industry = "", "", "未知產業"
            
                        # 優先搜尋原始輸入 (支援名稱)，其次嘗試補上 .TW/.TWO 後綴
            search_list = [stock_id, f"{stock_id}.TW", f"{stock_id}.TWO"]
            
            for target_id in search_list:
                try:
                    ticker = yf.Ticker(target_id)
                    df_test = ticker.history(period="60d")
                    if df_test is not None and not df_test.empty and len(df_test) >= 20:
                        df = df_test
                        success_id = target_id
                        try:
                            info = ticker.info
                            stock_name = info.get('longName', '') or info.get('shortName', stock_id)
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
                if p2_body < 0 and abs_p_body < abs(p2_body)*0.3 and body > 0 and close_p > (p2_open + p2_close)/2: buy_signals.append("晨星（經典底部看漲）")
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
                
                # --- [新增] 明日趨勢統計輔助 ---
                st.subheader("🔮 明日走勢機率輔助診斷")
                strength_score = 0
                if body > 0 and upper_shadow < abs_body * 0.2 and lower_shadow < abs_body * 0.2: strength_score += 3 # 漲勢強
                elif body > 0 and lower_shadow > abs_body * 0.5: strength_score += 2 # 先跌後漲
                elif body > 0 and upper_shadow > abs_body * 0.5: strength_score += 1 # 空方減弱
                if k_val > d_val: strength_score += 1
                if is_market_bullish: strength_score += 1
                
                if strength_score >= 4: st.success("🚀 明日漲勢機率較高 (統計強勢型態)")
                elif strength_score >= 2: st.info("⚖️ 明日震盪機率較高 (觀察盤中氣勢)")
                else: st.error("📉 明日下跌機率偏高 (缺乏強勢動能)")
                # ----------------------------

                                       # --- [新增] 老王分析師技術觀察邏輯引擎 (調整數值版) ---
                st.subheader("🎙️ 老王分析師技術觀察")
                
                # 老王核心指標數值：
                # 1. 均量需要爆出 1.5 倍 (主力表態)
                # 2. 均線依賴 MA20 (月線)
                # 3. RSI 超賣/超買區域設定更嚴格 (30/70)
                is_above_ma20 = close_p > ma20
                is_kd_gold = k_val > d_val
                is_vol_break = vol_ratio > 1.5 
                is_overheat = rsi_val > 70
                is_oversold = rsi_val < 30
                is_bullish_engulf = (p_body < 0 and body > 0 and close_p > p_open and open_p < p_close)
                
                # 矩陣式邏輯判斷
                comment = "🎙️ 老王：『"
                
                if is_above_ma20:
                    if is_kd_gold and is_vol_break:
                        comment += "站上月線且爆出 1.5 倍攻擊量，指標黃金交叉，這是主力強勢表態，多頭攻擊格局！"
                    elif is_kd_gold:
                        comment += "月線多頭排列，雖然量能稍平，但只要守住 20 日生命線，行情都還有戲。"
                    elif is_overheat:
                        comment += "乖離率已大，RSI 超過 70 進入過熱區，短線不建議追高，等拉回月線支撐再切入。"
                    else:
                        comment += "目前在月線之上整理，多空力道拉鋸，請嚴守月線這條生命線，沒破就續抱。"
                else:
                    if is_oversold:
                        comment += "RSI 已跌破 30 超賣區，技術面隨時有反彈機會，但上方套牢賣壓重，搶短要快。"
                    elif is_kd_gold:
                        comment += "雖然指標黃金交叉，但還在月線之下，這是空頭結構中的反彈，上方壓力沈重，先看戲。"
                    elif is_vol_break:
                        comment += "跌破月線後爆出 1.5 倍成交量，這是恐慌性出貨，千萬不要去接掉下來的刀子！"
                    else:
                        comment += "空頭排列結構，月線壓力沈重，趨勢向下，場外觀望才是最高指導原則。"
                
                if is_bullish_engulf:
                    comment += " 此外，今日強勢吞沒前一日黑 K，多方有強力反撲意圖。"
                
                comment += "』"
                
                # 顯示判斷結果
                if "攻擊" in comment or "續抱" in comment or "表態" in comment or "強力反撲" in comment:
                    st.success(comment)
                elif "觀望" in comment or "壓力" in comment or "刀子" in comment:
                    st.error(comment)
                else:
                    st.info(comment)
                # ----------------------------------------


                # ----------------------------------------

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
                st.subheader("🎯 老王式波段佈局關鍵價位")
                
                # 老王思維：以月線(MA20)作為多空分水嶺，所有佈局均以此為核心
                # 1. 如果股價在月線之上，月線是最佳支撐
                # 2. 如果股價在月線之下，月線是壓力，需等待帶量站上
                st.write(f"* **多空生命線 (月線)：** `{ma20:.2f} 元`")
                st.write(f"* **強勢攻擊門檻 (5日/10日均線)：** `{ma5:.2f} / {ma10:.2f} 元`")
                st.write(f"* **防守型支撐 (60日線低點)：** `{lowest_60d:.2f} 元`")
                
                # 停損邏輯改進：嚴格設定為月線下方 3% 或 60 日低點，這才是老王強調的紀律
                stop_loss = ma20 * 0.97 if close_p > ma20 else lowest_60d * 0.97
                st.error(f"🛡️ **老王鐵律退場價 (嚴格停損)：** `{stop_loss:.2f} 元`")

                st.divider()
                st.subheader("⚖️ 風報比交易評估 (老王邏輯)")
                # 風報比計算：利潤取黃金目標價(1.618)，風險取嚴格停損距離
                potential_profit = target_1618 - close_p
                potential_risk = close_p - stop_loss
                if potential_risk <= 0: potential_risk = 0.01
                rr_ratio = potential_profit / potential_risk
                
                st.write(f"* **潛在獲利目標 (1.618波段目標)：** `+{potential_profit:.2f} 元`")
                st.write(f"* **必須承擔的風險距離：** `-{potential_risk:.2f} 元`")
                st.write(f"* **交易風報比：** `{rr_ratio:.2f} (老王建議：至少要大於 2.0 才值得進場)`")

                if rr_ratio >= 2.0:
                    st.success("🟢 **勝算評估：風報比 > 2.0，符合老王期望的『低風險、高獲利』標準。**")
                elif rr_ratio >= 1.5:
                    st.warning("🟡 **勝算評估：風報比 1.5 ~ 2.0，可考慮分批佈局。**")
                else:
                    st.error("❌ **勝算評估：風險大於獲利潛力，不符合老王的操作紀律，請觀望。**")


                st.divider()
                st.subheader("🔮 未來上漲目標預估")
                st.write(f"* **近 60 天波段大魔王：** `{highest_60d:.2f} 元`")
                st.write(f"* **黃金波段第一目標價：** `{target_1382:.2f} 元`")
                st.write(f"* **黃金波段第二目標價：** `{target_1618:.2f} 元`")
                st.caption("⚠️ 聲明：本網頁僅供技術分析討論，不構成投資與買賣建議。")
