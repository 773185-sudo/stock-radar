import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests

# 設定 Streamlit 網頁標題與寬螢幕配置
st.set_page_config(page_title="🛡️ 台股籌碼防空雷達儀表板 V4.0", layout="wide")

st.title("🛡️ 實戰升級：台股籌碼防空雷達儀表板")
st.markdown("本系統全面串接 Yahoo Finance、FinMind 籌碼數據，並即時連線證交所/櫃買中心 OpenAPI 監控處置狀態。")

# ==========================================
# 🔑 側邊欄配置區：參數輸入與防禦機制
# ==========================================
st.sidebar.header("⚙️ 雷達控制面板")

stock_input = st.sidebar.text_input("請輸入台股代號", value="8069", help="例如：2409、8069、2330")

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 籌碼數據權限")
finmind_token = st.sidebar.text_input("輸入免費 FinMind Token", type="password", help="請輸入 FinMind Token 確保連線穩定不中斷。")

st.sidebar.markdown("---")
st.sidebar.subheader("📅 時間範圍設定")
end_date = st.sidebar.date_input("基準結束日期", value=datetime.date.today())

period_option = st.sidebar.selectbox(
    "選擇顯示區間 (預設半年)",
    ["1 個月", "3 個月", "半年", "1 年", "2 年"],
    index=2
)

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


# ==========================================
# ⚡ 數據下載函式區 (Yahoo, FinMind, OpenAPI)
# ==========================================
@st.cache_data(ttl=1800)
def fetch_smart_yfinance_data(stock_in, start, end):
    symbol = stock_in.strip().upper()
    if symbol.isdigit() and len(symbol) == 4:
        df = yf.download(f"{symbol}.TW", start=start, end=end, progress=False)
        if not df.empty and len(df) > 0:
            return df, f"{symbol}.TW"
        df = yf.download(f"{symbol}.TWO", start=start, end=end, progress=False)
        if not df.empty and len(df) > 0:
            return df, f"{symbol}.TWO"
        return pd.DataFrame(), symbol
    else:
        df = yf.download(symbol, start=start, end=end, progress=False)
        return df, symbol

@st.cache_data(ttl=1800)
def fetch_finmind_dataset(dataset_name, stock_code, start_str, end_str, token):
    from FinMind.data import DataLoader
    dl = DataLoader()
    if token:
        try:
            dl.login_by_token(token)
        except:
            pass
    try:
        if dataset_name == "institutional":
            return dl.taiwan_stock_institutional_investors(stock_id=stock_code, start_date=start_str, end_date=end_str)
        elif dataset_name == "shareholding":
            return dl.taiwan_stock_holding_shares_per(stock_id=stock_code, start_date=start_str, end_date=end_str)
        elif dataset_name == "margin":
            return dl.taiwan_stock_margin_purchase_short_sale(stock_id=stock_code, start_date=start_str, end_date=end_str)
    except:
        return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=1800)
def check_official_warning_status(stock_code):
    """直接爬取證交所與櫃買中心 OpenAPI 的注意/處置股名單"""
    status = {"is_attention": False, "is_disposition": False, "details": ""}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        # 證交所 API
        twse_disp = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/TWT84U", headers=headers, timeout=5).json()
        twse_attn = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/TWTB4U", headers=headers, timeout=5).json()
        # 櫃買中心 API
        tpex_disp = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_disposition_securities", headers=headers, timeout=5).json()
        tpex_attn = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_attention_securities", headers=headers, timeout=5).json()

        # 檢查證交所
        for item in twse_disp:
            if str(stock_code) == str(item.get('Code')):
                status["is_disposition"] = True
                status["details"] = f"處置條件：{item.get('Disposition_Condition', '詳見官網')}"
        for item in twse_attn:
            if str(stock_code) == str(item.get('Code')):
                status["is_attention"] = True

        # 檢查櫃買中心
        for item in tpex_disp:
            if str(stock_code) == str(item.get('SecuritiesCompanyCode')):
                status["is_disposition"] = True
                status["details"] = f"處置條件：{item.get('DispositionMeasures', '詳見官網')}"
        for item in tpex_attn:
            if str(stock_code) == str(item.get('SecuritiesCompanyCode')):
                status["is_attention"] = True

    except Exception:
        status["details"] = "無法連線至官方 API"
        
    return status

# ==========================================
# 📊 區塊 1：智慧 K 線主技術圖表
# ==========================================
st.subheader("📈 區塊 1：智慧 K 線主技術圖表")

clean_stock_id = "".join(filter(str.isdigit, stock_input))

with st.spinner("載入股價 K 線數據..."):
    df_price, final_ticker = fetch_smart_yfinance_data(stock_input, start_date, end_date)

if df_price.empty:
    st.error(f"❌ 找不到股票代號 '{stock_input}' 的價格數據。")
else:
    try:
        df_price = df_price.reset_index()
        if isinstance(df_price.columns, pd.MultiIndex):
            df_price.columns = [col[0] for col in df_price.columns]
        df_price.columns = [str(col).strip() for col in df_price.columns]
    except:
        pass

    if 'Date' not in df_price.columns:
        df_price.rename(columns={df_price.columns[0]: 'Date'}, inplace=True)
        
    st.success(f"✅ 成功載入 {final_ticker} 歷史技術數據！")
    
    fig1 = go.Figure()
    fig1.add_trace(go.Candlestick(
        x=df_price['Date'], open=df_price['Open'], high=df_price['High'], low=df_price['Low'], close=df_price['Close'],
        name='K線', increasing_line_color='#FF3333', decreasing_line_color='#00AA00'
    ))
    
    df_price['MA5'] = df_price['Close'].rolling(window=5).mean()
    df_price['MA20'] = df_price['Close'].rolling(window=20).mean()
    fig1.add_trace(go.Scatter(x=df_price['Date'], y=df_price['MA5'], name='5MA', line=dict(color='#FFD700', width=1.5)))
    fig1.add_trace(go.Scatter(x=df_price['Date'], y=df_price['MA20'], name='20MA', line=dict(color='#00BFFF', width=1.5)))
    
    fig1.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, hovermode="x unified")
    st.plotly_chart(fig1, width='stretch')


# ==========================================
# 💎 擴充區塊：基本資料擴充、籌碼浮額與官方處置警示
# ==========================================
st.markdown("---")
st.markdown("## 🔍 核心雷達：股東會、浮額診斷與官方處置監控")

if not finmind_token:
    st.info("💡 提示：請在左側面板輸入您的免費 FinMind Token 即可載入籌碼數據。")
else:
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    with st.spinner("🔍 正在安全調閱股權分布與資券法人數據..."):
        df_share = fetch_finmind_dataset("shareholding", clean_stock_id, start_str, end_str, finmind_token)
        df_margin = fetch_finmind_dataset("margin", clean_stock_id, start_str, end_str, finmind_token)
        df_inst = fetch_finmind_dataset("institutional", clean_stock_id, start_str, end_str, finmind_token)

    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        st.markdown("### 📅 股東會與重要日程")
        st.metric(label="預估下次股東大會/除權息區間", value="6 月 ~ 7 月中旬")

    with col_info2:
        st.markdown("### 🌊 流通籌碼與浮額診斷")
        if not df_share.empty:
            latest_share_date = df_share['date'].max()
            df_s_latest = df_share[df_share['date'] == latest_share_date]
            big_pct = df_s_latest[df_s_latest['HoldingSharesPer'] >= 1000]['percent'].sum()
            float_pct = 100 - big_pct
            
            st.metric(label="市場核心浮額比例 (非大戶持股)", value=f"{float_pct:.2f} %")
            if float_pct > 60:
                st.error("⚠️ 警告：籌碼極度分散！")
            elif float_pct > 40:
                st.warning("⚖️ 提示：籌碼結構中性。")
            else:
                st.success("💎 安全：籌碼高度集中！")
        else:
            st.caption("⚠️ 無數據")

    # 🟢 亮點 1：串接官方 OpenAPI 的處置與注意股監控
    with col_info3:
        st.markdown("### 🚨 證交所/櫃買 官方狀態監控")
        with st.spinner("查詢官方名單中..."):
            official_status = check_official_warning_status(clean_stock_id)
            
        if official_status["is_disposition"]:
            st.error(f"🛑 **【處置股】**\n\n此檔股票目前已被官方列為處置有價證券！\n\n{official_status['details']}")
        elif official_status["is_attention"]:
            st.warning("⚠️ **【注意股】**\n\n此檔股票目前被官方列為注意有價證券，請留意波動風險。")
        else:
            st.success("✅ **【狀態安全】**\n\n目前未被列入官方注意或處置名單。")


    # ==========================================
    # ⚔️ 法人進出戰報表 & 融資融券明細表
    # ==========================================
    st.markdown("---")
    st.markdown("## 📊 籌碼數據表：法人與資券明細")
    
    col_table1, col_table2 = st.columns([1, 1.2])

    with col_table1:
        if not df_inst.empty:
            df_inst['Net_Shares'] = (df_inst['buy'] - df_inst['sell']) / 1000
            df_valid_inst = df_inst[(df_inst['buy'] > 0) | (df_inst['sell'] > 0)]
            latest_inst_date = df_valid_inst['date'].max() if not df_valid_inst.empty else df_inst['date'].max()
                
            st.markdown(f"**三大法人最新交易日 ({latest_inst_date}) 進出**")
            df_table = df_inst[df_inst['date'] == latest_inst_date].copy()
            inst_summary = []
            for name_key in ['外資', '投信', '自營商']:
                sub_df = df_table[df_table['name'].str.contains(name_key, case=False, na=False)]
                buy_val = sub_df['buy'].sum() / 1000
                sell_val = sub_df['sell'].sum() / 1000
                net_val = buy_val - sell_val
                inst_summary.append({
                    "機構": name_key,
                    "買進": int(round(buy_val, 0)),
                    "賣出": int(round(sell_val, 0)),
                    "淨買賣超": int(round(net_val, 0))
                })
            
            st.dataframe(pd.DataFrame(inst_summary).style.format({
                "買進": "{:,}", "賣出": "{:,}", "淨買賣超": "{:,}"
            }), use_container_width=True)

    # 🟢 亮點 2：新增融資券數據明細表 (近 10 個交易日)
    with col_table2:
        if not df_margin.empty:
            st.markdown("**近 10 日融資與融券變化表**")
            df_m_show = df_margin.sort_values('date', ascending=False).head(10).copy()
            
            # 動態匹配欄位確保不出錯
            cols_to_show = ['date']
            col_names = ['日期']
            
            if 'MarginPurchaseTodayBalance' in df_m_show.columns:
                cols_to_show.extend(['MarginPurchaseBuy', 'MarginPurchaseSell', 'MarginPurchaseTodayBalance'])
                col_names.extend(['融資買進', '融資賣出', '融資餘額'])
                
            if 'ShortSaleTodayBalance' in df_m_show.columns:
                cols_to_show.extend(['ShortSaleBuy', 'ShortSaleSell', 'ShortSaleTodayBalance'])
                col_names.extend(['融券買進', '融券賣出', '融券餘額'])
                
            df_m_show = df_m_show[cols_to_show]
            df_m_show.columns = col_names
            
            format_dict = {col: "{:,.0f}" for col in col_names if col != '日期'}
            st.dataframe(df_m_show.style.format(format_dict), use_container_width=True)


    # ==========================================
    # 📈 區塊 4：三大法人 + 融券動態雷達
    # ==========================================
    if not df_inst.empty:
        st.markdown(f"### 📈 區塊 4：三大法人與空方動態連動雷達")


        # 整理法人資料，避免 df_inst[df_inst 這類未完成語法造成 SyntaxError
        df_inst_chart = df_inst.copy()
        df_inst_chart['date'] = pd.to_datetime(df_inst_chart['date'])
        df_inst_chart['name'] = df_inst_chart['name'].astype(str)

        if 'Net_Shares' not in df_inst_chart.columns:
            df_inst_chart['Net_Shares'] = (df_inst_chart['buy'] - df_inst_chart['sell']) / 1000

        def summarize_inst(pattern):
            sub = df_inst_chart[df_inst_chart['name'].str.contains(pattern, case=False, na=False, regex=True)]
            if sub.empty:
                return pd.DataFrame(columns=['date', 'Net_Shares'])
            return sub.groupby('date', as_index=False)['Net_Shares'].sum().sort_values('date')

        df_foreign = summarize_inst('外資|Foreign')
        df_trust = summarize_inst('投信|Investment Trust')
        df_dealer = summarize_inst('自營商|Dealer')

        fig4 = make_subplots(specs=[[{"secondary_y": True}]])

        if not df_foreign.empty:
            fig4.add_trace(
                go.Bar(x=df_foreign['date'], y=df_foreign['Net_Shares'], name='外資淨買賣超'),
                secondary_y=False
            )

        if not df_trust.empty:
            fig4.add_trace(
                go.Bar(x=df_trust['date'], y=df_trust['Net_Shares'], name='投信淨買賣超'),
                secondary_y=False
            )

        if not df_dealer.empty:
            fig4.add_trace(
                go.Bar(x=df_dealer['date'], y=df_dealer['Net_Shares'], name='自營商淨買賣超'),
                secondary_y=False
            )

        if not df_margin.empty and 'ShortSaleTodayBalance' in df_margin.columns:
            df_short = df_margin.copy()
            df_short['date'] = pd.to_datetime(df_short['date'])
            df_short = df_short.sort_values('date')
            fig4.add_trace(
                go.Scatter(
                    x=df_short['date'],
                    y=df_short['ShortSaleTodayBalance'],
                    mode='lines+markers',
                    name='融券餘額'
                ),
                secondary_y=True
            )

        fig4.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig4.update_yaxes(title_text="法人淨買賣超（張）", secondary_y=False)
        fig4.update_yaxes(title_text="融券餘額", secondary_y=True)

        st.plotly_chart(fig4, use_container_width=True)

        st.caption("註：法人買賣單位已由股數換算為張；融券餘額依 FinMind 原始欄位顯示。")

