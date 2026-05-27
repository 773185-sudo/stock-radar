import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np  # 確保矩陣運算正常

# 設定 Streamlit 網頁標題與主題
st.set_page_config(page_title="🛡️ 台股籌碼防空雷達儀表板", layout="wide")

st.title("🛡️ 終極實戰：台股籌碼防空雷達儀表板")
st.markdown("本系統已全面移除模擬數據，100% 串接 Yahoo Finance 與證交所真實法人籌碼。")

# ==========================================
# 🔑 側邊欄配置區：參數輸入與防禦機制
# ==========================================
st.sidebar.header("⚙️ 雷達控制面板")

# 1. 股票代號輸入 (支援純數字或自帶後綴)
stock_input = st.sidebar.text_input("請輸入台股代號", value="8069", help="例如：2409、8069、2330")

# 2. 籌碼數據免費 Token 配置
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 籌碼數據權限")
finmind_token = st.sidebar.text_input("輸入免費 FinMind Token", type="password", help="未輸入則使用匿名連線，極易因爆額度而斷線。")
st.sidebar.markdown("""
[👉 點此前往 FinMind 官網免費註冊](https://finmindtrade.com/)  
*(以 Google 登入後，至個人後台複製 Token 貼來此處，每日即享有 600 次真實數據查詢額度)*
""")

# 3. 📅 時間範圍安全設定 (單一日期 + 固定區間防禦，避免抓爆數據)
st.sidebar.markdown("---")
st.sidebar.subheader("📅 時間範圍設定")
end_date = st.sidebar.date_input("基準結束日期", value=datetime.date.today())

period_option = st.sidebar.selectbox(
    "選擇顯示區間 (預設半年)",
    ["1 個月", "3 個月", "半年", "1 年", "2 年"],
    index=2  # 預設停在「半年」
)

# 根據選擇動態計算開始日期
if period_option == "1 個月":
    start_date = end_date - datetime.timedelta(days=30)
elif period_option == "3 個月":
    start_date = end_date - datetime.timedelta(days=90)
elif period_option == "半年":
    start_date = end_date - datetime.timedelta(days=182)
elif period_option == "1 年":
    start_date = end_date - datetime.timedelta(days=365)
elif period_option == "2 年":
    start_date = end_date - datetime.timedelta(days=365 * 2)

st.sidebar.caption(f"🔍 系統將安全抓取：{start_date} 至 {end_date}")


# ==========================================
# ⚡ 高效快取數據下載函式 (防止重複消耗 API 額度)
# ==========================================
@st.cache_data(ttl=1800)  # 快取 30 分鐘
def fetch_smart_yfinance_data(stock_in, start, end):
    """智慧型 Yahoo Finance 下載器：自動識別上市(.TW)或上櫃(.TWO)"""
    symbol = stock_in.strip().upper()
    if symbol.isdigit() and len(symbol) == 4:
        # 先嘗試上市
        df = yf.download(f"{symbol}.TW", start=start, end=end, progress=False)
        if not df.empty and len(df) > 0:
            return df, f"{symbol}.TW"
        # 失敗則嘗試上櫃 (解決 8069.TW 找不到的問題)
        df = yf.download(f"{symbol}.TWO", start=start, end=end, progress=False)
        if not df.empty and len(df) > 0:
            return df, f"{symbol}.TWO"
        return pd.DataFrame(), symbol
    else:
        df = yf.download(symbol, start=start, end=end, progress=False)
        return df, symbol

@st.cache_data(ttl=1800)
def fetch_real_institutional_data(stock_code, start_str, end_str, token):
    """FinMind 真實三大法人籌碼下載器"""
    from FinMind.data import DataLoader
    dl = DataLoader()
    if token:
        try:
            dl.login_by_token(token)
        except:
            pass
    df = dl.taiwan_stock_institutional_investors(
        stock_id=stock_code,
        start_date=start_str,
        end_date=end_str
    )
    return df


# ==========================================
# 📊 區塊 1：K 線與技術主圖繪製 (Yahoo Finance)
# ==========================================
st.subheader("📈 區塊 1：智慧 K 線主技術圖表")

with st.spinner("正在向國際市場調閱股價 K 線數據..."):
    df_price, final_ticker = fetch_smart_yfinance_data(stock_input, start_date, end_date)

if df_price.empty:
    st.error(f"❌ 找不到股票代號 '{stock_input}' 的市場價格數據，請確認代號是否輸入正確。")
else:
    # 🌟 核心關鍵修復：如果欄位是新版 yfinance 的雙層 MultiIndex，強制降維成單層欄位
    if isinstance(df_price.columns, pd.MultiIndex):
        df_price.columns = df_price.columns.get_level_values(0)
    
    # 確保欄位完全壓平後，再進行索引重設
    df_price = df_price.reset_index()
    
    st.success(f"✅ 成功載入 {final_ticker} 的歷史技術數據！")
    
    # 建立 K 線圖表
    fig1 = go.Figure()
    fig1.add_trace(go.Candlestick(
        x=df_price['Date'],
        open=df_price['Open'],
        high=df_price['High'],
        low=df_price['Low'],
        close=df_price['Close'],
        name='K線',
        increasing_line_color='#FF3333', # 台股上漲為紅
        decreasing_line_color='#00AA00'  # 台股下跌為綠
    ))
    
    # 計算 5 日與 20 日均線
    df_price['MA5'] = df_price['Close'].rolling(window=5).mean()
    df_price['MA20'] = df_price['Close'].rolling(window=20).mean()
    
    fig1.add_trace(go.Scatter(x=df_price['Date'], y=df_price['MA5'], name='5MA', line=dict(color='#FFD700', width=1.5)))
    fig1.add_trace(go.Scatter(x=df_price['Date'], y=df_price['MA20'], name='20MA', line=dict(color='#00BFFF', width=1.5)))
    
    fig1.update_layout(
        template="plotly_dark",
        height=450,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )
    st.plotly_chart(fig1, width='stretch')


# ==========================================
# 🛡️ 區塊 2 & 4：真實法人籌碼對決雷達 (FinMind)
# ==========================================
st.markdown("---")
st.markdown("## 🛡️ 真實法人籌碼對決雷達")

# 自動清洗代號，只取純數字送給證交所 API
clean_stock_id = "".join(filter(str.isdigit, stock_input))

if not finmind_token:
    st.info("💡 **請在左側邊欄輸入您的免費 FinMind Token**，即可安全解鎖證交所真實籌碼數據！\n\n*(由於 Streamlit 雲端公用 IP 極易被 API 官方限流，必須使用個人 Token 才能穿透阻擋。)*")
else:
    with st.spinner("🚀 正在穿透證交所防火牆，安全載入真實籌碼數據中..."):
        try:
            df_inst = fetch_real_institutional_data(
                stock_code=clean_stock_id,
                start_str=start_date.strftime("%Y-%m-%d"),
                end_str=end_date.strftime("%Y-%m-%d"),
                token=finmind_token
            )
        except Exception as e:
            st.error(f"❌ 連線失敗。您的 Token 可能輸入錯誤或已達今日上限。錯誤訊息: {e}")
            df_inst = pd.DataFrame()

    if df_inst.empty:
        st.warning("⚠️ 目前該日期區間無真實籌碼資料，請嘗試更換代號或將基準日期調整為交易日。")
    else:
        # 將證交所單位的「股」換算為台股習慣的「張」 (除以 1000)
        df_inst['Net_Shares'] = (df_inst['buy'] - df_inst['sell']) / 1000

        # ---------------------------------------------------------
        # 區塊 2: 三大法人對決表 (真實最新單日數據)
        # ---------------------------------------------------------
        st.markdown("### ⚔️ 區塊 2：最新單日三大法人動向")
        
        latest_date = df_inst['date'].max()
        df_latest = df_inst[df_inst['date'] == latest_date]

        # 透過精準字串過濾分離三大法人
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
        # 區塊 4: 真實法人籌碼動向與趨勢圖
        # ---------------------------------------------------------
        st.markdown(f"### 📈 區塊 4：{clean_stock_id} 法人合計買賣超與歷史趨勢線")

        # 彙整每日三大法人合計
        df_daily = df_inst.groupby('date')['Net_Shares'].sum().reset_index()
        df_daily['MA5'] = df_daily['Net_Shares'].rolling(window=5).mean() # 5日籌碼均線
        df_daily['Cumulative'] = df_daily['Net_Shares'].cumsum()          # 累積庫存趨勢

        # 建立雙軸畫布
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        # 1. 每日法人買賣超柱狀圖 (左軸)
        bar_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_daily['Net_Shares']]
        fig2.add_trace(go.Bar(
            x=df_daily['date'], 
            y=df_daily['Net_Shares'], 
            name='法人單日合計 (張)', 
            marker_color=bar_colors,
            opacity=0.8
        ), secondary_y=False)

        # 2. 5日籌碼均線 (左軸)
        fig2.add_trace(go.Scatter(
            x=df_daily['date'], 
            y=df_daily['MA5'], 
            name='籌碼 5日均線', 
            line=dict(color='#FFD700', width=2)
        ), secondary_y=False)

        # 3. 累積籌碼趨勢線 (右軸)
        fig2.add_trace(go.Scatter(
            x=df_daily['date'], 
            y=df_daily['Cumulative'], 
            name='大戶累積波段籌碼', 
            line=dict(color='#00BFFF', width=2.5, dash='dot')
        ), secondary_y=True)

        # 圖表美化配置
        fig2.update_layout(
            template="plotly_dark",
            height=450,
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig2.update_yaxes(title_text="單日 / 均線灌入張數", secondary_y=False)
        fig2.update_yaxes(title_text="波段累積庫存張數", secondary_y=True, showgrid=False)

        # 打上網頁展示
        st.plotly_chart(fig2, width='stretch')
