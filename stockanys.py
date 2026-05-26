import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time  # 🌟 新增：用來控制 API 請求頻率，防止被封鎖
from FinMind.data import DataLoader

# ==========================================
# 1. 網頁基本配置
# ==========================================
st.set_page_config(
    page_title="台股100%全真籌碼歷史防空雷達", 
    page_icon="📡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📡 台股 100% 純金真籌碼歷史防空雷達 🚀")
st.write("已實裝【防封鎖節流引擎】，穩定提取 FinMind 實時官方數據！")
st.markdown("---")

# ==========================================
# 2. 使用者互動輸入元件
# ==========================================
col_in1, col_in2 = st.columns([1.2, 1])
with col_in1:
    stock_input = st.text_input("👉 請輸入台股 4 碼股票代號（例如：2409、3481、8069）：", value="2409", max_chars=4).strip()
with col_in2:
    target_date = st.date_input("📅 請選擇欲檢視的交易日期：", value=datetime.date.today())

actual_date_finmind = target_date.strftime("%Y-%m-%d")

if st.button("🔥 啟動跨時空全景大數據補完"):
    with st.spinner(f"📡 雷達正在向官方與 FinMind 資料庫調取 {actual_date_finmind} 的實時數據 (為防阻擋，約需 3-5 秒)..."):
        
        api_loader = DataLoader()
        
        # ==========================================
        # 3. K線與上市櫃識別 (Yahoo Finance)
        # ==========================================
        start_date = target_date - datetime.timedelta(days=90)
        end_date = target_date + datetime.timedelta(days=1)
        
        stock_yahoo = f"{stock_input}.TW"
        df_k = yf.download(stock_yahoo, start=start_date, end=end_date, progress=False)
        market_type_name = "上市"
        
        if df_k.empty:
            stock_yahoo = f"{stock_input}.TWO"
            df_k = yf.download(stock_yahoo, start=start_date, end=end_date, progress=False)
            market_type_name = "上櫃"
            
        if df_k.empty:
            st.error(f"❌ 查無此代號 [{stock_input}]。當天（{actual_date_finmind}）可能為台股非交易日（週末/國定假日），官方無任何籌碼公告。")
            st.stop()
            
        if isinstance(df_k.columns, pd.MultiIndex):
            df_k.columns = df_k.columns.get_level_values(0)
            
        df_k['5MA'] = df_k['Close'].rolling(window=5).mean()
        df_k['20MA'] = df_k['Close'].rolling(window=20).mean()
        df_k['5VolMA'] = df_k['Volume'].rolling(window=5).mean()
        
        latest_close = float(df_k['Close'].iloc[-1])
        actual_data_date = df_k.index[-1].strftime("%Y/%m/%d")
        actual_date_finmind = df_k.index[-1].strftime("%Y-%m-%d")

        # ==========================================
        # 🌟 模組二：三大法人買賣超 (FinMind)
        # ==========================================
        foreign_shares = 0
        trust_shares = 0
        dealer_shares = 0
        
        try:
            df_institutional = api_loader.taiwan_stock_institutional_investors(
                stock_id=stock_input,
                start_date=actual_date_finmind,
                end_date=actual_date_finmind
            )
            if not df_institutional.empty:
                for _, row_inst in df_institutional.iterrows():
                    name = row_inst['name']
                    buy_sell_lots = int(row_inst['buy'] - row_inst['sell']) // 1000
                    if "外資" in name or "陸資" in name:
                        foreign_shares += buy_sell_lots
                    elif "投信" in name:
                        trust_shares += buy_sell_lots
                    elif "自營商" in name:
                        dealer_shares += buy_sell_lots
                        
                foreign_txt = f"🔺 淨買超 {foreign_shares:,} 張" if foreign_shares > 0 else (f"❌ 淨賣超 {abs(foreign_shares):,} 張" if foreign_shares < 0 else "⚪ 淨買賣 0 張")
                trust_txt = f"🔺 淨買超 {trust_shares:,} 張" if trust_shares > 0 else (f"❌ 淨賣超 {abs(trust_shares):,} 張" if trust_shares < 0 else "⚪ 淨買賣 0 張")
                dealer_txt = f"🔺 淨買超 {dealer_shares:,} 張" if dealer_shares > 0 else (f"❌ 淨賣超 {abs(dealer_shares):,} 張" if dealer_shares < 0 else "⚪ 淨買賣 0 張")
            else:
                foreign_txt = trust_txt = dealer_txt = "⏳ 官方當日未公告或無交易"
        except:
            foreign_txt = trust_txt = dealer_txt = "⚠️ API 阻擋，請稍後再試"

        time.sleep(0.8) # 🛑 節流閥：防止連續請求被 FinMind 封鎖

        # ==========================================
        # 🌟 模組三：融資、融券、借券賣出 (FinMind)
        # ==========================================
        real_margin_balance = "官方當日未公告"
        real_margin_change = "0 張"
        real_short_balance = "官方當日未公告"
        real_short_change = "0 張"
        real_borrow_sell = "官方當日未公告"
        
        try:
            df_margin = api_loader.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_input,
                start_date=actual_date_finmind,
                end_date=actual_date_finmind
            )
            if not df_margin.empty:
                cols = df_margin.columns.tolist()
                
                # 🌟 嚴格修正：只抓取包含 Balance (餘額) 的真實數據，排除 Limit (限額)
                m_bal_col = next((c for c in cols if 'MarginPurchase' in c and 'Balance' in c), '')
                m_buy_col = next((c for c in cols if 'MarginPurchaseBuy' in c), '')
                m_sell_col = next((c for c in cols if 'MarginPurchaseSell' in c), '')
                
                s_bal_col = next((c for c in cols if 'ShortSale' in c and 'Balance' in c), '')
                s_buy_col = next((c for c in cols if 'ShortSaleBuy' in c), '')
                s_sell_col = next((c for c in cols if 'ShortSaleSell' in c), '')
                
                sbl_col = next((c for c in cols if 'SBL' in c and 'Balance' in c), '')
                
                if m_bal_col:
                    real_margin_balance = f"{int(df_margin[m_bal_col].iloc[-1]):,} 張"
                if m_buy_col and m_sell_col:
                    m_change = int(df_margin[m_buy_col].iloc[-1] - df_margin[m_sell_col].iloc[-1])
                    real_margin_change = f"{m_change:+,} 張"
                    
                if s_bal_col:
                    real_short_balance = f"{int(df_margin[s_bal_col].iloc[-1]):,} 張"
                if s_buy_col and s_sell_col:
                    s_change = int(df_margin[s_buy_col].iloc[-1] - df_margin[s_sell_col].iloc[-1])
                    real_short_change = f"{s_change:+,} 張"
                    
                if sbl_col:
                    real_borrow_sell = f"{int(df_margin[sbl_col].iloc[-1]):,} 張"
        except:
            pass

        time.sleep(0.8) # 🛑 節流閥

        # ==========================================
        # 🌟 模組四：當沖比例 (FinMind)
        # ==========================================
        real_day_trade_rate = "官方當日未公告"
        try:
            df_day_trade = api_loader.taiwan_stock_day_trading(
                stock_id=stock_input, 
                start_date=actual_date_finmind, 
                end_date=actual_date_finmind
            )
            if not df_day_trade.empty:
                cols = df_day_trade.columns.tolist()
                v_col = next((c for c in cols if 'Volume' in c and 'Day' not in c), '')
                dt_col = next((c for c in cols if 'Day_Trading_Volume' in c or 'DayTradingVolume' in c), '')
                
                if v_col and dt_col and float(df_day_trade[v_col].iloc[-1]) > 0:
                    dt_ratio = float(df_day_trade[dt_col].iloc[-1]) / float(df_day_trade[v_col].iloc[-1]) * 100
                    real_day_trade_rate = f"⚡ {dt_ratio:.1f} %"
        except:
            pass

        time.sleep(0.8) # 🛑 節流閥

        # ==========================================
        # 🌟 模組五：Top 3 券商分點對決 (FinMind)
        # ==========================================
        buy_df_show = pd.DataFrame()
        sell_df_show = pd.DataFrame()
        
        try:
            df_broker = api_loader.taiwan_stock_broker_holders_by_id(
                stock_id=stock_input,
                start_date=actual_date_finmind,
                end_date=actual_date_finmind
            )
            if not df_broker.empty:
                b_cols = df_broker.columns.tolist()
                buy_idx = next((c for c in b_cols if 'BuyShare' in c or 'buy_share' in c), '')
                sell_idx = next((c for c in b_cols if 'SellShare' in c or 'sell_share' in c), '')
                name_idx = next((c for c in b_cols if 'BrokerName' in c or 'broker_name' in c), '')
                
                if buy_idx and sell_idx and name_idx:
                    df_broker['Net_Shares'] = df_broker[buy_idx] - df_broker[sell_idx]
                    df_broker['Net_Lots'] = (df_broker['Net_Shares'] / 1000).round(0).astype(int)
                    
                    df_active = df_broker[df_broker['Net_Lots'] != 0]
                    df_top_buy = df_active.sort_values(by='Net_Lots', ascending=False).head(3)
                    df_top_sell = df_active.sort_values(by='Net_Lots', ascending=True).head(3)
                    
                    if not df_top_buy.empty:
                        buy_df_show = pd.DataFrame({
                            "買超券商分點": df_top_buy[name_idx].tolist(),
                            "買賣超張數": [f"{x:,} 張" for x in df_top_buy['Net_Lots'].tolist()],
                            "當日收盤價": [f"{latest_close:.2f} 元" for _ in range(len(df_top_buy))]
                        })
                        
                    if not df_top_sell.empty:
                        sell_brokers = df_top_sell[name_idx].tolist()
                        tags = []
                        for b_name in sell_brokers:
                            if any(ext in b_name for ext in ["摩根", "高盛", "美林", "瑞士", "麥格理", "野村"]):
                                tags.append("🚨 外資主要分點")
                            elif any(local in b_name for local in ["凱基", "富邦", "元大", "永豐金", "統一"]):
                                tags.append("⚠️ 本土大型券商")
                            else:
                                tags.append("📡 分點實時監控")
                                
                        sell_df_show = pd.DataFrame({
                            "賣超券商分點": sell_brokers,
                            "買賣超張數": [f"{abs(x):,} 張" for x in df_top_sell['Net_Lots'].tolist()],
                            "當日收盤價": [f"{latest_close:.2f} 元" for _ in range(len(df_top_sell))],
                            "券商屬性標籤": tags
                        })
        except:
            pass

        # ==========================================
        # 6. 前端畫面渲染
        # ==========================================
        st.success(f"✅ 【100% 全真實數據解鎖】 [{market_type_name}] 代號：{stock_input} | 交易日期：{actual_data_date} (收盤價: {latest_close:.2f} 元)")
        
        # K線圖表
        st.subheader(f"📈 歷史動態日 K 線與成交量均線圖表 ({actual_data_date} 之前)")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12, row_width=[0.35, 0.65])
        fig.add_trace(go.Candlestick(x=df_k.index, open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'], name="日K線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_k.index, y=df_k['5MA'], line=dict(color='#2980B9', width=1.5), name="5MA"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_k.index, y=df_k['20MA'], line=dict(color='#E67E22', width=2), name="20MA(月線)"), row=1, col=1)
        v_colors = ['#E74C3C' if cl >= op else '#2ECC71' for op, cl in zip(df_k['Open'], df_k['Close'])]
        fig.add_trace(go.Bar(x=df_k.index, y=df_k['Volume'], marker_color=v_colors, name="成交量"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_k.index, y=df_k['5VolMA'], line=dict(color='#8E44AD', width=1.5), name="5日均量"), row=2, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False, height=520, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("---")
        
        # 三大法人
        st.subheader(f"🕵️‍♂️ 三大法人當日進出明細 ({actual_data_date})")
        st.write(f"🛸 **外資主力動向**： {foreign_txt}")
        st.write(f"🧸 **投信法人動向**： {trust_txt}")
        st.write(f"🦊 **自營商動向**： {dealer_txt}")
        
        st.write("---")
        
        # 信用資券與當沖
        st.subheader(f"💳 信用資券與當沖力檢視 ({actual_data_date})")
        col_credit1, col_credit2 = st.columns(2)
        with col_credit1:
            st.write(f"🛒 **融資當日餘額**： {real_margin_balance} (今日變動: {real_margin_change})")
            st.write(f"📉 **融券當日餘額**： {real_short_balance} (今日變動: {real_short_change})")
        with col_credit2:
            st.write(f"🔥 **外資借券賣出餘額**： {real_borrow_sell}")
            st.write(f"⚡ **當天當沖成交比例**： {real_day_trade_rate}")
            
        st.write("---")
        
        # 核心分點
        st.subheader(f"🔥 核心券商分點進出大對決 ({actual_data_date})")
        col_buy, col_sell = st.columns(2)
        with col_buy:
            st.markdown("📈 **當日真實買超前三強券商**")
            if not buy_df_show.empty:
                st.table(buy_df_show)
            else:
                st.write("⚪ 當天官方暫無買超張數大於1張之主要分點資料。")
        with col_sell:
            st.markdown("📉 **當日真實賣超前三強券商**")
            if not sell_df_show.empty:
                st.table(sell_df_show)
            else:
                st.write("⚪ 當天官方暫無賣超張數大於1張之主要分點資料。")
                
        # 超連結
        goodinfo_url = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={stock_input}"
        st.markdown(f"🔗 [交叉比對外部網站？點我一鍵跳轉 Goodinfo! 備用頁面]({goodinfo_url})")
