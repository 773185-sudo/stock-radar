import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests

# ==========================================
# 1. 網頁基本配置
# ==========================================
st.set_page_config(
    page_title="台股終極籌碼防空雷達",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📡 台股終極籌碼與 K 線防空雷達")
st.markdown(
    "整合 Yahoo Finance 歷史 K 線、成交量、FinMind 法人籌碼、融資融券，以及證交所/櫃買中心官方注意與處置股監控。"
)
st.markdown("---")

# ==========================================
# 2. 側邊欄參數輸入區
# ==========================================
st.sidebar.header("⚙️ 雷達控制面板")

stock_input = st.sidebar.text_input(
    "請輸入台股 4 碼股票代號",
    value="8069",
    help="例如：2330、2409、3481、8069"
).strip()

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 籌碼數據權限")
finmind_token = st.sidebar.text_input(
    "FinMind Token",
    type="password",
    help="若要載入法人、融資融券、股權分布資料，請輸入 FinMind Token。"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 時間範圍設定")

today = datetime.date.today()

period_option = st.sidebar.selectbox(
    "快速選擇顯示區間",
    ["自訂", "1 個月", "3 個月", "半年", "1 年", "2 年"],
    index=3
)

default_end_date = today

if period_option == "1 個月":
    default_start_date = default_end_date - datetime.timedelta(days=30)
elif period_option == "3 個月":
    default_start_date = default_end_date - datetime.timedelta(days=90)
elif period_option == "半年":
    default_start_date = default_end_date - datetime.timedelta(days=182)
elif period_option == "1 年":
    default_start_date = default_end_date - datetime.timedelta(days=365)
elif period_option == "2 年":
    default_start_date = default_end_date - datetime.timedelta(days=365 * 2)
else:
    default_start_date = default_end_date - datetime.timedelta(days=90)

col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    start_date = st.date_input("起始日期", value=default_start_date)
with col_date2:
    end_date = st.date_input("結束日期", value=default_end_date)

run_scan = st.sidebar.button("🔥 啟動雷達掃描", use_container_width=True)

# ==========================================
# 3. 工具函式
# ==========================================
def clean_stock_code(stock_text: str) -> str:
    return "".join(filter(str.isdigit, str(stock_text)))


@st.cache_data(ttl=1800)
def fetch_yfinance_tw_stock(stock_code: str, start, end):
    """
    自動判斷上市 .TW 或上櫃 .TWO。
    先抓 .TW，若無資料再抓 .TWO。
    """
    stock_code = clean_stock_code(stock_code)

    if not stock_code:
        return pd.DataFrame(), ""

    # yfinance 的 end 通常是 exclusive，這裡多加一天，避免選今天卻抓不到今天以前資料。
    yf_end = end + datetime.timedelta(days=1)

    candidates = [f"{stock_code}.TW", f"{stock_code}.TWO"]

    for symbol in candidates:
        try:
            df = yf.download(
                symbol,
                start=start,
                end=yf_end,
                interval="1d",
                progress=False,
                auto_adjust=False
            )

            if df is not None and not df.empty:
                df = df.reset_index()

                # yfinance 某些版本會回傳 MultiIndex 欄位，這裡統一壓平。
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(col[0]).strip() for col in df.columns]
                else:
                    df.columns = [str(col).strip() for col in df.columns]

                if "Date" not in df.columns:
                    df.rename(columns={df.columns[0]: "Date"}, inplace=True)

                return df, symbol

        except Exception:
            continue

    return pd.DataFrame(), ""


@st.cache_data(ttl=1800)
def fetch_finmind_dataset(dataset_name, stock_code, start_str, end_str, token):
    try:
        from FinMind.data import DataLoader
    except Exception:
        return pd.DataFrame()

    dl = DataLoader()

    if token:
        try:
            dl.login_by_token(token)
        except Exception:
            pass

    try:
        if dataset_name == "institutional":
            return dl.taiwan_stock_institutional_investors(
                stock_id=stock_code,
                start_date=start_str,
                end_date=end_str
            )

        if dataset_name == "shareholding":
            return dl.taiwan_stock_holding_shares_per(
                stock_id=stock_code,
                start_date=start_str,
                end_date=end_str
            )

        if dataset_name == "margin":
            return dl.taiwan_stock_margin_purchase_short_sale(
                stock_id=stock_code,
                start_date=start_str,
                end_date=end_str
            )

    except Exception:
        return pd.DataFrame()

    return pd.DataFrame()


@st.cache_data(ttl=1800)
def check_official_warning_status(stock_code):
    """
    查詢證交所與櫃買中心 OpenAPI 的注意/處置股狀態。
    欄位名稱可能因官方 API 異動而變化，所以用多欄位 fallback。
    """
    status = {
        "is_attention": False,
        "is_disposition": False,
        "details": "",
        "source": []
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    urls = {
        "twse_disp": "https://openapi.twse.com.tw/v1/exchangeReport/TWT84U",
        "twse_attn": "https://openapi.twse.com.tw/v1/exchangeReport/TWTB4U",
        "tpex_disp": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_disposition_securities",
        "tpex_attn": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_attention_securities",
    }

    def safe_json(url):
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                return r.json()
        except Exception:
            return []
        return []

    def get_code(item):
        for key in [
            "Code",
            "SecuritiesCompanyCode",
            "SecuritiesCode",
            "股票代號",
            "有價證券代號",
            "代號"
        ]:
            if key in item:
                return str(item.get(key)).strip()
        return ""

    try:
        twse_disp = safe_json(urls["twse_disp"])
        twse_attn = safe_json(urls["twse_attn"])
        tpex_disp = safe_json(urls["tpex_disp"])
        tpex_attn = safe_json(urls["tpex_attn"])

        for item in twse_disp:
            if get_code(item) == str(stock_code):
                status["is_disposition"] = True
                status["source"].append("證交所處置")
                status["details"] = (
                    item.get("Disposition_Condition")
                    or item.get("處置條件")
                    or item.get("DispositionMeasures")
                    or "詳見官方公告"
                )

        for item in twse_attn:
            if get_code(item) == str(stock_code):
                status["is_attention"] = True
                status["source"].append("證交所注意")

        for item in tpex_disp:
            if get_code(item) == str(stock_code):
                status["is_disposition"] = True
                status["source"].append("櫃買中心處置")
                status["details"] = (
                    item.get("DispositionMeasures")
                    or item.get("處置條件")
                    or item.get("Disposition_Condition")
                    or "詳見官方公告"
                )

        for item in tpex_attn:
            if get_code(item) == str(stock_code):
                status["is_attention"] = True
                status["source"].append("櫃買中心注意")

    except Exception:
        status["details"] = "無法連線至官方 API"

    return status


def draw_price_volume_chart(df_k, stock_yahoo):
    """
    K 線 + 成交量 + MA5/MA20
    """
    df = df_k.copy()
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.72, 0.28]
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="日 K 線",
            increasing_line_color="#FF3333",
            decreasing_line_color="#00AA00"
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MA5"],
            name="MA5",
            line=dict(color="#FFD700", width=1.5)
        ),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MA20"],
            name="MA20",
            line=dict(color="#00BFFF", width=1.5)
        ),
        row=1,
        col=1
    )

    volume_colors = [
        "#FF3333" if close_price >= open_price else "#00AA00"
        for close_price, open_price in zip(df["Close"], df["Open"])
    ]

    fig.add_trace(
        go.Bar(
            x=df["Date"],
            y=df["Volume"],
            name="成交量",
            marker_color=volume_colors
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=f"<b>{stock_yahoo} K 線與成交量</b>",
        template="plotly_dark",
        height=650,
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    return fig


def summarize_inst_by_name(df_inst_chart, pattern):
    sub = df_inst_chart[df_inst_chart["name"].str.contains(pattern, case=False, na=False, regex=True)]

    if sub.empty:
        return pd.DataFrame(columns=["date", "Net_Shares"])

    return sub.groupby("date", as_index=False)["Net_Shares"].sum().sort_values("date")


def draw_institutional_margin_chart(df_inst, df_margin):
    """
    三大法人淨買賣超 + 融券餘額
    修正原本 df_foreign = df_inst[df_inst 的未完成語法。
    """
    df_inst_chart = df_inst.copy()
    df_inst_chart["date"] = pd.to_datetime(df_inst_chart["date"])
    df_inst_chart["name"] = df_inst_chart["name"].astype(str)

    if "Net_Shares" not in df_inst_chart.columns:
        df_inst_chart["Net_Shares"] = (df_inst_chart["buy"] - df_inst_chart["sell"]) / 1000

    df_foreign = summarize_inst_by_name(df_inst_chart, "外資|Foreign")
    df_trust = summarize_inst_by_name(df_inst_chart, "投信|Investment Trust")
    df_dealer = summarize_inst_by_name(df_inst_chart, "自營商|Dealer")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if not df_foreign.empty:
        fig.add_trace(
            go.Bar(x=df_foreign["date"], y=df_foreign["Net_Shares"], name="外資淨買賣超"),
            secondary_y=False
        )

    if not df_trust.empty:
        fig.add_trace(
            go.Bar(x=df_trust["date"], y=df_trust["Net_Shares"], name="投信淨買賣超"),
            secondary_y=False
        )

    if not df_dealer.empty:
        fig.add_trace(
            go.Bar(x=df_dealer["date"], y=df_dealer["Net_Shares"], name="自營商淨買賣超"),
            secondary_y=False
        )

    if df_margin is not None and not df_margin.empty and "ShortSaleTodayBalance" in df_margin.columns:
        df_short = df_margin.copy()
        df_short["date"] = pd.to_datetime(df_short["date"])
        df_short = df_short.sort_values("date")

        fig.add_trace(
            go.Scatter(
                x=df_short["date"],
                y=df_short["ShortSaleTodayBalance"],
                mode="lines+markers",
                name="融券餘額"
            ),
            secondary_y=True
        )

    fig.update_layout(
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="法人淨買賣超（張）", secondary_y=False)
    fig.update_yaxes(title_text="融券餘額", secondary_y=True)

    return fig


# ==========================================
# 4. 主畫面執行邏輯
# ==========================================
if not run_scan:
    st.info("請在左側輸入股票代號與日期範圍，然後按下「啟動雷達掃描」。")
    st.stop()

clean_stock_id = clean_stock_code(stock_input)

if not clean_stock_id:
    st.warning("⚠️ 請先輸入有效的台股 4 碼股票代號。")
    st.stop()

if start_date >= end_date:
    st.warning("⚠️ 起始日期必須早於結束日期。")
    st.stop()

# ==========================================
# 5. 區塊 1：K 線與成交量
# ==========================================
st.subheader("📈 區塊 1：K 線與成交量")

with st.spinner("載入 Yahoo Finance 歷史股價資料..."):
    df_price, final_ticker = fetch_yfinance_tw_stock(clean_stock_id, start_date, end_date)

if df_price.empty:
    st.error(f"❌ 查無股票代號 [{clean_stock_id}] 的 Yahoo Finance 歷史資料。請確認是否為上市櫃正常股票。")
    st.stop()

st.success(f"✅ 成功載入 {final_ticker} 歷史價格資料。")

fig_price = draw_price_volume_chart(df_price, final_ticker)
st.plotly_chart(fig_price, use_container_width=True)

latest_close = df_price["Close"].dropna().iloc[-1]
latest_volume = df_price["Volume"].dropna().iloc[-1]
latest_date = pd.to_datetime(df_price["Date"].iloc[-1]).date()

m1, m2, m3 = st.columns(3)
m1.metric("最新資料日", str(latest_date))
m2.metric("最新收盤價", f"{latest_close:,.2f}")
m3.metric("最新成交量", f"{latest_volume:,.0f}")

# ==========================================
# 6. FinMind 籌碼資料
# ==========================================
st.markdown("---")
st.markdown("## 🔍 核心雷達：股權分布、法人、資券與官方狀態")

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

df_share = pd.DataFrame()
df_margin = pd.DataFrame()
df_inst = pd.DataFrame()

if not finmind_token:
    st.info("💡 尚未輸入 FinMind Token，因此只顯示 K 線、成交量與官方注意/處置查詢。")
else:
    with st.spinner("載入 FinMind 籌碼資料..."):
        df_share = fetch_finmind_dataset("shareholding", clean_stock_id, start_str, end_str, finmind_token)
        df_margin = fetch_finmind_dataset("margin", clean_stock_id, start_str, end_str, finmind_token)
        df_inst = fetch_finmind_dataset("institutional", clean_stock_id, start_str, end_str, finmind_token)

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("### 📅 股東會與重要日程")
    st.metric(label="預估常見股東會/除權息區間", value="6 月 ~ 7 月")
    st.caption("此為一般台股常見區間提示，實際日期仍須查公司公告。")

with col_info2:
    st.markdown("### 🌊 流通籌碼與浮額診斷")

    if not df_share.empty and {"date", "HoldingSharesPer", "percent"}.issubset(df_share.columns):
        latest_share_date = df_share["date"].max()
        df_s_latest = df_share[df_share["date"] == latest_share_date]

        big_pct = df_s_latest[df_s_latest["HoldingSharesPer"] >= 1000]["percent"].sum()
        float_pct = 100 - big_pct

        st.metric(label="估算市場浮額比例", value=f"{float_pct:.2f} %")

        if float_pct > 60:
            st.error("⚠️ 籌碼偏分散")
        elif float_pct > 40:
            st.warning("⚖️ 籌碼結構中性")
        else:
            st.success("💎 籌碼相對集中")
    else:
        st.caption("尚無股權分布資料。")

with col_info3:
    st.markdown("### 🚨 官方注意/處置狀態")

    with st.spinner("查詢官方注意/處置名單..."):
        official_status = check_official_warning_status(clean_stock_id)

    if official_status["is_disposition"]:
        st.error(f"🛑 處置股\n\n{official_status['details']}")
        if official_status["source"]:
            st.caption("來源：" + "、".join(official_status["source"]))
    elif official_status["is_attention"]:
        st.warning("⚠️ 注意股\n\n目前被官方列為注意有價證券，請留意波動風險。")
        if official_status["source"]:
            st.caption("來源：" + "、".join(official_status["source"]))
    else:
        st.success("✅ 目前未列入官方注意或處置名單。")

# ==========================================
# 7. 法人與資券明細
# ==========================================
if finmind_token:
    st.markdown("---")
    st.markdown("## 📊 籌碼數據表：法人與資券明細")

    col_table1, col_table2 = st.columns([1, 1.25])

    with col_table1:
        st.markdown("### 三大法人最新交易日")

        if not df_inst.empty and {"date", "name", "buy", "sell"}.issubset(df_inst.columns):
            df_inst = df_inst.copy()
            df_inst["Net_Shares"] = (df_inst["buy"] - df_inst["sell"]) / 1000

            df_valid_inst = df_inst[(df_inst["buy"] > 0) | (df_inst["sell"] > 0)]
            latest_inst_date = df_valid_inst["date"].max() if not df_valid_inst.empty else df_inst["date"].max()

            st.markdown(f"**最新交易日：{latest_inst_date}**")

            df_table = df_inst[df_inst["date"] == latest_inst_date].copy()
            inst_summary = []

            for name_key, pattern in [
                ("外資", "外資|Foreign"),
                ("投信", "投信|Investment Trust"),
                ("自營商", "自營商|Dealer")
            ]:
                sub_df = df_table[df_table["name"].astype(str).str.contains(pattern, case=False, na=False, regex=True)]

                buy_val = sub_df["buy"].sum() / 1000
                sell_val = sub_df["sell"].sum() / 1000
                net_val = buy_val - sell_val

                inst_summary.append({
                    "機構": name_key,
                    "買進（張）": int(round(buy_val, 0)),
                    "賣出（張）": int(round(sell_val, 0)),
                    "淨買賣超（張）": int(round(net_val, 0))
                })

            st.dataframe(
                pd.DataFrame(inst_summary).style.format({
                    "買進（張）": "{:,}",
                    "賣出（張）": "{:,}",
                    "淨買賣超（張）": "{:,}"
                }),
                use_container_width=True
            )
        else:
            st.caption("尚無法人資料。")

    with col_table2:
        st.markdown("### 近 10 日融資融券變化")

        if not df_margin.empty:
            df_m_show = df_margin.sort_values("date", ascending=False).head(10).copy()

            cols_to_show = ["date"]
            col_names = ["日期"]

            if "MarginPurchaseTodayBalance" in df_m_show.columns:
                for c, n in [
                    ("MarginPurchaseBuy", "融資買進"),
                    ("MarginPurchaseSell", "融資賣出"),
                    ("MarginPurchaseTodayBalance", "融資餘額")
                ]:
                    if c in df_m_show.columns:
                        cols_to_show.append(c)
                        col_names.append(n)

            if "ShortSaleTodayBalance" in df_m_show.columns:
                for c, n in [
                    ("ShortSaleBuy", "融券買進"),
                    ("ShortSaleSell", "融券賣出"),
                    ("ShortSaleTodayBalance", "融券餘額")
                ]:
                    if c in df_m_show.columns:
                        cols_to_show.append(c)
                        col_names.append(n)

            df_m_show = df_m_show[cols_to_show]
            df_m_show.columns = col_names

            format_dict = {col: "{:,.0f}" for col in col_names if col != "日期"}
            st.dataframe(df_m_show.style.format(format_dict), use_container_width=True)
        else:
            st.caption("尚無融資融券資料。")

# ==========================================
# 8. 區塊 4：三大法人與空方動態連動雷達
# ==========================================
if finmind_token and not df_inst.empty:
    st.markdown("---")
    st.markdown("## 📈 區塊 4：三大法人與空方動態連動雷達")

    fig_inst = draw_institutional_margin_chart(df_inst, df_margin)
    st.plotly_chart(fig_inst, use_container_width=True)

    st.caption("註：法人買賣單位已由股數換算為張；融券餘額依 FinMind 原始欄位顯示。")

# ==========================================
# 9. 原始資料檢視
# ==========================================
with st.expander("🔎 展開查看原始資料"):
    st.markdown("### Yahoo Finance 股價資料")
    st.dataframe(df_price, use_container_width=True)

    if finmind_token:
        st.markdown("### FinMind 法人資料")
        st.dataframe(df_inst, use_container_width=True)

        st.markdown("### FinMind 融資融券資料")
        st.dataframe(df_margin, use_container_width=True)

        st.markdown("### FinMind 股權分布資料")
        st.dataframe(df_share, use_container_width=True)
