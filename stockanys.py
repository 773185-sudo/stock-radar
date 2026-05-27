import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np
from FinMind.data import DataLoader
# ==========================================
# 1. 網頁基本配置 (手機/電腦全適應、科技風)
# ==========================================
st.set_page_config(
    page_title="台股終極籌碼防空雷達",
    page_icon="📡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📡 台股終極籌碼與 K 線防空雷達 🚀")
st.markdown("---")

# ==========================================
# 2. 參數輸入區 (股票代號與日期區間)
# ==========================================
stock_input = st.text_input("👉 請輸入台股 4 碼股票代號（例如：2409、3481、8069）：", value="")

col1, col2 = st.columns(2)
with col1:
    # 預設起始日為 90 天前
    start_date = st.date_input("📅 起始日期", datetime.date.today() - datetime.timedelta(days=90))
with col2:
    # 預設結束日為今天
    end_date = st.date_input("📅 結束日期", datetime.date.today())

# ==========================================
# 3. 核心數據流與動態繪圖區
# ==========================================
if st.button("🔥 啟動終極全景大數據掃描"):
    
    if not stock_input:
        st.warning("⚠️ 請先輸入股票代號！")
        st.stop()

    with st.spinner("雷達掃描中，請稍候..."):
        # --------------------------------------
        # A. 雙重確認機制：自動判斷上市 (.TW) 或上櫃 (.TWO)
        # --------------------------------------
        stock_yahoo_tw = f"{stock_input}.TW"
        ticker = yf.Ticker(stock_yahoo_tw)
        df_k = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if df_k.empty:
            # 若上市找不到，改找上櫃
            stock_yahoo_two = f"{stock_input}.TWO"
            ticker = yf.Ticker(stock_yahoo_two)
            df_k = ticker.history(start=start_date, end=end_date, interval="1d")
            stock_yahoo = stock_yahoo_two 
        else:
            stock_yahoo = stock_yahoo_tw
            
        # 兩次都失敗，阻斷程式並報錯
        if df_k.empty:
            st.error(f"❌ 查無此台股代號 [{stock_input}] 之歷史數據，請確認是否為上市櫃正常股票。")
            st.stop()
            
        # --------------------------------------
        # B. 資料清理與前處理
        # --------------------------------------
        # 將 Date 從 Index 移出變成一般欄位，方便 plotly 繪圖
        df_k = df_k.reset_index() 
        st.success(f"✅ 成功獲取 {stock_yahoo} 數據！")

        # --------------------------------------
        # C. 繪製 K 線圖與成交量 (Plotly 雙軸圖表)
        # --------------------------------------
        # 建立兩個子圖，共用 X 軸
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            row_heights=[0.7, 0.3])

        # 子圖 1：K線圖
        fig.add_trace(go.Candlestick(
            x=df_k['Date'],
            open=df_k['Open'],
            high=df_k['High'],
            low=df_k['Low'],
            close=df_k['Close'],
            name="日 K 線",
            increasing_line_color='#FF3333',    # 台股習慣：紅漲
            decreasing_line_color='#00AA00'     # 台股習慣：綠跌
        ), row=1, col=1)

        # 子圖 2：成交量圖
        # 依據當日收盤與開盤價，決定成交量柱狀圖是紅色還是綠色
        colors = ['#FF3333' if row['Close'] >= row['Open'] else '#00AA00' for index, row in df_k.iterrows()]
        fig.add_trace(go.Bar(
            x=df_k['Date'],
            y=df_k['Volume'],
            name="成交量",
            marker_color=colors
        ), row=2, col=1)

        # --------------------------------------
        # D. 圖表版面視覺優化
        # --------------------------------------
        fig.update_layout(
            title=f"<b>{stock_yahoo} 走勢全景圖</b>",
            xaxis_rangeslider_visible=False, # 隱藏預設的底部滑桿，讓畫面更簡潔
            height=600,
            margin=dict(l=20, r=20, t=50, b=20),
            template="plotly_dark",          # 啟動深色科技風主題
            showlegend=False
        )

        # 將畫好的圖表推送到網頁上
        st.plotly_chart(fig, use_container_width=True)
        # ==========================================
        # F. 終極籌碼防空雷達儀表板 (UI 版面建構)
        # ==========================================
        st.markdown("---")
        st.markdown("## 🛡️ 終極籌碼防空儀表板")
        
        # ⚠️ 提示訊息：告知目前為版面展示，需另外串接資料
        st.info("💡 溫馨提示：以下為您規劃的完美版面。由於 Yahoo 無法提供台灣籌碼數據，此處暫以「模擬變數」展示，未來可串接證交所或 FinMind API 替換真實數據。")

        # 【模擬真實數據的變數】(未來這裡會寫爬蟲程式來抓真實數字)
        mock_capital = 150  # 股本(億)
        mock_cost_60d = 145.5 # 60日成本
        mock_price = df_k['Close'].iloc[-1] # 抓取今天真實收盤價
        mock_diff_percent = ((mock_price - mock_cost_60d) / mock_cost_60d) * 100
        
        # ---------------------------------------------------------
        # 區塊 1: 基本防禦線 (大字報)
        # ---------------------------------------------------------
        st.markdown("### 🎯 區塊 1：基本防禦線")
        col1, col2, col3 = st.columns(3)
        with col1:
            # 股本大小自動分類邏輯
            capital_type = "大型股" if mock_capital > 100 else ("中型股" if mock_capital > 20 else "小型股")
            st.metric(label="📊 公司股本", value=f"{mock_capital} 億", delta=capital_type, delta_color="off")
        with col2:
            st.metric(label="🛡️ 60日大戶成本線", value=f"{mock_cost_60d} 元")
        with col3:
            # 依據正負值自動顯示紅綠顏色
            st.metric(label="⚖️ 當前股價與成本價差比", 
                      value=f"{mock_price:.2f} 元", 
                      delta=f"{mock_diff_percent:.2f}% (距離成本)")

       # ==========================================
        # 🌟 終極籌碼防空儀表板 (真實 FinMind API 數據)
        # ==========================================
        st.markdown("---")
        st.markdown("## 🛡️ 真實法人籌碼對決雷達")

        with st.spinner("連線證交所/櫃買中心，抓取真實籌碼中..."):
            dl = DataLoader()
            # 抓取法人資料 (FinMind 使用純數字代號)
            df_inst = dl.taiwan_stock_institutional_investors(
                stock_id=stock_input,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )

        if df_inst.empty:
            st.warning("⚠️ 目前查無這段期間的三大法人籌碼資料，可能是近期無交易或假日期。")
        else:
            # FinMind 的資料單位通常是「股」，我們換算成「張」 (除以 1000)
            # 計算淨買賣超：買進 - 賣出
            df_inst['Net'] = (df_inst['buy'] - df_inst['sell']) / 1000

            # ---------------------------------------------------------
            # 區塊 2: 三大法人對決表 (真實最新單日)
            # ---------------------------------------------------------
            st.markdown("### ⚔️ 最新單日三大法人動向")
            
            # 取得有資料的最新一天
            latest_date = df_inst['date'].max()
            df_latest = df_inst[df_inst['date'] == latest_date]

            # 自動分類計算三大法人 (使用正規表達式涵蓋中英文字位)
            foreign_net = df_latest[df_latest['name'].str.contains('外資|Foreign', case=False, na=False)]['Net'].sum()
            trust_net = df_latest[df_latest['name'].str.contains('投信|Trust', case=False, na=False)]['Net'].sum()
            dealer_net = df_latest[df_latest['name'].str.contains('自營商|Dealer', case=False, na=False)]['Net'].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label=f"外資 ({latest_date})", value=f"{foreign_net:,.0f} 張")
            with col2:
                st.metric(label=f"投信 ({latest_date})", value=f"{trust_net:,.0f} 張")
            with col3:
                st.metric(label=f"自營商 ({latest_date})", value=f"{dealer_net:,.0f} 張")

            # ---------------------------------------------------------
            # 區塊 4: 真實法人籌碼動向與趨勢圖
            # ---------------------------------------------------------
            st.markdown("### 📈 三大法人合計買賣超趨勢圖")

            # 將每天的所有法人買賣超加總，計算出每天的「總淨買賣」
            df_daily = df_inst.groupby('date')['Net'].sum().reset_index()
            # 計算 5 日平均與累積籌碼
            df_daily['MA5'] = df_daily['Net'].rolling(window=5).mean()
            df_daily['Cumulative'] = df_daily['Net'].cumsum()

            # 建立雙 Y 軸圖表
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])

            # A. 柱狀圖 (每日真實買賣超)
            bar_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_daily['Net']]
            fig2.add_trace(go.Bar(
                x=df_daily['date'], 
                y=df_daily['Net'], 
                name='單日合計買賣超 (張)', 
                marker_color=bar_colors,
                opacity=0.7
            ), secondary_y=False)

            # B. 趨勢圖 (5日均線)
            fig2.add_trace(go.Scatter(
                x=df_daily['date'], 
                y=df_daily['MA5'], 
                name='5日均線', 
                line=dict(color='#FFD700', width=2)
            ), secondary_y=False)

            # C. 累積趨勢線
            fig2.add_trace(go.Scatter(
                x=df_daily['date'], 
                y=df_daily['Cumulative'], 
                name='累積籌碼', 
                line=dict(color='#00BFFF', width=2, dash='dot')
            ), secondary_y=True)

            # 圖表版面優化
            fig2.update_layout(
                template="plotly_dark",
                height=400,
                margin=dict(l=20, r=20, t=30, b=20),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig2.update_yaxes(title_text="單日/均線 (張)", secondary_y=False)
            fig2.update_yaxes(title_text="累積 (張)", secondary_y=True, showgrid=False)

            # 輸出到網頁
            st.plotly_chart(fig2, use_container_width=True)
