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
        # 🌟 終極籌碼防空儀表板 (真實 FinMind API + 高效快取防禦)
        # ==========================================
        st.markdown("---")
        st.markdown("## 🛡️ 真實法人籌碼對決雷達")

        # A. 在側邊欄配置 Token 輸入框，全面保護您的看盤額度
        st.sidebar.markdown("---")
        st.sidebar.header("🔑 籌碼數據權限設定")
        finmind_token = st.sidebar.text_input("請輸入您的免費 FinMind Token", type="password", help="未輸入則使用匿名連線，極易因爆額度而斷線。")
        st.sidebar.markdown("""
        [👉 點此前往 FinMind 官網免費註冊](https://finmindtrade.com/)  
        *(以 Google 登入後，至個人後台複製 Token 貼來此處，每日即享有 600 次真實數據查詢額度)*
        """)

        # B. 建立具有「快取保護機制」的真實數據下載函式 (防止網頁重整重複消耗額度)
        @st.cache_data(ttl=1800) # 快取 30 分鐘
        def fetch_real_institutional_data(stock_code, start_str, end_str, token):
            from FinMind.data import DataLoader
            dl = DataLoader()
            if token:
                try:
                    dl.login_by_token(token) # 使用您的專屬 Token 登入
                except:
                    pass
            # 抓取真實三大法人資料
            df = dl.taiwan_stock_institutional_investors(
                stock_id=stock_code,
                start_date=start_str,
                end_date=end_str
            )
            return df

        # C. 自動清洗代號 (不管輸入 8069.TWO 還是 2409.TW，都自動轉為純數字 8069、2409 送給證交所)
        clean_stock_id = "".join(filter(str.isdigit, stock_input))

        # D. 執行真實數據調用
        with st.spinner("🚀 正在穿透證交所防火牆，安全載入真實籌碼數據中..."):
            try:
                df_inst = fetch_real_institutional_data(
                    stock_code=clean_stock_id,
                    start_str=start_date.strftime("%Y-%m-%d"),
                    end_str=end_date.strftime("%Y-%m-%d"),
                    token=finmind_token
                )
            except Exception as e:
                st.error(f"❌ 無法連線至數據庫，可能已被官方限制 IP。請於側邊欄輸入免費的個人 Token 解除限制。錯誤原因: {e}")
                df_inst = pd.DataFrame()

        # E. 開始繪製真實籌碼面板
        if df_inst.empty:
            st.warning("⚠️ 目前該日期區間無真實籌碼資料，或是匿名額度已達上限。請嘗試縮短查詢天數，或在左側填入免費 Token。")
        else:
            # 將證交所的「股」換算為台股習慣的「張」 (除以 1000)
            df_inst['Net_Shares'] = (df_inst['buy'] - df_inst['sell']) / 1000

            # ---------------------------------------------------------
            # 區塊 2: 三大法人對決表 (真實最新單日數據)
            # ---------------------------------------------------------
            st.markdown("### ⚔️ 區塊 2：最新單日三大法人動向")
            
            latest_date = df_inst['date'].max()
            df_latest = df_inst[df_inst['date'] == latest_date]

            # 透過字串比對，精準分離外資、投信、自營商
            foreign_net = df_latest[df_latest['name'].str.contains('外資|Foreign', case=False, na=False)]['Net_Shares'].sum()
            trust_net = df_latest[df_latest['name'].str.contains('投信|Trust', case=False, na=False)]['Net_Shares'].sum()
            dealer_net = df_latest[df_latest['name'].str.contains('自營商|Dealer', case=False, na=False)]['Net_Shares'].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label=f"外資單日 ({latest_date})", value=f"{foreign_net:,.0f} 張", 
                          delta="買超偏多" if foreign_net >= 0 else "賣超偏空", delta_color="normal")
            with col2:
                st.metric(label=f"投信單日 ({latest_date})", value=f"{trust_net:,.0f} 張",
                          delta="買超偏多" if trust_net >= 0 else "賣超偏空", delta_color="normal")
            with col3:
                st.metric(label=f"自營商單日 ({latest_date})", value=f"{dealer_net:,.0f} 張",
                          delta="買超偏多" if dealer_net >= 0 else "賣超偏空", delta_color="normal")

            # ---------------------------------------------------------
            # 區塊 4: 真實法人籌碼動向與趨勢圖 (柱狀 + 均線 + 右軸累積)
            # ---------------------------------------------------------
            st.markdown(f"### 📈 區塊 4：{clean_stock_id} 法人合計買賣超與歷史趨勢線")

            # 計算每日三大法人合計
            df_daily = df_inst.groupby('date')['Net_Shares'].sum().reset_index()
            df_daily['MA5'] = df_daily['Net_Shares'].rolling(window=5).mean() # 5日籌碼平均線
            df_daily['Cumulative'] = df_daily['Net_Shares'].cumsum()          # 累積籌碼趨勢

            # 建立高級雙 Y 軸畫布
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])

            # 1. 每日法人買賣超柱狀圖 (左軸)
            # 買超為正顯示紅色，賣超為負顯示綠色
            bar_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_daily['Net_Shares']]
            fig2.add_trace(go.Bar(
                x=df_daily['date'], 
                y=df_daily['Net_Shares'], 
                name='法人單日合計 (張)', 
                marker_color=bar_colors,
                opacity=0.8
            ), secondary_y=False)

            # 2. 5日籌碼均線 (左軸) - 用來觀察主力有沒有連續吃貨
            fig2.add_trace(go.Scatter(
                x=df_daily['date'], 
                y=df_daily['MA5'], 
                name='籌碼 5日均線', 
                line=dict(color='#FFD700', width=2) # 金色
            ), secondary_y=False)

            # 3. 累積籌碼趨勢線 (右軸) - 觀察長線大戶資金是流入還是流出
            fig2.add_trace(go.Scatter(
                x=df_daily['date'], 
                y=df_daily['Cumulative'], 
                name='大戶累積波段籌碼', 
                line=dict(color='#00BFFF', width=2.5, dash='dot') # 藍色波浪虛線
            ), secondary_y=True)

            # 圖表整體美化
            fig2.update_layout(
                template="plotly_dark",
                height=450,
                margin=dict(l=10, r=10, t=30, b=10),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig2.update_yaxes(title_text="單日 / 均線灌入張數", secondary_y=False)
            fig2.update_yaxes(title_text="波段累積庫存張數", secondary_y=True, showgrid=False)

            # 把精心調製的真實籌碼圖打上網頁
            st.plotly_chart(fig2, width='stretch')

            # 輸出到網頁
            st.plotly_chart(fig2, use_container_width=True)
