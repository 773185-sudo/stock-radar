import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np

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

        # ---------------------------------------------------------
        # 區塊 2: 三大法人對決表
        # ---------------------------------------------------------
        st.markdown("### ⚔️ 區塊 2：三大法人對決表 (單日)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="外資單日動向", value="買超", delta="+2,500 張")
        with col2:
            st.metric(label="投信單日動向", value="買超", delta="+800 張")
        with col3:
            st.metric(label="自營商單日動向", value="賣超", delta="-350 張", delta_color="inverse")

        # ---------------------------------------------------------
        # 區塊 3: 單日反水警報燈
        # ---------------------------------------------------------
        st.markdown("### 🚨 區塊 3：單日反水警報燈")
        # 這裡用一點 HTML/Markdown 做出警報燈的效果
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<h5 style='text-align: center; color: #a0a0a0;'>家數差 (籌碼集中度)</h5>", unsafe_allow_html=True)
            # 假設家數為負(買家少賣家多 = 籌碼集中) 亮綠燈
            st.markdown("<h3 style='text-align: center;'>🟢 集中綠燈</h3>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<h5 style='text-align: center; color: #a0a0a0;'>散戶動向</h5>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center;'>🏃‍♂️ 散戶逃亡 (偏多)</h3>", unsafe_allow_html=True)
            
        with col3:
            st.markdown("<h5 style='text-align: center; color: #a0a0a0;'>借券賣出變動率</h5>", unsafe_allow_html=True)
            st.metric(label="單日增減", value="-5.2%", delta="空單回補 (偏多)")

# ---------------------------------------------------------
        # 區塊 4: 法人籌碼動向與趨勢圖 (複合圖表)
        # ---------------------------------------------------------
        st.markdown("### 📈 區塊 4：法人籌碼動向趨勢圖 (模擬數據演示)")
        
        # 1. 產生模擬歷史數據 (近 30 天法人買賣超)
        dates = pd.date_range(end=datetime.date.today(), periods=30)
        # 隨機產生買賣超張數 (介於 -5000 到 5000 之間)
        np.random.seed(42) # 固定亂數種子讓畫面穩定，實際串接時請拿掉
        net_buy_sell = np.random.randint(-5000, 5000, size=30)
        
        # 建立 DataFrame 並計算均線與累積值
        df_mock = pd.DataFrame({'Date': dates, 'Net': net_buy_sell})
        df_mock['MA5'] = df_mock['Net'].rolling(window=5).mean() # 5日平均線
        df_mock['Cumulative'] = df_mock['Net'].cumsum()          # 累積買賣超

        # 2. 建立雙 Y 軸圖表
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        # A. 柱狀圖 (每日買賣超，對應左側 Y 軸)
        # 買超為紅，賣超為綠
        bar_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_mock['Net']]
        fig2.add_trace(go.Bar(
            x=df_mock['Date'], 
            y=df_mock['Net'], 
            name='單日買賣超 (張)', 
            marker_color=bar_colors,
            opacity=0.7
        ), secondary_y=False)

        # B. 趨勢圖 (5日平均線，對應左側 Y 軸)
        fig2.add_trace(go.Scatter(
            x=df_mock['Date'], 
            y=df_mock['MA5'], 
            name='5日平均線', 
            line=dict(color='#FFD700', width=2) # 金色
        ), secondary_y=False)

        # C. 累積趨勢線 (看長期方向，對應右側 Y 軸，避免刻度被單日數據吃掉)
        fig2.add_trace(go.Scatter(
            x=df_mock['Date'], 
            y=df_mock['Cumulative'], 
            name='累積買賣超', 
            line=dict(color='#00BFFF', width=2, dash='dot') # 藍色虛線
        ), secondary_y=True)

        # 3. 版面細節優化
        fig2.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            hovermode="x unified", # 滑鼠游標對齊時顯示所有數據
            legend=dict(
                orientation="h",   # 圖例橫向排列
                yanchor="bottom", y=1.02, 
                xanchor="right", x=1
            )
        )
        
        # 設定雙 Y 軸的標題
        fig2.update_yaxes(title_text="單日/均線 張數", secondary_y=False)
        fig2.update_yaxes(title_text="累積 張數", secondary_y=True, showgrid=False)

        # 輸出到網頁
        st.plotly_chart(fig2, use_container_width=True)
