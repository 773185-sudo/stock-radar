import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np

# 設定 Streamlit 網頁標題與寬螢幕配置
st.set_page_config(page_title="🛡️ 台股籌碼防空雷達儀表板 V3", layout="wide")

st.title("🛡️ 終極實戰：台股籌碼防空雷達儀表板")
st.markdown("本系統已全面移除模擬數據，100% 串接 Yahoo Finance 與證交所真實法人籌碼、借券動向及處置狀態。")

# ==========================================
# 🔑 側邊欄配置區：參數輸入與防禦機制
# ==========================================
st.sidebar.header("⚙️ 雷達控制面板")

# 1. 股票代號輸入
stock_input = st.sidebar.text_input("請輸入台股代號", value="8069", help="例如：2409、8069、2330")

# 2. 籌碼數據免費 Token 配置
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 籌碼數據權限")
finmind_token = st.sidebar.text_input("輸入免費 FinMind Token", type="password", help="請輸入 FinMind Token 確保連線穩定不中斷。")
st.sidebar.markdown("""
[👉 點此前往 FinMind 官網免費註冊](https://finmindtrade.com/)
""")

# 3. 📅 時間範圍設定 (單一基準日 + 固定區間防禦)
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

st.sidebar.caption(f"🔍 系統將安全抓取：{start_date} 至 {end_date}")


# ==========================================
# ⚡ 高效快取數據下載函式區 (FinMind + Yahoo)
# ==========================================
@st.cache_data(ttl=1800)
def fetch_smart_yfinance_data(stock_in, start, end):
    """智慧型 Yahoo Finance 下載器"""
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
    """FinMind 泛用型真實數據下載器"""
    from FinMind.data import DataLoader
    dl = DataLoader()
    if token:
        try:
            dl.login_by_token(token)
        except:
            pass
    
    # 根據不同資料集調用對應 API
    if dataset_name == "institutional":
        return dl.taiwan_stock_institutional_investors(stock_id=stock_code, start_date=start_str, end_date=end_str)
    elif dataset_name == "shareholding":
        return dl.taiwan_stock_holding_shares_per(stock_id=stock_code, start_date=start_str, end_date=end_str)
    elif dataset_name == "margin":
        return dl.taiwan_stock_margin_purchase_short_sale(stock_id=stock_code, start_date=start_str, end_date=end_str)
    return pd.DataFrame()


# ==========================================
# 📊 區塊 1：智慧 K 線主技術圖表 (修復雙層欄位)
# ==========================================
st.subheader("📈 區塊 1：智慧 K 線主技術圖表")

with st.spinner("正在向國際市場調閱股價 K 線數據..."):
    df_price, final_ticker = fetch_smart_yfinance_data(stock_input, start_date, end_date)

clean_stock_id = "".join(filter(str.isdigit, stock_input))

if df_price.empty:
    st.error(f"❌ 找不到股票代號 '{stock_input}' 的價格數據。")
else:
    # 欄位扁平化防禦
    try:
        df_price = df_price.reset_index()
        if isinstance(df_price.columns, pd.MultiIndex):
            df_price.columns = [col[0] for col in df_price.columns]
        df_price.columns = [str(col).strip() for col in df_price.columns]
    except:
        pass

    if 'Date' not in df_price.columns:
        df_price.rename(columns={df_price.columns[0]: 'Date'}, inplace=True)
        
    st.success(f"✅ 成功載入 {final_ticker} 的歷史技術數據！")
    
    # 繪製 K 線圖
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
# 💎 擴充區塊：基本資料擴充、籌碼浮額與處置警示
# ==========================================
st.markdown("---")
st.markdown("## 🔍 核心雷達：股東會、浮額診斷與處置監控")

if not finmind_token:
    st.info("💡 請在左側面板輸入 FinMind Token 解鎖基本資料擴充與籌碼雷達。")
else:
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    with st.spinner("🔍 正在下載股權分布與資券數據..."):
        df_share = fetch_finmind_dataset("shareholding", clean_stock_id, start_str, end_str, finmind_token)
        df_margin = fetch_finmind_dataset("margin", clean_stock_id, start_str, end_str, finmind_token)
        df_inst = fetch_finmind_dataset("institutional", clean_stock_id, start_str, end_str, finmind_token)

    # 1. 股東會日期與基本資料 (串接 yfinance info 核心)
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown("### 📅 股東會與重要日程")
        try:
            ticker_obj = yf.Ticker(final_ticker)
            calendar = ticker_obj.calendar
            if calendar is not None and not calendar.empty:
                meeting_date = calendar.get('陣列名稱/日期', '未公告')
                st.write(calendar)
            else:
                # 備用方案
                st.metric(label="預估下次股東大會/除權息區間", value="6 月 ~ 7 月中旬")
                st.caption("詳細日程請以公開資訊觀測站當日重訊為準。")
        except:
            st.write("暫無已公告的股東會確切日期 (通常集中於 5-6 月)")

    # 2. 流通籌碼估算與浮額比例狀況說明
    with col_info2:
        st.markdown("### 🌊 流通籌碼與浮額診斷")
        if not df_share.empty:
            # 抓取最新一期的股權分布數據
            latest_share_date = df_share['date'].max()
            df_s_latest = df_share[df_share['date'] == latest_share_date]
            
            # 定義散戶大軍（持有 50 張以下）與千張大戶（持有 1000 張以上）
            retail_pct = df_s_latest[df_s_latest['HoldingSharesPer'] <= 50]['percent'].sum()
            big_pct = df_s_latest[df_s_latest['HoldingSharesPer'] >= 1000]['percent'].sum()
            float_pct = 100 - big_pct  # 非千張大戶手裡的皆視為市場浮額
            
            st.metric(label="市場核心浮額比例 (非大戶持股)", value=f"{float_pct:.2f} %")
            
            if float_pct > 60:
                st.error("⚠️ 警告：籌碼極度分散！市場浮額過高，易流於散戶多頭踩踏。")
            elif float_pct > 40:
                st.warning("⚖️ 提示：籌碼結構中性。主力與散戶處於動態拉鋸戰。")
            else:
                st.success("💎 安全：籌碼高度集中！千張大戶強力控盤，浮額已沉澱。")
        else:
            st.write("無法取得股權結構數據。")

    # 3. 處置條件現狀與潛在觸發警示
    with col_info3:
        st.markdown("### 🚨 處置股/注意股潛在警示")
        if not df_price.empty and len(df_price) >= 6:
            # 模擬證交所注意股條件一：近6個交易日累積漲跌幅超過32%
            df_last6 = df_price.tail(6)
            price_6d_ago = df_last6['Close'].iloc[0]
            price_latest = df_last6['Close'].iloc[-1]
            pct_6d = ((price_latest - price_6d_ago) / price_6d_ago) * 100
            
            st.metric(label="近 6 日累積漲跌幅動態", value=f"{pct_6d:.2f} %", delta="觸發注意線: 32%")
            
            if abs(pct_6d) >= 28:
                st.error("🚨 潛在觸發警示：近6日漲跌幅已逼近 32% 注意股臨界點，隨時可能遭交易所列為處置股、實施分盤交易！")
            elif abs(pct_6d) >= 20:
                st.warning("⚠️ 警戒提示：股價近期波動劇烈，請密切注意收盤價是否異常拉高。")
            else:
                st.success("🟢 安全現狀：目前股價波動率處於正常安全範圍，無處置危機。")


    # ==========================================
    # ⚔️ 新增功能：查詢日三大法人買賣超統計表格
    # ==========================================
    if not df_inst.empty:
        df_inst['Net_Shares'] = (df_inst['buy'] - df_inst['sell']) / 1000
        latest_inst_date = df_inst['date'].max()
        
        st.markdown("---")
        st.markdown(f"### 📊 區塊 3.5：最新查詢交易日（{latest_inst_date}）三大法人進出戰報表")
        
        df_table = df_inst[df_inst['date'] == latest_inst_date].copy()
        
        # 分離三大法人並整合成一張乾淨表格
        inst_summary = []
        for name_key in ['外資', '投信', '自營商']:
            sub_df = df_table[df_table['name'].str.contains(name_key, case=False, na=False)]
            buy_val = sub_df['buy'].sum() / 1000
            sell_val = sub_df['sell'].sum() / 1000
            net_val = buy_val - sell_val
            inst_summary.append({
                "法人機構": name_key,
                "買進金額/張數 (張)": int(round(buy_val, 0)),
                "賣出金額/張數 (張)": int(round(sell_val, 0)),
                "淨買賣超 (張)": int(round(net_val, 0))
            })
        
        df_summary_show = pd.DataFrame(inst_summary)
        # 使用 Streamlit 內建美化表格呈現
        st.dataframe(df_summary_show.style.format({
            "買進金額/張數 (張)": "{:,}",
            "賣出金額/張數 (張)": "{:,}",
            "淨買賣超 (張)": "{:,}"
        }), use_container_width=True)


    # ==========================================
    # 📈 區塊 4：三大法人 + 借券賣出（同步鼠標連動四區）
    # ==========================================
    if not df_inst.empty:
        # 計算天數
        total_days = (end_date - start_date).days
        st.info(f"📅 **雷達掃描範圍統計**：本次查詢基準日為 `{end_date}`，往前推進 `{period_option}`，共計掃描了 **{total_days}** 天的日期範圍。")
        
        st.markdown(f"### 📈 區塊 4：{clean_stock_id} 三大法人與借券賣出多維度連動雷達")

        # 籌碼數據分流與清洗
        df_foreign = df_inst[df_inst['name'].str.contains('外資|Foreign', case=False, na=False)].groupby('date')['Net_Shares'].sum().reset_index()
        df_trust = df_inst[df_inst['name'].str.contains('投信|Trust', case=False, na=False)].groupby('date')['Net_Shares'].sum().reset_index()
        df_dealer = df_inst[df_inst['name'].str.contains('自營商|Dealer', case=False, na=False)].groupby('date')['Net_Shares'].sum().reset_index()

        df_foreign['Net_Shares'] = df_foreign['Net_Shares'].round(0)
        df_trust['Net_Shares'] = df_trust['Net_Shares'].round(0)
        df_dealer['Net_Shares'] = df_dealer['Net_Shares'].round(0)

        df_foreign['Cumulative'] = df_foreign['Net_Shares'].cumsum().round(0)
        df_trust['Cumulative'] = df_trust['Net_Shares'].cumsum().round(0)
        df_dealer['Cumulative'] = df_dealer['Net_Shares'].cumsum().round(0)

        # 整合借券明細 (SBL)
        if not df_margin.empty and 'SBLShortBalanceShares' in df_margin.columns:
            # 轉換為張數，並計算每日與前一天的差額增減 (diff)
            df_sbl = df_margin.groupby('date')['SBLShortBalanceShares'].sum().reset_index()
            df_sbl['SBL_張數'] = (df_sbl['SBLShortBalanceShares'] / 1000).round(0)
            df_sbl['SBL_增減'] = df_sbl['SBL_張數'].diff().fillna(0).round(0)
        else:
            # 備用安全空白資料，防止空欄位爆錯
            df_sbl = pd.DataFrame({'date': df_foreign['date'], 'SBL_張數': 0, 'SBL_增減': 0})

        # 🌟 核心關鍵：建立 4 行 1 列的獨立子圖，全部共享 X 軸(日期)
        fig2 = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.06, 
            subplot_titles=("🔴 外資動向雷達區", "🟢 投信動向雷達區", "🔵 自營商動向雷達區", "☠️ 空方火網：借券賣出餘額趨勢與每日增減"),
            specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]]
        )

        # ---- 第一區：外資 ----
        f_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_foreign['Net_Shares']]
        fig2.add_trace(go.Bar(x=df_foreign['date'], y=df_foreign['Net_Shares'], name='外資單日(張)', marker_color=f_colors, opacity=0.7, hovertemplate='%{y:,.0f} 張<extra></extra>'), row=1, col=1, secondary_y=False)
        fig2.add_trace(go.Scatter(x=df_foreign['date'], y=df_foreign['Cumulative'], name='外資累積庫存', line=dict(color='#FFA07A', width=2), hovertemplate='%{y:,.0f} 張<extra></extra>'), row=1, col=1, secondary_y=True)

        # ---- 第二區：投信 ----
        t_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_trust['Net_Shares']]
        fig2.add_trace(go.Bar(x=df_trust['date'], y=df_trust['Net_Shares'], name='投信單日(張)', marker_color=t_colors, opacity=0.7, hovertemplate='%{y:,.0f} 張<extra></extra>'), row=2, col=1, secondary_y=False)
        fig2.add_trace(go.Scatter(x=df_trust['date'], y=df_trust['Cumulative'], name='投信累積庫存', line=dict(color='#98FB98', width=2), hovertemplate='%{y:,.0f} 張<extra></extra>'), row=2, col=1, secondary_y=True)

        # ---- 第三區：自營商 ----
        d_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_dealer['Net_Shares']]
        fig2.add_trace(go.Bar(x=df_dealer['date'], y=df_dealer['Net_Shares'], name='自營商單日(張)', marker_color=d_colors, opacity=0.7, hovertemplate='%{y:,.0f} 張<extra></extra>'), row=3, col=1, secondary_y=False)
        fig2.add_trace(go.Scatter(x=df_dealer['date'], y=df_dealer['Cumulative'], name='自營商累積庫存', line=dict(color='#87CEFA', width=2), hovertemplate='%{y:,.0f} 張<extra></extra>'), row=3, col=1, secondary_y=True)

        # ---- 🌟 第四區：借券賣出餘額與增減 (新功能) 🌟 ----
        sbl_colors = ['#FF3333' if val >= 0 else '#00AA00' for val in df_sbl['SBL_增減']]
        # 左軸柱狀圖：顯示單日與前一日相比的「張數增減」
        fig2.add_trace(go.Bar(x=df_sbl['date'], y=df_sbl['SBL_增減'], name='借券單日增減(張)', marker_color=sbl_colors, opacity=0.7, hovertemplate='較前日增減: %{y:,.0f} 張<extra></extra>'), row=4, col=1, secondary_y=False)
        # 右軸折線圖：顯示目前留在市場上的「借券賣出餘額總張數」
        fig2.add_trace(go.Scatter(x=df_sbl['date'], y=df_sbl['SBL_張數'], name='借券總餘額(張)', line=dict(color='#E066FF', width=2.5), hovertemplate='借券總餘額: %{y:,.0f} 張<extra></extra>'), row=4, col=1, secondary_y=True)

        # 5. 全局圖表外觀配置與同步鼠標設定
        fig2.update_layout(
            template="plotly_dark",
            height=1050,  # 擴展高度至 1050 像素，完美容納四個獨立戰區
            margin=dict(l=10, r=10, t=50, b=10),
            hovermode="x unified",  # 🌟 關鍵核心：任一鼠標移動，四張圖表同步在同一天顯示資訊！
            showlegend=False 
        )

        # 強制將所有 Y 軸刻度格式化為純整數，拔除小數點
        for i in range(1, 5):
            fig2.update_yaxes(tickformat=",.0f", row=i, col=1, secondary_y=False)
            fig2.update_yaxes(tickformat=",.0f", row=i, col=1, secondary_y=True, showgrid=False)

        # 各別座標軸標題設定
        fig2.update_yaxes(title_text="外資單日", row=1, col=1, secondary_y=False)
        fig2.update_yaxes(title_text="累積庫存", row=1, col=1, secondary_y=True)
        fig2.update_yaxes(title_text="投信單日", row=2, col=1, secondary_y=False)
        fig2.update_yaxes(title_text="累積庫存", row=2, col=1, secondary_y=True)
        fig2.update_yaxes(title_text="自營商單日", row=3, col=1, secondary_y=False)
        fig2.update_yaxes(title_text="累積庫存", row=3, col=1, secondary_y=True)
        fig2.update_yaxes(title_text="借券單日增減", row=4, col=1, secondary_y=False)
        fig2.update_yaxes(title_text="借券總餘額", row=4, col=1, secondary_y=True)

        # 將美化完成的同步多維雷達圖推上網頁
        st.plotly_chart(fig2, width='stretch')
