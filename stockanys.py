import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests
import numpy as np

# ============================================================
# 台股籌碼防空雷達 V2 Stable
# 功能：K線、漲跌、三大法人、融資融券、借券賣出餘額、基本資料股本
# 套件：pip install streamlit pandas yfinance plotly requests FinMind numpy
# 執行：streamlit run stockanys_v2_stable.py
# ============================================================

st.set_page_config(
    page_title="台股籌碼防空雷達 V2 Stable",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📡 台股籌碼防空雷達 V2 Stable")
st.caption("K線 / 漲跌 / 三大法人 / 融資融券 / 借券賣出餘額 / 基本資料股本")

# ============================================================
# 側邊欄
# ============================================================
st.sidebar.header("⚙️ 雷達控制面板")

stock_input = st.sidebar.text_input(
    "股票代號",
    value="8069",
    help="請輸入台股 4 碼股票代號，例如 2330、8069、6854"
).strip()

finmind_token = st.sidebar.text_input(
    "FinMind Token",
    value="",
    type="password",
    help="法人、資券、股權分布、借券資料建議輸入 FinMind Token。"
)

today = datetime.date.today()

period_option = st.sidebar.selectbox(
    "顯示區間",
    ["1個月", "3個月", "半年", "1年", "2年", "3年"],
    index=2
)

period_days = {
    "1個月": 31,
    "3個月": 93,
    "半年": 183,
    "1年": 366,
    "2年": 732,
    "3年": 1098
}[period_option]

default_start = today - datetime.timedelta(days=period_days)

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    start_date = st.date_input("起始日", value=default_start)
with col_s2:
    end_date = st.date_input("結束日", value=today)

k_period = st.sidebar.radio("K線週期", ["日K", "週K", "月K"], horizontal=True)
run_btn = st.sidebar.button("🔥 啟動掃描", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("穩定版先不做分點買賣超；分點資料通常需要另外資料源。")


# ============================================================
# 通用工具
# ============================================================
def clean_stock_code(text: str) -> str:
    return "".join(filter(str.isdigit, str(text)))


def fmt_num(x, decimals=0):
    try:
        if pd.isna(x):
            return "-"
        return f"{float(x):,.{decimals}f}"
    except Exception:
        return "-"


def fmt_pct(x, decimals=2):
    try:
        if pd.isna(x):
            return "-"
        return f"{float(x):,.{decimals}f}%"
    except Exception:
        return "-"


def get_first_existing_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def normalize_date_col(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    elif "日期" in df.columns:
        df["date"] = pd.to_datetime(df["日期"], errors="coerce")
    return df


def safe_to_numeric(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ============================================================
# Yahoo Finance：上市 / 上櫃自動判斷
# ============================================================
@st.cache_data(ttl=1800)
def fetch_yfinance_price(stock_code: str, start_date, end_date):
    stock_code = clean_stock_code(stock_code)
    if not stock_code:
        return pd.DataFrame(), ""

    yf_end = end_date + datetime.timedelta(days=1)
    candidates = [f"{stock_code}.TW", f"{stock_code}.TWO"]

    for ticker in candidates:
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=yf_end,
                interval="1d",
                progress=False,
                auto_adjust=False
            )
            if df is not None and not df.empty:
                df = df.reset_index()

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [str(c[0]).strip() for c in df.columns]
                else:
                    df.columns = [str(c).strip() for c in df.columns]

                if "Date" not in df.columns:
                    df.rename(columns={df.columns[0]: "Date"}, inplace=True)

                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df.dropna(subset=["Date"])
                df = safe_to_numeric(df, ["Open", "High", "Low", "Close", "Adj Close", "Volume"])
                return df, ticker
        except Exception:
            pass

    return pd.DataFrame(), ""


def resample_ohlcv(df, mode):
    df = df.copy()

    if mode == "日K":
        out = df.copy()
    else:
        df = df.set_index("Date").sort_index()
        rule = "W-FRI" if mode == "週K" else "ME"
        agg = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }
        if "Adj Close" in df.columns:
            agg["Adj Close"] = "last"

        out = df.resample(rule).agg(agg).dropna(subset=["Open", "High", "Low", "Close"]).reset_index()

    for ma in [5, 10, 20, 60, 120, 240]:
        out[f"MA{ma}"] = out["Close"].rolling(ma).mean()

    return out


def compute_price_summary(df_daily):
    df = df_daily.copy().sort_values("Date").dropna(subset=["Close"])
    if df.empty:
        return {}

    latest = df.iloc[-1]
    prev_close = None

    if len(df) >= 2:
        prev_close = float(df.iloc[-2]["Close"])

    close = float(latest["Close"])
    change = close - prev_close if prev_close is not None else np.nan
    change_pct = (change / prev_close * 100) if prev_close not in [None, 0] else np.nan

    return {
        "date": latest["Date"],
        "open": float(latest.get("Open", np.nan)),
        "high": float(latest.get("High", np.nan)),
        "low": float(latest.get("Low", np.nan)),
        "close": close,
        "volume": float(latest.get("Volume", np.nan)),
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct
    }


# ============================================================
# FinMind 資料
# ============================================================
def finmind_dataloader_login(token):
    try:
        from FinMind.data import DataLoader
        dl = DataLoader()
        if token:
            try:
                dl.login_by_token(token)
            except Exception:
                pass
        return dl
    except Exception:
        return None


@st.cache_data(ttl=1800)
def fetch_finmind_institutional(stock_code, start_str, end_str, token):
    dl = finmind_dataloader_login(token)
    if dl is None:
        return pd.DataFrame()
    try:
        df = dl.taiwan_stock_institutional_investors(
            stock_id=stock_code,
            start_date=start_str,
            end_date=end_str
        )
        return normalize_date_col(df)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_finmind_margin(stock_code, start_str, end_str, token):
    dl = finmind_dataloader_login(token)
    if dl is None:
        return pd.DataFrame()
    try:
        df = dl.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_code,
            start_date=start_str,
            end_date=end_str
        )
        return normalize_date_col(df)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_finmind_shareholding(stock_code, start_str, end_str, token):
    dl = finmind_dataloader_login(token)
    if dl is None:
        return pd.DataFrame()
    try:
        df = dl.taiwan_stock_holding_shares_per(
            stock_id=stock_code,
            start_date=start_str,
            end_date=end_str
        )
        return normalize_date_col(df)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def fetch_finmind_basic_info(stock_code, token):
    params = {
        "dataset": "TaiwanStockInfo",
        "data_id": stock_code
    }
    if token:
        params["token"] = token

    try:
        r = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, timeout=10)
        js = r.json()
        data = js.get("data", [])
        df = pd.DataFrame(data)
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}


@st.cache_data(ttl=1800)
def fetch_finmind_securities_lending(stock_code, start_str, end_str, token):
    """
    借券賣出餘額。
    FinMind 資料集或 DataLoader 方法名稱可能因版本不同而不同，
    所以這裡用多重候選抓法，抓不到時畫面會顯示提示，不會中斷。
    """
    dl = finmind_dataloader_login(token)

    if dl is not None:
        method_candidates = [
            "taiwan_stock_securities_lending",
            "taiwan_stock_securities_lending_sbl",
            "taiwan_stock_borrow_sell",
        ]

        for method_name in method_candidates:
            try:
                if hasattr(dl, method_name):
                    func = getattr(dl, method_name)
                    df = func(stock_id=stock_code, start_date=start_str, end_date=end_str)
                    if df is not None and not df.empty:
                        return normalize_date_col(df)
            except Exception:
                pass

    dataset_candidates = [
        "TaiwanStockSecuritiesLending",
        "TaiwanStockSecuritiesLendingSBL",
        "TaiwanStockBorrowSell",
        "TaiwanStockTotalSecuritiesLending",
    ]

    for dataset in dataset_candidates:
        try:
            params = {
                "dataset": dataset,
                "data_id": stock_code,
                "start_date": start_str,
                "end_date": end_str
            }
            if token:
                params["token"] = token

            r = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, timeout=12)
            js = r.json()
            data = js.get("data", [])
            df = pd.DataFrame(data)

            if not df.empty:
                df["source_dataset"] = dataset
                return normalize_date_col(df)
        except Exception:
            pass

    return pd.DataFrame()


# ============================================================
# 官方 OpenAPI：基本資料 / 注意處置
# ============================================================
@st.cache_data(ttl=3600)
def fetch_twse_tpex_basic_info(stock_code):
    result = {
        "stock_id": stock_code,
        "stock_name": "",
        "market": "",
        "industry": "",
        "capital": "",
        "listing_date": "",
        "source": ""
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    api_list = [
        ("TWSE公司基本資料", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"),
        ("TPEX公司基本資料", "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_company_info"),
    ]

    def pick(item, keys):
        for k in keys:
            if k in item and str(item.get(k)).strip():
                return str(item.get(k)).strip()
        return ""

    for source, url in api_list:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue

            data = r.json()
            if not isinstance(data, list):
                continue

            for item in data:
                code = pick(item, ["Code", "SecuritiesCompanyCode", "公司代號", "股票代號", "有價證券代號"])

                if code == stock_code:
                    result["stock_name"] = pick(item, ["Name", "公司名稱", "簡稱", "有價證券名稱", "SecuritiesCompanyName"])
                    result["market"] = "上市" if "TWSE" in source else "上櫃"
                    result["industry"] = pick(item, ["產業別", "Industry", "產業名稱"])
                    result["capital"] = pick(item, ["實收資本額", "實收資本額(元)", "Capital", "股本"])
                    result["listing_date"] = pick(item, ["上市日期", "上櫃日期", "掛牌日期", "ListingDate"])
                    result["source"] = source
                    return result
        except Exception:
            pass

    return result


@st.cache_data(ttl=1800)
def check_official_warning_status(stock_code):
    status = {
        "is_attention": False,
        "is_disposition": False,
        "details": "",
        "source": []
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    urls = {
        "證交所處置": "https://openapi.twse.com.tw/v1/exchangeReport/TWT84U",
        "證交所注意": "https://openapi.twse.com.tw/v1/exchangeReport/TWTB4U",
        "櫃買處置": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_disposition_securities",
        "櫃買注意": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_attention_securities",
    }

    def get_code(item):
        for key in ["Code", "SecuritiesCompanyCode", "SecuritiesCode", "股票代號", "有價證券代號", "代號"]:
            if key in item:
                return str(item.get(key)).strip()
        return ""

    for label, url in urls.items():
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                continue

            data = r.json()
            if not isinstance(data, list):
                continue

            for item in data:
                if get_code(item) == stock_code:
                    status["source"].append(label)

                    if "處置" in label:
                        status["is_disposition"] = True
                        status["details"] = (
                            item.get("Disposition_Condition")
                            or item.get("DispositionMeasures")
                            or item.get("處置條件")
                            or "詳見官方公告"
                        )
                    elif "注意" in label:
                        status["is_attention"] = True
        except Exception:
            pass

    return status


# ============================================================
# 圖表函式
# ============================================================
def draw_kline_chart(df_k, ticker, k_period):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.72, 0.28]
    )

    fig.add_trace(
        go.Candlestick(
            x=df_k["Date"],
            open=df_k["Open"],
            high=df_k["High"],
            low=df_k["Low"],
            close=df_k["Close"],
            name="K線",
            increasing_line_color="#FF3333",
            decreasing_line_color="#00AA00"
        ),
        row=1,
        col=1
    )

    ma_settings = [
        ("MA5", "#4C78FF"),
        ("MA10", "#58C9A5"),
        ("MA20", "#F2B134"),
        ("MA60", "#FF9EDB"),
        ("MA120", "#9B4DFF"),
        ("MA240", "#DDDDDD"),
    ]

    for ma, color in ma_settings:
        if ma in df_k.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_k["Date"],
                    y=df_k[ma],
                    name=ma,
                    line=dict(width=1.2, color=color)
                ),
                row=1,
                col=1
            )

    volume_colors = [
        "#FF3333" if close_price >= open_price else "#00AA00"
        for close_price, open_price in zip(df_k["Close"], df_k["Open"])
    ]

    fig.add_trace(
        go.Bar(
            x=df_k["Date"],
            y=df_k["Volume"],
            name="成交量",
            marker_color=volume_colors
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        title=f"{ticker} {k_period} K線與成交量",
        template="plotly_dark",
        height=700,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    return fig


def make_institutional_summary(df_inst):
    if df_inst is None or df_inst.empty:
        return pd.DataFrame(), pd.DataFrame()

    required = {"date", "name", "buy", "sell"}
    if not required.issubset(df_inst.columns):
        return pd.DataFrame(), pd.DataFrame()

    df = df_inst.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["name"] = df["name"].astype(str)
    df["buy"] = pd.to_numeric(df["buy"], errors="coerce").fillna(0)
    df["sell"] = pd.to_numeric(df["sell"], errors="coerce").fillna(0)
    df["Net_Shares"] = (df["buy"] - df["sell"]) / 1000

    def summarize(pattern, label):
        sub = df[df["name"].str.contains(pattern, case=False, na=False, regex=True)]
        if sub.empty:
            return pd.DataFrame(columns=["date", label])
        out = sub.groupby("date", as_index=False)["Net_Shares"].sum()
        out = out.rename(columns={"Net_Shares": label})
        return out

    foreign = summarize("外資|Foreign", "外資")
    trust = summarize("投信|Investment Trust", "投信")
    dealer = summarize("自營商|Dealer", "自營商")

    merged = None
    for x in [foreign, trust, dealer]:
        merged = x if merged is None else pd.merge(merged, x, on="date", how="outer")

    if merged is None or merged.empty:
        return pd.DataFrame(), pd.DataFrame()

    merged = merged.sort_values("date").fillna(0)
    for c in ["外資", "投信", "自營商"]:
        if c not in merged.columns:
            merged[c] = 0

    merged["三大法人"] = merged["外資"] + merged["投信"] + merged["自營商"]

    latest_rows = merged.sort_values("date", ascending=False).head(10).copy()
    latest_rows["日期"] = latest_rows["date"].dt.strftime("%m/%d")
    latest_rows = latest_rows[["日期", "外資", "投信", "自營商", "三大法人"]]

    return merged, latest_rows


def draw_institutional_chart(df_inst_summary, df_price_daily):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if df_inst_summary is None or df_inst_summary.empty:
        return fig

    colors = ["#FF3333" if x >= 0 else "#00AA00" for x in df_inst_summary["三大法人"]]

    fig.add_trace(
        go.Bar(
            x=df_inst_summary["date"],
            y=df_inst_summary["三大法人"],
            name="三大法人買賣超",
            marker_color=colors
        ),
        secondary_y=False
    )

    if df_price_daily is not None and not df_price_daily.empty:
        df_p = df_price_daily[["Date", "Close"]].copy()
        df_p["Date"] = pd.to_datetime(df_p["Date"], errors="coerce")

        fig.add_trace(
            go.Scatter(
                x=df_p["Date"],
                y=df_p["Close"],
                name="股價",
                mode="lines",
                line=dict(color="#DDDDDD", width=1.5)
            ),
            secondary_y=True
        )

    fig.update_layout(
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=40, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02)
    )
    fig.update_yaxes(title_text="買賣超（張）", secondary_y=False)
    fig.update_yaxes(title_text="股價", secondary_y=True)

    return fig


def draw_margin_chart(df_margin, df_price_daily):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if df_margin is None or df_margin.empty:
        return fig

    df = df_margin.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")

    if "MarginPurchaseTodayBalance" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=pd.to_numeric(df["MarginPurchaseTodayBalance"], errors="coerce"),
                name="融資餘額",
                mode="lines+markers"
            ),
            secondary_y=False
        )

    if "ShortSaleTodayBalance" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=pd.to_numeric(df["ShortSaleTodayBalance"], errors="coerce"),
                name="融券餘額",
                mode="lines+markers"
            ),
            secondary_y=False
        )

    if df_price_daily is not None and not df_price_daily.empty:
        fig.add_trace(
            go.Scatter(
                x=df_price_daily["Date"],
                y=df_price_daily["Close"],
                name="股價",
                mode="lines",
                line=dict(color="#DDDDDD", width=1.3)
            ),
            secondary_y=True
        )

    fig.update_layout(
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=40, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02)
    )

    fig.update_yaxes(title_text="資券餘額", secondary_y=False)
    fig.update_yaxes(title_text="股價", secondary_y=True)

    return fig


def standardize_lending_df(df_lending):
    if df_lending is None or df_lending.empty:
        return pd.DataFrame()

    df = df_lending.copy()

    if "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    balance_col = get_first_existing_col(df, [
        "SBLShortSaleBalance",
        "SecuritiesLendingSalesBalance",
        "ShortSaleBalance",
        "SecuritiesLendingBalance",
        "BorrowingBalance",
        "borrow_sell_balance",
        "借券賣出餘額"
    ])

    sell_col = get_first_existing_col(df, [
        "SBLShortSaleTodayVolume",
        "SecuritiesLendingSales",
        "ShortSaleTodayVolume",
        "BorrowingSell",
        "borrow_sell",
        "借券賣出"
    ])

    out = pd.DataFrame()
    out["date"] = df["date"]

    if balance_col:
        out["借券賣出餘額"] = pd.to_numeric(df[balance_col], errors="coerce")
    elif sell_col:
        out["借券賣出餘額"] = pd.to_numeric(df[sell_col], errors="coerce").cumsum()
    else:
        return pd.DataFrame()

    out = out.sort_values("date")
    out["借券賣出今日異動"] = out["借券賣出餘額"].diff()

    return out


def draw_lending_chart(df_lending_std, df_price_daily):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if df_lending_std is None or df_lending_std.empty:
        return fig

    fig.add_trace(
        go.Bar(
            x=df_lending_std["date"],
            y=df_lending_std["借券賣出餘額"],
            name="借券賣出餘額",
            marker_color="#8FD3E8"
        ),
        secondary_y=False
    )

    if df_price_daily is not None and not df_price_daily.empty:
        fig.add_trace(
            go.Scatter(
                x=df_price_daily["Date"],
                y=df_price_daily["Close"],
                name="股價",
                mode="lines",
                line=dict(color="#DDDDDD", width=1.3)
            ),
            secondary_y=True
        )

    fig.update_layout(
        template="plotly_dark",
        height=430,
        margin=dict(l=10, r=10, t=40, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02)
    )

    fig.update_yaxes(title_text="借券賣出餘額", secondary_y=False)
    fig.update_yaxes(title_text="股價", secondary_y=True)

    return fig


# ============================================================
# 主流程
# ============================================================
if not run_btn:
    st.info("請輸入股票代號後，按左側「啟動掃描」。")
    st.stop()

stock_code = clean_stock_code(stock_input)

if not stock_code:
    st.error("請輸入有效股票代號。")
    st.stop()

if start_date >= end_date:
    st.error("起始日必須早於結束日。")
    st.stop()

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

with st.spinner("讀取 Yahoo Finance K 線資料..."):
    df_price_daily, final_ticker = fetch_yfinance_price(stock_code, start_date, end_date)

if df_price_daily.empty:
    st.error(f"查無 {stock_code} 的 Yahoo Finance 價格資料。")
    st.stop()

with st.spinner("讀取基本資料與官方注意/處置狀態..."):
    basic_official = fetch_twse_tpex_basic_info(stock_code)
    basic_finmind = fetch_finmind_basic_info(stock_code, finmind_token)
    warning_status = check_official_warning_status(stock_code)

df_inst = pd.DataFrame()
df_margin = pd.DataFrame()
df_share = pd.DataFrame()
df_lending_raw = pd.DataFrame()

if finmind_token:
    with st.spinner("讀取 FinMind 法人、資券、股權與借券資料..."):
        df_inst = fetch_finmind_institutional(stock_code, start_str, end_str, finmind_token)
        df_margin = fetch_finmind_margin(stock_code, start_str, end_str, finmind_token)
        df_share = fetch_finmind_shareholding(stock_code, start_str, end_str, finmind_token)
        df_lending_raw = fetch_finmind_securities_lending(stock_code, start_str, end_str, finmind_token)
else:
    st.warning("尚未輸入 FinMind Token，因此法人、資券、借券、股權資料可能不會顯示。")

df_k = resample_ohlcv(df_price_daily, k_period)
price_summary = compute_price_summary(df_price_daily)

# ============================================================
# 股票摘要
# ============================================================
stock_name = (
    basic_official.get("stock_name")
    or basic_finmind.get("stock_name")
    or basic_finmind.get("stock_name_en")
    or ""
)

market = (
    basic_official.get("market")
    or basic_finmind.get("type")
    or ""
)

industry = (
    basic_official.get("industry")
    or basic_finmind.get("industry_category")
    or basic_finmind.get("industry")
    or ""
)

capital_raw = (
    basic_official.get("capital")
    or basic_finmind.get("capital")
    or basic_finmind.get("paid_in_capital")
    or ""
)

st.markdown("## 🧾 股票摘要")

title_left, title_right = st.columns([2.2, 1])

with title_left:
    st.markdown(f"### {stock_code} {stock_name} `{final_ticker}`")
    tag_text = []
    if market:
        tag_text.append(str(market))
    if industry:
        tag_text.append(str(industry))
    if tag_text:
        st.caption("・".join(tag_text))

with title_right:
    if warning_status["is_disposition"]:
        st.error("🛑 官方處置股")
        if warning_status["details"]:
            st.caption(warning_status["details"])
    elif warning_status["is_attention"]:
        st.warning("⚠️ 官方注意股")
    else:
        st.success("✅ 未列注意/處置")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("收盤價", fmt_num(price_summary.get("close"), 2))
m2.metric("漲跌", fmt_num(price_summary.get("change"), 2), delta=fmt_num(price_summary.get("change"), 2))
m3.metric("漲跌幅", fmt_pct(price_summary.get("change_pct"), 2))
m4.metric("成交量", fmt_num(price_summary.get("volume"), 0))
m5.metric("股本", capital_raw if capital_raw else "-")
m6.metric("資料日", str(pd.to_datetime(price_summary.get("date")).date()))

ohlc_text = (
    f"開 {fmt_num(price_summary.get('open'), 2)}　"
    f"高 {fmt_num(price_summary.get('high'), 2)}　"
    f"低 {fmt_num(price_summary.get('low'), 2)}　"
    f"收 {fmt_num(price_summary.get('close'), 2)}"
)
st.caption(ohlc_text)

# ============================================================
# K線
# ============================================================
st.markdown("---")
st.markdown("## 📈 K線圖與成交量")

fig_k = draw_kline_chart(df_k, final_ticker, k_period)
st.plotly_chart(fig_k, use_container_width=True)

latest_k = df_k.dropna(subset=["Close"]).iloc[-1]
ma_cols_show = [c for c in ["MA5", "MA10", "MA20", "MA60", "MA120", "MA240"] if c in df_k.columns]

ma_text_parts = []
for c in ma_cols_show:
    ma_text_parts.append(f"{c} {fmt_num(latest_k.get(c), 2)}")
st.caption("　".join(ma_text_parts))

# ============================================================
# 三大法人
# ============================================================
st.markdown("---")
st.markdown("## 🧑‍💼 三大法人買賣超")

df_inst_summary, df_inst_latest = make_institutional_summary(df_inst)

if df_inst_summary.empty:
    st.info("無三大法人資料。請確認 FinMind Token 或資料區間。")
else:
    col_i1, col_i2 = st.columns([1.4, 1])

    with col_i1:
        fig_inst = draw_institutional_chart(df_inst_summary, df_price_daily)
        st.plotly_chart(fig_inst, use_container_width=True)

    with col_i2:
        st.markdown("### 近 10 日法人買賣超（張）")
        st.dataframe(
            df_inst_latest.style.format({
                "外資": "{:,.0f}",
                "投信": "{:,.0f}",
                "自營商": "{:,.0f}",
                "三大法人": "{:,.0f}",
            }),
            use_container_width=True,
            height=420
        )

# ============================================================
# 融資融券
# ============================================================
st.markdown("---")
st.markdown("## 💳 融資融券餘額")

if df_margin.empty:
    st.info("無融資融券資料。請確認 FinMind Token 或資料區間。")
else:
    fig_margin = draw_margin_chart(df_margin, df_price_daily)
    st.plotly_chart(fig_margin, use_container_width=True)

    df_m = df_margin.copy().sort_values("date", ascending=False).head(12)

    cols = ["date"]
    rename_map = {"date": "日期"}

    margin_candidates = [
        ("MarginPurchaseBuy", "融資買進"),
        ("MarginPurchaseSell", "融資賣出"),
        ("MarginPurchaseCashRepayment", "融資現償"),
        ("MarginPurchaseTodayBalance", "融資餘額"),
        ("ShortSaleBuy", "融券買進"),
        ("ShortSaleSell", "融券賣出"),
        ("ShortSaleCashRepayment", "融券現償"),
        ("ShortSaleTodayBalance", "融券餘額"),
    ]

    for c, n in margin_candidates:
        if c in df_m.columns:
            cols.append(c)
            rename_map[c] = n

    df_m_show = df_m[cols].rename(columns=rename_map)
    st.dataframe(df_m_show, use_container_width=True)

# ============================================================
# 借券賣出餘額
# ============================================================
st.markdown("---")
st.markdown("## 🏦 借券賣出餘額")

df_lending = standardize_lending_df(df_lending_raw)

if df_lending.empty:
    st.info(
        "目前沒有成功取得借券賣出餘額。"
        "若 FinMind 資料集名稱或權限不同，請先確認 Token 權限；之後也可改接官方借券資料。"
    )

    if df_lending_raw is not None and not df_lending_raw.empty:
        st.markdown("### 已取得但尚未能自動辨識欄位的原始借券資料")
        st.dataframe(df_lending_raw, use_container_width=True)
else:
    fig_lending = draw_lending_chart(df_lending, df_price_daily)
    st.plotly_chart(fig_lending, use_container_width=True)

    latest_lending = df_lending.sort_values("date").iloc[-1]
    l1, l2, l3 = st.columns(3)
    l1.metric("最新日期", str(pd.to_datetime(latest_lending["date"]).date()))
    l2.metric("借券賣出餘額", fmt_num(latest_lending["借券賣出餘額"], 0))
    l3.metric("今日異動", fmt_num(latest_lending["借券賣出今日異動"], 0))

    st.dataframe(
        df_lending.sort_values("date", ascending=False).head(12).rename(columns={"date": "日期"}),
        use_container_width=True
    )

# ============================================================
# 股權分布 / 浮額估算
# ============================================================
st.markdown("---")
st.markdown("## 🌊 股權分布與浮額估算")

if df_share.empty:
    st.info("無股權分布資料。")
else:
    if {"date", "HoldingSharesPer", "percent"}.issubset(df_share.columns):
        df_s = df_share.copy()
        df_s["date"] = pd.to_datetime(df_s["date"], errors="coerce")
        df_s["HoldingSharesPer"] = pd.to_numeric(df_s["HoldingSharesPer"], errors="coerce")
        df_s["percent"] = pd.to_numeric(df_s["percent"], errors="coerce")

        latest_share_date = df_s["date"].max()
        df_latest_share = df_s[df_s["date"] == latest_share_date].copy()

        big_pct = df_latest_share[df_latest_share["HoldingSharesPer"] >= 1000]["percent"].sum()
        float_pct = 100 - big_pct

        c1, c2, c3 = st.columns(3)
        c1.metric("股權資料日", str(pd.to_datetime(latest_share_date).date()))
        c2.metric("大戶持股估算", fmt_pct(big_pct, 2))
        c3.metric("市場浮額估算", fmt_pct(float_pct, 2))

        st.dataframe(df_latest_share, use_container_width=True)
    else:
        st.dataframe(df_share, use_container_width=True)

# ============================================================
# 基本資料
# ============================================================
st.markdown("---")
st.markdown("## 🏢 基本資料")

basic_rows = [
    ["股票代號", stock_code],
    ["股票名稱", stock_name if stock_name else "-"],
    ["Yahoo Ticker", final_ticker],
    ["市場別", market if market else "-"],
    ["產業別", industry if industry else "-"],
    ["股本 / 實收資本額", capital_raw if capital_raw else "-"],
    ["上市櫃日期", basic_official.get("listing_date") or basic_finmind.get("date") or "-"],
    ["基本資料來源", basic_official.get("source") or "FinMind / fallback"],
]

df_basic_show = pd.DataFrame(basic_rows, columns=["項目", "內容"])
st.dataframe(df_basic_show, use_container_width=True, hide_index=True)

# ============================================================
# 原始資料
# ============================================================
with st.expander("🔎 原始資料檢視"):
    st.markdown("### Yahoo Finance 股價")
    st.dataframe(df_price_daily, use_container_width=True)

    st.markdown("### FinMind 三大法人")
    st.dataframe(df_inst, use_container_width=True)

    st.markdown("### FinMind 融資融券")
    st.dataframe(df_margin, use_container_width=True)

    st.markdown("### FinMind 借券原始資料")
    st.dataframe(df_lending_raw, use_container_width=True)

    st.markdown("### FinMind 股權分布")
    st.dataframe(df_share, use_container_width=True)

st.caption("本工具僅整理公開資料與視覺化，不構成投資建議。")
