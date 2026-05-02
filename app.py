"""
================================================================================
 IHSG EoD SWING TRADING SCREENER DASHBOARD
 Author  : Senior Quantitative Developer
 Stack   : Streamlit · yfinance · pandas-ta · Plotly · requests
 Market  : Indonesian Stock Exchange (IDX / IHSG)
 Strategy: End-of-Day (EoD) Swing Trading
================================================================================
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta
import time
import warnings

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# 0.  PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IHSG Swing Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# 1.  GLOBAL CONSTANTS & MOCK FUNDAMENTAL DATABASE
# ──────────────────────────────────────────────────────────────────────────────

# Liquid IHSG tickers in Yahoo Finance format (suffix .JK)
TICKER_UNIVERSE = [
    "BBCA.JK", "BMRI.JK", "ASII.JK", "TLKM.JK",
    "BBNI.JK", "AMMN.JK", "BBRI.JK", "GOTO.JK",
    "BYAN.JK", "PGAS.JK",
]

# Static mock fundamental database
# In production, replace with an API call (e.g., Bloomberg, Refinitiv, IDX API)
FUNDAMENTAL_DB: dict[str, dict] = {
    "BBCA.JK": {"PER": 24.1, "PBV": 4.8,  "sector": "Banking",       "name": "Bank Central Asia"},
    "BMRI.JK": {"PER": 11.3, "PBV": 2.1,  "sector": "Banking",       "name": "Bank Mandiri"},
    "ASII.JK": {"PER":  9.8, "PBV": 1.3,  "sector": "Automotive",    "name": "Astra International"},
    "TLKM.JK": {"PER": 13.5, "PBV": 2.9,  "sector": "Telecom",       "name": "Telkom Indonesia"},
    "BBNI.JK": {"PER":  8.7, "PBV": 1.1,  "sector": "Banking",       "name": "Bank Negara Indonesia"},
    "AMMN.JK": {"PER": 14.2, "PBV": 3.4,  "sector": "Mining",        "name": "Amman Mineral"},
    "BBRI.JK": {"PER": 10.1, "PBV": 1.8,  "sector": "Banking",       "name": "Bank Rakyat Indonesia"},
    "GOTO.JK": {"PER": -1.0, "PBV": 0.9,  "sector": "Technology",    "name": "GoTo Group"},
    "BYAN.JK": {"PER":  6.5, "PBV": 8.2,  "sector": "Coal",          "name": "Bayan Resources"},
    "PGAS.JK": {"PER":  7.8, "PBV": 0.8,  "sector": "Energy",        "name": "Perusahaan Gas Negara"},
}

DATA_PERIOD   = "6mo"   # yfinance period string
DATA_INTERVAL = "1d"    # daily EoD bars


# ──────────────────────────────────────────────────────────────────────────────
# 2.  DATA INGESTION LAYER
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)   # Cache for 1 hour (EoD strategy)
def fetch_ohlcv(ticker: str) -> pd.DataFrame | None:
    """
    Fetch 6-month daily OHLCV data from Yahoo Finance for a single ticker.

    Returns
    -------
    pd.DataFrame with columns [Open, High, Low, Close, Volume]
    or None if the download fails / returns empty data.
    """
    try:
        raw = yf.download(
            ticker,
            period=DATA_PERIOD,
            interval=DATA_INTERVAL,
            auto_adjust=True,   # Adjust for splits & dividends
            progress=False,
        )
        if raw.empty:
            return None

        # Flatten MultiIndex columns that yfinance sometimes returns
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df

    except Exception as exc:
        st.warning(f"⚠️  Could not fetch data for {ticker}: {exc}")
        return None


def build_universe_data(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV data for every ticker in the universe.

    Returns
    -------
    dict  {ticker: DataFrame}
    """
    universe: dict[str, pd.DataFrame] = {}
    progress = st.progress(0, text="Fetching market data…")

    for i, ticker in enumerate(tickers):
        df = fetch_ohlcv(ticker)
        if df is not None and len(df) >= 60:   # Need enough bars for SMA-50
            universe[ticker] = df
        progress.progress((i + 1) / len(tickers), text=f"Fetching {ticker}…")
        time.sleep(0.2)   # Gentle rate-limiting

    progress.empty()
    return universe


# ──────────────────────────────────────────────────────────────────────────────
# 3.  INDICATOR ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Close"].rolling(window=50).mean()
    df["RSI_14"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    macd = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD_12_26_9"]  = macd.macd()
    df["MACDh_12_26_9"] = macd.macd_diff()
    df["MACDs_12_26_9"] = macd.macd_signal()
    return df



# ──────────────────────────────────────────────────────────────────────────────
# 4.  SCREENER / FILTER ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def run_screener(
    universe_data: dict[str, pd.DataFrame],
    max_per: float,
    max_pbv: float,
    min_volume: float,
    rsi_threshold: float,
) -> pd.DataFrame:
    """
    Apply all EoD swing-trading filters and return a summary DataFrame
    of stocks that pass every criterion.

    Criteria (ALL must be True)
    ---------------------------
    1. Value       : PBV < max_pbv  OR  PER < max_per  (AND PER > 0)
    2. Liquidity   : 20-day avg volume  > min_volume shares
    3. Trend       : Close > SMA_50
    4. Short Bounce: Close > SMA_20
    5. Momentum    : MACD histogram > 0  OR  RSI crosses above rsi_threshold
    """
    rows = []

    for ticker, df in universe_data.items():
        df_ind = compute_indicators(df)

        if len(df_ind) < 2:
            continue   # Need at least 2 rows to detect crossovers

        # --- Latest & previous bar ---
        latest = df_ind.iloc[-1]
        prev   = df_ind.iloc[-2]

        # --- Fundamental metrics (from mock DB) ---
        fundamentals = FUNDAMENTAL_DB.get(ticker, {})
        per = fundamentals.get("PER", 999)
        pbv = fundamentals.get("PBV", 999)

        # 1. VALUE FILTER
        value_ok = (pbv < max_pbv) or (0 < per < max_per)

        # 2. LIQUIDITY FILTER (20-day average volume)
        avg_vol_20 = df_ind["Volume"].iloc[-20:].mean()
        liquidity_ok = avg_vol_20 > min_volume

        # 3. TREND FILTER
        close    = latest["Close"]
        sma_50   = latest.get("SMA_50", float("nan"))
        trend_ok = close > sma_50 if pd.notna(sma_50) else False

        # 4. SHORT-TERM BOUNCE
        sma_20      = latest.get("SMA_20", float("nan"))
        bounce_ok   = close > sma_20 if pd.notna(sma_20) else False

        # 5. MOMENTUM TRIGGERS
        # a) MACD histogram turns positive (crossover from negative)
        macd_hist_col = "MACDh_12_26_9"
        macd_hist_now  = latest.get(macd_hist_col, float("nan"))
        macd_hist_prev = prev.get(macd_hist_col, float("nan"))

        macd_golden = (
            pd.notna(macd_hist_now) and pd.notna(macd_hist_prev)
            and macd_hist_now > 0 and macd_hist_prev <= 0
        )

        # b) RSI crosses above threshold from below (oversold recovery)
        rsi_now  = latest.get("RSI_14", float("nan"))
        rsi_prev = prev.get("RSI_14", float("nan"))

        rsi_cross = (
            pd.notna(rsi_now) and pd.notna(rsi_prev)
            and rsi_now > rsi_threshold and rsi_prev <= rsi_threshold
        )

        momentum_ok = macd_golden or rsi_cross

        # --- Final gate ---
        if value_ok and liquidity_ok and trend_ok and bounce_ok and momentum_ok:
            signal_reasons = []
            if macd_golden: signal_reasons.append("MACD Cross")
            if rsi_cross:   signal_reasons.append(f"RSI>{rsi_threshold:.0f}")

            rows.append({
                "Ticker":      ticker,
                "Name":        fundamentals.get("name", ticker),
                "Sector":      fundamentals.get("sector", "N/A"),
                "Close (IDR)": round(close, 2),
                "SMA 20":      round(sma_20, 2) if pd.notna(sma_20) else None,
                "SMA 50":      round(sma_50, 2) if pd.notna(sma_50) else None,
                "RSI (14)":    round(rsi_now, 2) if pd.notna(rsi_now) else None,
                "MACD Hist":   round(macd_hist_now, 4) if pd.notna(macd_hist_now) else None,
                "Avg Vol 20D": int(avg_vol_20),
                "PER":         per,
                "PBV":         pbv,
                "Signal":      " & ".join(signal_reasons),
            })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# 5.  PLOTLY CHART ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def build_chart(ticker: str, df_raw: pd.DataFrame) -> go.Figure:
    """
    Build a multi-panel Plotly chart:
      Panel 1 (top, 60%): Candlestick + SMA 20 + SMA 50
      Panel 2 (mid, 20%): MACD histogram + signal lines
      Panel 3 (bot, 20%): Volume bars
    """
    df = compute_indicators(df_raw)
    name = FUNDAMENTAL_DB.get(ticker, {}).get("name", ticker)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.60, 0.20, 0.20],
        subplot_titles=(f"{ticker} · {name}", "MACD (12, 26, 9)", "Volume"),
    )

    # --- Candlestick ---
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"],
            low=df["Low"],   close=df["Close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a",
            decreasing_fillcolor="#ef5350",
        ),
        row=1, col=1,
    )

    # --- SMA lines ---
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["SMA_20"],
            name="SMA 20", line=dict(color="#f7c325", width=1.5, dash="solid"),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["SMA_50"],
            name="SMA 50", line=dict(color="#2979ff", width=1.5, dash="dot"),
        ),
        row=1, col=1,
    )

    # --- MACD histogram (colour-coded) ---
    macd_col  = "MACD_12_26_9"
    hist_col  = "MACDh_12_26_9"
    sig_col   = "MACDs_12_26_9"

    hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df[hist_col].fillna(0)]

    fig.add_trace(
        go.Bar(
            x=df.index, y=df[hist_col],
            name="MACD Hist", marker_color=hist_colors, opacity=0.7,
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[macd_col],
            name="MACD", line=dict(color="#2979ff", width=1.2),
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[sig_col],
            name="Signal", line=dict(color="#ff6d00", width=1.2, dash="dot"),
        ),
        row=2, col=1,
    )

    # --- Volume bars ---
    vol_colors = [
        "#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
        for i in range(len(df))
    ]
    fig.add_trace(
        go.Bar(
            x=df.index, y=df["Volume"],
            name="Volume", marker_color=vol_colors, opacity=0.7,
        ),
        row=3, col=1,
    )

    # --- Layout ---
    fig.update_layout(
        template="plotly_dark",
        height=750,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(family="Courier New, monospace", color="#e0e0e0", size=11),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h", yanchor="bottom",
            y=1.02, xanchor="right", x=1,
        ),
        margin=dict(l=50, r=30, t=60, b=40),
    )
    fig.update_yaxes(gridcolor="#1e2130", zerolinecolor="#1e2130")
    fig.update_xaxes(gridcolor="#1e2130", showspikes=True, spikecolor="#555")

    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 6.  WEBHOOK AUTOMATION (Make.com → Telegram)
# ──────────────────────────────────────────────────────────────────────────────

def build_webhook_payload(screened_df: pd.DataFrame) -> dict:
    """
    Construct a structured JSON payload optimised for a Make.com custom webhook
    that drives a Telegram Bot message module.

    Payload schema
    --------------
    {
      "source"    : "IHSG_EoD_Screener",
      "timestamp" : "<ISO-8601>",
      "alert_count": <int>,
      "alerts": [
        {
          "ticker"    : "BBNI.JK",
          "name"      : "Bank Negara Indonesia",
          "sector"    : "Banking",
          "close_idr" : 4850.0,
          "rsi_14"    : 36.8,
          "macd_hist" : 12.5,
          "per"       : 8.7,
          "pbv"       : 1.1,
          "signal"    : "RSI>35",
          "message"   : "<human-readable summary>"
        },
        …
      ]
    }

    Make.com Mapping Guide
    ----------------------
    In the "Custom Webhook" trigger module, map:
      {{1.alerts[]}}  →  Iterator
    Then in the Telegram "Send Message" module, compose:
      *{{ticker}}* – {{name}}
      Price : Rp {{close_idr}}
      RSI   : {{rsi_14}}
      PER / PBV : {{per}} / {{pbv}}
      Signal: {{signal}}
    """
    if screened_df.empty:
        return {"source": "IHSG_EoD_Screener", "alert_count": 0, "alerts": []}

    alerts = []
    for _, row in screened_df.iterrows():
        ticker    = row.get("Ticker", "")
        close_idr = row.get("Close (IDR)", 0)
        rsi       = row.get("RSI (14)", 0)
        macd_h    = row.get("MACD Hist", 0)
        per       = row.get("PER", 0)
        pbv       = row.get("PBV", 0)
        signal    = row.get("Signal", "")
        name      = row.get("Name", "")
        sector    = row.get("Sector", "")

        human_msg = (
            f"🟢 *{ticker}* ({name}) is signalling an EoD swing entry.\n"
            f"   💰 Close: Rp {close_idr:,.0f}\n"
            f"   📈 RSI(14): {rsi:.1f} | MACD Hist: {macd_h:.4f}\n"
            f"   📊 PER: {per} | PBV: {pbv}\n"
            f"   🎯 Trigger: {signal}"
        )

        alerts.append({
            "ticker":    ticker,
            "name":      name,
            "sector":    sector,
            "close_idr": float(close_idr),
            "rsi_14":    float(rsi) if rsi else None,
            "macd_hist": float(macd_h) if macd_h else None,
            "per":       float(per),
            "pbv":       float(pbv),
            "signal":    signal,
            "message":   human_msg,
        })

    return {
        "source":      "IHSG_EoD_Screener",
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "alert_count": len(alerts),
        "alerts":      alerts,
    }


def send_telegram_webhook(screened_df: pd.DataFrame, webhook_url: str) -> dict:
    """
    POST the structured payload to a Make.com custom webhook URL.

    Parameters
    ----------
    screened_df : pd.DataFrame
        The filtered output from run_screener().
    webhook_url : str
        Your Make.com webhook endpoint (starts with https://hook.eu1.make.com/…)

    Returns
    -------
    dict with keys: success (bool), status_code (int), response_text (str)
    """
    payload = build_webhook_payload(screened_df)

    try:
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=15,
        )
        return {
            "success":       response.status_code == 200,
            "status_code":   response.status_code,
            "response_text": response.text,
            "payload_sent":  payload,
        }
    except requests.exceptions.Timeout:
        return {"success": False, "status_code": 0, "response_text": "Request timed out."}
    except requests.exceptions.ConnectionError as exc:
        return {"success": False, "status_code": 0, "response_text": str(exc)}
    except Exception as exc:
        return {"success": False, "status_code": 0, "response_text": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# 7.  STREAMLIT UI
# ──────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> tuple[float, float, float, float, str]:
    """Render the sidebar controls and return user parameters."""
    st.sidebar.markdown(
        """
        <div style='text-align:center; padding:12px 0 6px;'>
            <span style='font-size:2rem;'>📊</span><br>
            <span style='font-size:1.15rem; font-weight:700; letter-spacing:1px;
                         color:#f7c325;'>IHSG SWING SCREENER</span><br>
            <span style='font-size:0.72rem; color:#888;'>
                End-of-Day · Indonesian Equities
            </span>
        </div>
        <hr style='border-color:#333; margin:8px 0;'>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.subheader("⚙️  Screener Parameters")

    max_per = st.sidebar.slider(
        "Max PER",
        min_value=5.0, max_value=40.0, value=15.0, step=0.5,
        help="Stocks with Price-to-Earnings Ratio below this threshold pass the value filter.",
    )
    max_pbv = st.sidebar.slider(
        "Max PBV",
        min_value=0.5, max_value=5.0, value=1.5, step=0.1,
        help="Stocks with Price-to-Book Value below this threshold also pass (OR logic).",
    )
    min_volume_m = st.sidebar.slider(
        "Min 20D Avg Volume (M shares)",
        min_value=1.0, max_value=100.0, value=20.0, step=1.0,
        help="Minimum average daily traded volume over 20 days (in millions).",
    )
    rsi_threshold = st.sidebar.slider(
        "RSI Cross-Above Threshold",
        min_value=20.0, max_value=50.0, value=35.0, step=1.0,
        help="RSI must cross above this level from below to trigger a momentum signal.",
    )

    st.sidebar.markdown("<hr style='border-color:#333;'>", unsafe_allow_html=True)
    st.sidebar.subheader("🔔  Webhook Config")

    webhook_url = st.sidebar.text_input(
        "Make.com Webhook URL",
        value="",
        placeholder="https://hook.eu1.make.com/xxxx…",
        type="password",
        help="Paste your Make.com custom webhook URL here. It will not be stored.",
    )

    st.sidebar.markdown(
        """
        <hr style='border-color:#333;'>
        <div style='font-size:0.7rem; color:#555; text-align:center;'>
            Data: Yahoo Finance · EoD Bars<br>
            Indicators: pandas-ta<br>
            Charts: Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )

    return max_per, max_pbv, min_volume_m * 1_000_000, rsi_threshold, webhook_url


def style_screener_df(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply colour-based styling to the screener results table."""
    def rsi_color(val):
        if pd.isna(val): return ""
        if val < 30:  return "color: #ef5350; font-weight:bold"
        if val < 50:  return "color: #f7c325"
        return "color: #26a69a"

    def signal_color(val):
        return "color: #26a69a; font-weight: bold" if val else ""

    fmt = {
        "Close (IDR)": "{:,.0f}",
        "SMA 20":      "{:,.0f}",
        "SMA 50":      "{:,.0f}",
        "RSI (14)":    "{:.1f}",
        "MACD Hist":   "{:.4f}",
        "Avg Vol 20D": "{:,.0f}",
        "PER":         "{:.1f}",
        "PBV":         "{:.2f}",
    }

    return (
        df.style
          .applymap(rsi_color,     subset=["RSI (14)"])
          .applymap(signal_color,  subset=["Signal"])
          .format(fmt, na_rep="–")
          .set_properties(**{"text-align": "right"})
          .set_table_styles([
              {"selector": "th", "props": [("text-align", "center"),
                                           ("background-color", "#1a1d27"),
                                           ("color", "#f7c325")]},
          ])
    )


def main():
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='padding:18px 0 6px;'>
            <h1 style='margin:0; font-size:1.8rem; font-family:Courier New,monospace;
                       color:#f7c325; letter-spacing:2px;'>
                IHSG · EoD SWING SCREENER
            </h1>
            <p style='margin:4px 0 0; color:#888; font-size:0.85rem;'>
                Indonesian Equities · End-of-Day Signal Detection ·
                Last refreshed: {ts}
            </p>
        </div>
        <hr style='border-color:#333; margin:8px 0 16px;'>
        """.format(ts=datetime.now().strftime("%d %b %Y, %H:%M WIB")),
        unsafe_allow_html=True,
    )

    # ── Sidebar ────────────────────────────────────────────────────────────────
    max_per, max_pbv, min_volume, rsi_threshold, webhook_url = render_sidebar()

    # ── Data Fetch (with spinner) ──────────────────────────────────────────────
    with st.spinner("📡  Downloading market data from Yahoo Finance…"):
        universe_data = build_universe_data(TICKER_UNIVERSE)

    if not universe_data:
        st.error("❌  No data could be fetched. Check your internet connection.")
        return

    st.caption(f"✅  {len(universe_data)} tickers loaded successfully.")

    # ── Run Screener ──────────────────────────────────────────────────────────
    with st.spinner("🔍  Running screener logic…"):
        result_df = run_screener(
            universe_data, max_per, max_pbv, min_volume, rsi_threshold
        )

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Universe Size",      len(universe_data))
    col2.metric("Passed Screener",    len(result_df),
                delta=f"+{len(result_df)}" if len(result_df) > 0 else None)
    col3.metric("PER Filter",         f"< {max_per}")
    col4.metric("RSI Threshold",      f"> {rsi_threshold}")

    st.markdown("---")

    # ── Results Table ─────────────────────────────────────────────────────────
    st.subheader("📋  Screener Results — Stocks Passing ALL Criteria")

    if result_df.empty:
        st.info(
            "🔎  No stocks matched all criteria today. "
            "Try relaxing the parameters in the sidebar."
        )
    else:
        st.dataframe(
            style_screener_df(result_df),
            use_container_width=True,
            height=min(400, 60 + len(result_df) * 40),
        )

        # ── Webhook Trigger ────────────────────────────────────────────────────
        st.markdown("---")
        col_btn, col_status = st.columns([1, 3])

        with col_btn:
            trigger = st.button(
                "🔔  Trigger Telegram Alert",
                type="primary",
                disabled=not webhook_url,
                help="Enter your Make.com webhook URL in the sidebar first.",
            )

        with col_status:
            if not webhook_url:
                st.warning("⚠️  Enter a webhook URL in the sidebar to enable alerts.")

        if trigger and webhook_url:
            with st.spinner("Sending webhook to Make.com…"):
                result = send_telegram_webhook(result_df, webhook_url)

            if result["success"]:
                st.success(
                    f"✅  Webhook delivered!  "
                    f"(HTTP {result['status_code']}) — "
                    f"{len(result_df)} alert(s) sent."
                )
            else:
                st.error(
                    f"❌  Webhook failed (HTTP {result['status_code']}): "
                    f"{result['response_text']}"
                )

            # Show the raw payload for debugging
            with st.expander("🔍  Inspect Payload (JSON)"):
                st.json(build_webhook_payload(result_df))

        # ── Chart Panel ───────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📈  Visual Validation — Interactive Chart")

        passed_tickers = result_df["Ticker"].tolist()
        selected = st.selectbox(
            "Select a ticker from the passed list:",
            options=passed_tickers,
        )

        if selected and selected in universe_data:
            with st.spinner(f"Rendering chart for {selected}…"):
                fig = build_chart(selected, universe_data[selected])
            st.plotly_chart(fig, use_container_width=True)

            # Mini fundamental card
            fnd = FUNDAMENTAL_DB.get(selected, {})
            row = result_df[result_df["Ticker"] == selected].iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PER",     fnd.get("PER", "–"))
            c2.metric("PBV",     fnd.get("PBV", "–"))
            c3.metric("RSI(14)", f"{row['RSI (14)']:.1f}" if pd.notna(row["RSI (14)"]) else "–")
            c4.metric("Signal",  row["Signal"])

    # ── All-Universe Overview ─────────────────────────────────────────────────
    with st.expander("🌐  Full Universe — Latest Snapshot (All Tickers)"):
        snapshot_rows = []
        for ticker, df in universe_data.items():
            df_ind = compute_indicators(df)
            last   = df_ind.iloc[-1]
            fnd    = FUNDAMENTAL_DB.get(ticker, {})
            snapshot_rows.append({
                "Ticker":   ticker,
                "Name":     fnd.get("name", ticker),
                "Close":    round(last["Close"], 2),
                "SMA 20":   round(last.get("SMA_20", float("nan")), 2),
                "SMA 50":   round(last.get("SMA_50", float("nan")), 2),
                "RSI (14)": round(last.get("RSI_14", float("nan")), 1),
                "PER":      fnd.get("PER"),
                "PBV":      fnd.get("PBV"),
                "Sector":   fnd.get("sector", "–"),
            })
        snap_df = pd.DataFrame(snapshot_rows)
        st.dataframe(snap_df, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()