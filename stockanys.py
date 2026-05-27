import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

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
