"""
================================================================================
 IHSG EoD SWING TRADING SCREENER DASHBOARD
 Author  : Senior Quantitative Developer
 Stack   : Streamlit · yfinance · ta · Plotly · requests
 Market  : Indonesian Stock Exchange (IDX / IHSG)
 Strategy: End-of-Day (EoD) Swing Trading
 Universe: 300 Saham IHSG
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
from datetime import datetime
import time
import warnings

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# 0.  PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IHSG Swing Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# 1.  UNIVERSE — 300 SAHAM IHSG
# ──────────────────────────────────────────────────────────────────────────────
TICKER_UNIVERSE = [
    # PERBANKAN
    "BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","BNGA.JK","NISP.JK",
    "BDMN.JK","BNII.JK","MEGA.JK","PNBN.JK","BJBR.JK","BJTM.JK","AGRO.JK",
    "BTPS.JK","BBKP.JK","NOBU.JK","ARTO.JK","BANK.JK","BBYB.JK","MAYA.JK",
    "MCOR.JK","AMAR.JK","BABP.JK","BMAS.JK","BCIC.JK","DNAR.JK","BEKS.JK",
    # TELEKOMUNIKASI
    "TLKM.JK","EXCL.JK","ISAT.JK","FREN.JK","TBIG.JK","TOWR.JK","SUPR.JK",
    "MTEL.JK","MPXL.JK",
    # TEKNOLOGI & DIGITAL
    "GOTO.JK","EMTK.JK","DMMX.JK","MTDL.JK","MLPT.JK","NFCX.JK","CASH.JK",
    "FORE.JK","SKYB.JK","AXIO.JK","ATIC.JK","DIGI.JK",
    # ENERGI & MINYAK
    "PGAS.JK","MEDC.JK","ENRG.JK","AKRA.JK","ELSA.JK","RUIS.JK","ARTI.JK",
    "BIPI.JK","ESSA.JK","MITI.JK","WINS.JK","SURE.JK",
    # BATUBARA
    "BYAN.JK","ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","ARII.JK","DOID.JK",
    "BUMI.JK","GEMS.JK","SMMT.JK","MBAP.JK","FIRE.JK","TOBA.JK","INDY.JK",
    "MYOH.JK","GTBO.JK","PKPK.JK","BRAU.JK","MCMB.JK",
    # PERTAMBANGAN & MINERAL
    "AMMN.JK","ANTM.JK","INCO.JK","MDKA.JK","PSAB.JK","CITA.JK","DKFT.JK",
    "ZINC.JK","NCKL.JK","ADMR.JK","SMRU.JK","TINS.JK","ARCI.JK","FTTH.JK",
    # KONSUMER & MAKANAN
    "ICBP.JK","INDF.JK","MYOR.JK","ULTJ.JK","CLEO.JK","SKBM.JK","GOOD.JK",
    "CAMP.JK","HOKI.JK","STTP.JK","DLTA.JK","MLBI.JK","SKLT.JK","ROTI.JK",
    "KEJU.JK","DMND.JK","PANI.JK","PSDN.JK","AISA.JK","WMUU.JK",
    # ROKOK
    "GGRM.JK","HMSP.JK","WIIM.JK","ITIC.JK",
    # CONSUMER GOODS & RETAIL
    "UNVR.JK","MAPI.JK","ACES.JK","LPPF.JK","RALS.JK","AMRT.JK","MIDI.JK",
    "HERO.JK","MPPA.JK","CSAP.JK","RANC.JK","SONA.JK","KOIN.JK","PZZA.JK",
    "FAST.JK","PTSP.JK","MAP.JK","PJAA.JK","KFIN.JK",
    # KESEHATAN & FARMASI
    "KLBF.JK","SIDO.JK","MIKA.JK","SILO.JK","HEAL.JK","PRDA.JK","DVLA.JK",
    "PYFA.JK","TSPC.JK","KAEF.JK","INAF.JK","SOHO.JK","BMHS.JK","SAME.JK",
    "OMED.JK","PRIM.JK","RSGK.JK",
    # PROPERTI & REAL ESTATE
    "BSDE.JK","SMRA.JK","CTRA.JK","PWON.JK","LPKR.JK","ASRI.JK","DILD.JK",
    "MDLN.JK","APLN.JK","KIJA.JK","DART.JK","JRPT.JK","NIRO.JK","MKPI.JK",
    "GPRA.JK","PLIN.JK","BEST.JK","LPCK.JK","RBMS.JK","FORZ.JK",
    # OTOMOTIF & INDUSTRI
    "ASII.JK","AUTO.JK","SMSM.JK","UNTR.JK","IMAS.JK","GJTL.JK","GDYR.JK",
    "NIPS.JK","BOLT.JK","INDS.JK","MASA.JK","PRAS.JK","MYTX.JK",
    # SEMEN & BAHAN BANGUNAN
    "INTP.JK","SMGR.JK","WTON.JK","BDKR.JK","ARNA.JK","TOTO.JK","KIAS.JK",
    "MARK.JK","SMBR.JK","CAKK.JK",
    # INFRASTRUKTUR & KONSTRUKSI
    "JSMR.JK","WIKA.JK","WSKT.JK","PTPP.JK","ADHI.JK","ACST.JK","NRCA.JK",
    "TOTL.JK","DGIK.JK","PBSA.JK","IDPR.JK","WEGE.JK","MABA.JK",
    # PERKEBUNAN & AGRIBISNIS
    "AALI.JK","LSIP.JK","DSNG.JK","TAPG.JK","SSMS.JK","PALM.JK","SGRO.JK",
    "TBLA.JK","SMAR.JK","BWPT.JK","JAWA.JK","GZCO.JK","MAGP.JK","ANJT.JK",
    # LOGISTIK & TRANSPORTASI
    "BIRD.JK","BLTA.JK","SAFE.JK","SMDR.JK","TMAS.JK","MBSS.JK","ASSA.JK",
    "GIAA.JK","CMPP.JK","IPCM.JK","NELY.JK","BULL.JK","CASS.JK",
    # MEDIA & HIBURAN
    "SCMA.JK","MNCN.JK","KPIG.JK","LINK.JK","MSIN.JK","FILM.JK","CBPE.JK",
    # KIMIA & INDUSTRI DASAR
    "TPIA.JK","BRPT.JK","DPNS.JK","EKAD.JK","INCI.JK","UNIC.JK","SRSN.JK",
    "SOBI.JK","TDPM.JK","ADMG.JK","FPNI.JK","ALDO.JK","ETWA.JK",
    # TEKSTIL & GARMEN
    "RICY.JK","PBRX.JK","ESTI.JK","TRIS.JK","UNIT.JK","CNTX.JK",
    # MULTI FINANCE & ASURANSI
    "BBLD.JK","MFIN.JK","BFIN.JK","VRNA.JK","ADMF.JK","IMJS.JK","JMAS.JK",
    "LIFE.JK","PNLF.JK","ASRM.JK","ABDA.JK","MREI.JK","LPGI.JK",
]

# Deduplicate jaga urutan
_seen = set()
TICKER_UNIVERSE = [t for t in TICKER_UNIVERSE if not (_seen.add(t) or t in _seen)]

DATA_PERIOD   = "6mo"
DATA_INTERVAL = "1d"


# ──────────────────────────────────────────────────────────────────────────────
# 2.  AUTO FUNDAMENTAL FETCH
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamentals(ticker: str) -> dict:
    """Auto-fetch PER, PBV, nama, sektor dari Yahoo Finance. Cache 24 jam."""
    try:
        info   = yf.Ticker(ticker).info
        per    = info.get("trailingPE") or info.get("forwardPE") or -1
        pbv    = info.get("priceToBook") or -1
        name   = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector") or info.get("industry") or "N/A"
        return {
            "PER":    round(float(per), 2) if per and float(per) > 0 else -1,
            "PBV":    round(float(pbv), 2) if pbv and float(pbv) > 0 else -1,
            "name":   name,
            "sector": sector,
        }
    except Exception:
        return {"PER": -1, "PBV": -1, "name": ticker, "sector": "N/A"}


# ──────────────────────────────────────────────────────────────────────────────
# 3.  DATA INGESTION
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(ticker: str) -> pd.DataFrame | None:
    """Fetch 6-bulan data OHLCV harian. Cache 1 jam."""
    try:
        raw = yf.download(
            ticker,
            period=DATA_PERIOD,
            interval=DATA_INTERVAL,
            auto_adjust=True,
            progress=False,
        )
        if raw.empty:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df if len(df) >= 55 else None
    except Exception:
        return None


def build_universe_data(tickers: list) -> dict:
    """Download OHLCV semua ticker."""
    universe = {}
    total    = len(tickers)
    progress = st.progress(0, text="Memuat data pasar…")
    for i, ticker in enumerate(tickers):
        df = fetch_ohlcv(ticker)
        if df is not None:
            universe[ticker] = df
        progress.progress((i + 1) / total, text=f"📡 {ticker} ({i+1}/{total})")
        time.sleep(0.05)
    progress.empty()
    return universe


# ──────────────────────────────────────────────────────────────────────────────
# 4.  INDICATOR ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Hitung SMA 20/50, RSI 14, MACD."""
    df = df.copy()
    df["SMA_20"]       = df["Close"].rolling(20).mean()
    df["SMA_50"]       = df["Close"].rolling(50).mean()
    df["RSI_14"]       = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    macd               = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD_12_26_9"] = macd.macd()
    df["MACDh_12_26_9"]= macd.macd_diff()
    df["MACDs_12_26_9"]= macd.macd_signal()
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 5.  SCREENER ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def run_screener(
    universe_data: dict,
    max_per: float,
    max_pbv: float,
    min_volume: float,
    rsi_threshold: float,
) -> pd.DataFrame:
    """
    Filter semua kriteria swing EoD:
    1. Value      : PBV < max_pbv ATAU PER < max_per
    2. Likuiditas : Avg volume 20H > min_volume
    3. Tren       : Close > SMA 50
    4. Bounce     : Close > SMA 20
    5. Momentum   : MACD histogram cross positif ATAU RSI cross above threshold
    """
    rows = []
    for ticker, df in universe_data.items():
        df_ind = compute_indicators(df)
        if len(df_ind) < 2:
            continue

        latest = df_ind.iloc[-1]
        prev   = df_ind.iloc[-2]
        fnd    = fetch_fundamentals(ticker)
        per    = fnd["PER"]
        pbv    = fnd["PBV"]

        # 1. VALUE
        value_ok = (pbv > 0 and pbv < max_pbv) or (0 < per < max_per)

        # 2. LIKUIDITAS
        avg_vol  = df_ind["Volume"].iloc[-20:].mean()
        liq_ok   = avg_vol > min_volume

        # 3. TREN
        close    = float(latest["Close"])
        sma50    = latest.get("SMA_50", float("nan"))
        trend_ok = close > sma50 if pd.notna(sma50) else False

        # 4. BOUNCE
        sma20     = latest.get("SMA_20", float("nan"))
        bounce_ok = close > sma20 if pd.notna(sma20) else False

        # 5. MOMENTUM
        hist_now  = latest.get("MACDh_12_26_9", float("nan"))
        hist_prev = prev.get("MACDh_12_26_9",   float("nan"))
        macd_cross = (
            pd.notna(hist_now) and pd.notna(hist_prev)
            and hist_now > 0 and hist_prev <= 0
        )

        rsi_now   = latest.get("RSI_14", float("nan"))
        rsi_prev  = prev.get("RSI_14",   float("nan"))
        rsi_cross = (
            pd.notna(rsi_now) and pd.notna(rsi_prev)
            and rsi_now > rsi_threshold and rsi_prev <= rsi_threshold
        )

        momentum_ok = macd_cross or rsi_cross

        if value_ok and liq_ok and trend_ok and bounce_ok and momentum_ok:
            signals = []
            if macd_cross: signals.append("MACD Cross")
            if rsi_cross:  signals.append(f"RSI>{rsi_threshold:.0f}")
            rows.append({
                "Ticker":      ticker,
                "Nama":        fnd["name"],
                "Sektor":      fnd["sector"],
                "Close (IDR)": round(close, 0),
                "SMA 20":      round(sma20,  0) if pd.notna(sma20)    else None,
                "SMA 50":      round(sma50,  0) if pd.notna(sma50)    else None,
                "RSI (14)":    round(rsi_now, 1) if pd.notna(rsi_now) else None,
                "MACD Hist":   round(hist_now, 4) if pd.notna(hist_now) else None,
                "Vol Rata20D": int(avg_vol),
                "PER":         per,
                "PBV":         pbv,
                "Signal":      " & ".join(signals),
            })

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# 6.  PLOTLY CHART
# ──────────────────────────────────────────────────────────────────────────────

def build_chart(ticker: str, df_raw: pd.DataFrame) -> go.Figure:
    """3-panel chart: Candlestick+SMA | MACD | Volume."""
    df   = compute_indicators(df_raw)
    fnd  = fetch_fundamentals(ticker)
    name = fnd["name"]

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        vertical_spacing=0.04, row_heights=[0.60, 0.20, 0.20],
        subplot_titles=(f"{ticker} — {name}", "MACD (12,26,9)", "Volume"),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a",  decreasing_fillcolor="#ef5350",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["SMA_20"], name="SMA 20",
        line=dict(color="#f7c325", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["SMA_50"], name="SMA 50",
        line=dict(color="#2979ff", width=1.5, dash="dot"),
    ), row=1, col=1)

    hist_colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACDh_12_26_9"].fillna(0)]
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACDh_12_26_9"],
        name="Hist", marker_color=hist_colors, opacity=0.7,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_12_26_9"], name="MACD",
        line=dict(color="#2979ff", width=1.2),
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACDs_12_26_9"], name="Signal",
        line=dict(color="#ff6d00", width=1.2, dash="dot"),
    ), row=2, col=1)

    vol_colors = [
        "#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350"
        for i in range(len(df))
    ]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"],
        name="Volume", marker_color=vol_colors, opacity=0.7,
    ), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", height=750,
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(family="Courier New, monospace", color="#e0e0e0", size=11),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=30, t=60, b=40),
    )
    fig.update_yaxes(gridcolor="#1e2130", zerolinecolor="#1e2130")
    fig.update_xaxes(gridcolor="#1e2130", showspikes=True, spikecolor="#555")
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 7.  WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────

def build_webhook_payload(screened_df: pd.DataFrame) -> dict:
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
        name      = row.get("Nama", "")
        sector    = row.get("Sektor", "")
        msg = (
            f"🟢 *{ticker}* ({name})\n"
            f"   💰 Close: Rp {close_idr:,.0f}\n"
            f"   📈 RSI(14): {rsi:.1f} | MACD Hist: {macd_h:.4f}\n"
            f"   📊 PER: {per} | PBV: {pbv}\n"
            f"   🎯 Trigger: {signal}"
        )
        alerts.append({
            "ticker": ticker, "name": name, "sector": sector,
            "close_idr": float(close_idr),
            "rsi_14":    float(rsi)    if rsi    else None,
            "macd_hist": float(macd_h) if macd_h else None,
            "per": float(per), "pbv": float(pbv),
            "signal": signal, "message": msg,
        })
    return {
        "source":      "IHSG_EoD_Screener",
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "alert_count": len(alerts),
        "alerts":      alerts,
    }


def send_telegram_webhook(screened_df: pd.DataFrame, webhook_url: str) -> dict:
    payload = build_webhook_payload(screened_df)
    try:
        r = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=15,
        )
        return {"success": r.status_code == 200, "status_code": r.status_code,
                "response_text": r.text, "payload_sent": payload}
    except requests.exceptions.Timeout:
        return {"success": False, "status_code": 0, "response_text": "Timeout."}
    except Exception as exc:
        return {"success": False, "status_code": 0, "response_text": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# 8.  STREAMLIT UI
# ──────────────────────────────────────────────────────────────────────────────

def render_sidebar():
    st.sidebar.markdown(
        """
        <div style='text-align:center;padding:12px 0 6px;'>
            <span style='font-size:2rem;'>📊</span><br>
            <span style='font-size:1.1rem;font-weight:700;letter-spacing:1px;
                         color:#f7c325;'>IHSG SWING SCREENER</span><br>
            <span style='font-size:0.72rem;color:#888;'>
                End-of-Day · 300 Saham IHSG
            </span>
        </div>
        <hr style='border-color:#333;margin:8px 0;'>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.subheader("⚙️ Parameter Screener")
    max_per   = st.sidebar.slider("Max PER",  5.0, 40.0, 15.0, 0.5)
    max_pbv   = st.sidebar.slider("Max PBV",  0.5,  5.0,  1.5, 0.1)
    min_vol_m = st.sidebar.slider("Min Volume Rata-rata 20H (Juta lembar)", 1.0, 200.0, 20.0, 1.0)
    rsi_thr   = st.sidebar.slider("RSI Cross-Above Threshold", 20.0, 50.0, 35.0, 1.0)
    st.sidebar.markdown("<hr style='border-color:#333;'>", unsafe_allow_html=True)
    st.sidebar.subheader("🔔 Webhook")
    webhook_url = st.sidebar.text_input(
        "Make.com Webhook URL", value="",
        placeholder="https://hook.eu1.make.com/…", type="password",
    )
    st.sidebar.markdown(
        "<div style='font-size:0.7rem;color:#555;text-align:center;'>"
        "Data: Yahoo Finance · EoD<br>"
        "Fundamental: Auto-fetch (cache 24j)<br>"
        "Indikator: library ta · Plotly</div>",
        unsafe_allow_html=True,
    )
    return max_per, max_pbv, min_vol_m * 1_000_000, rsi_thr, webhook_url


def style_df(df: pd.DataFrame):
    def rsi_clr(v):
        if pd.isna(v): return ""
        if v < 30:  return "color:#ef5350;font-weight:bold"
        if v < 50:  return "color:#f7c325"
        return "color:#26a69a"
    def sig_clr(v):
        return "color:#26a69a;font-weight:bold" if v else ""
    fmt = {
        "Close (IDR)": "{:,.0f}", "SMA 20": "{:,.0f}", "SMA 50": "{:,.0f}",
        "RSI (14)": "{:.1f}", "MACD Hist": "{:.4f}",
        "Vol Rata20D": "{:,.0f}", "PER": "{:.1f}", "PBV": "{:.2f}",
    }
    return (
        df.style
          .applymap(rsi_clr, subset=["RSI (14)"])
          .applymap(sig_clr, subset=["Signal"])
          .format(fmt, na_rep="–")
    )


def main():
    st.markdown(
        f"""
        <div style='padding:16px 0 4px;'>
            <h1 style='margin:0;font-size:1.8rem;font-family:Courier New,monospace;
                       color:#f7c325;letter-spacing:2px;'>
                IHSG · EoD SWING SCREENER
            </h1>
            <p style='margin:4px 0 0;color:#888;font-size:0.82rem;'>
                300 Saham IHSG · End-of-Day Signal · Fundamental Auto-Fetch ·
                {datetime.now().strftime("%d %b %Y %H:%M WIB")}
            </p>
        </div>
        <hr style='border-color:#333;margin:8px 0 16px;'>
        """,
        unsafe_allow_html=True,
    )

    max_per, max_pbv, min_volume, rsi_thr, webhook_url = render_sidebar()

    # Fetch data
    st.info(
        f"⏳ Memuat {len(TICKER_UNIVERSE)} saham dari Yahoo Finance. "
        "Data di-cache 1 jam — proses ini hanya sekali per sesi."
    )
    universe_data = build_universe_data(TICKER_UNIVERSE)

    if not universe_data:
        st.error("❌ Tidak ada data. Cek koneksi internet.")
        return

    loaded = len(universe_data)
    st.caption(f"✅ {loaded} dari {len(TICKER_UNIVERSE)} ticker berhasil dimuat.")

    # Screener
    with st.spinner("🔍 Menjalankan screener…"):
        result_df = run_screener(universe_data, max_per, max_pbv, min_volume, rsi_thr)

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Universe",       loaded)
    c2.metric("Lolos Screener", len(result_df),
              delta=f"+{len(result_df)}" if len(result_df) else None)
    c3.metric("Max PER / PBV",  f"{max_per} / {max_pbv}")
    c4.metric("RSI Threshold",  f"> {rsi_thr}")
    st.markdown("---")

    # Hasil
    st.subheader("📋 Saham yang Lolos Semua Kriteria")
    if result_df.empty:
        st.info("🔎 Tidak ada saham yang lolos hari ini. Coba longgarkan parameter di sidebar.")
    else:
        st.dataframe(
            style_df(result_df), use_container_width=True,
            height=min(500, 80 + len(result_df) * 40),
        )
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name=f"IHSG_swing_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
        st.markdown("---")

        # Webhook
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            trigger = st.button("🔔 Trigger Telegram Alert", type="primary",
                                disabled=not webhook_url)
        with col_info:
            if not webhook_url:
                st.warning("⚠️ Masukkan webhook URL di sidebar.")
        if trigger and webhook_url:
            with st.spinner("Mengirim ke Make.com…"):
                res = send_telegram_webhook(result_df, webhook_url)
            if res["success"]:
                st.success(f"✅ Webhook terkirim! ({len(result_df)} alert)")
            else:
                st.error(f"❌ Gagal: {res['response_text']}")
            with st.expander("🔍 Lihat Payload JSON"):
                st.json(build_webhook_payload(result_df))

        st.markdown("---")

        # Chart
        st.subheader("📈 Chart Validasi")
        selected = st.selectbox("Pilih ticker:", options=result_df["Ticker"].tolist())
        if selected and selected in universe_data:
            with st.spinner(f"Render chart {selected}…"):
                fig = build_chart(selected, universe_data[selected])
            st.plotly_chart(fig, use_container_width=True)
            row = result_df[result_df["Ticker"] == selected].iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("PER",     row["PER"])
            m2.metric("PBV",     row["PBV"])
            m3.metric("RSI(14)", f"{row['RSI (14)']:.1f}" if pd.notna(row["RSI (14)"]) else "–")
            m4.metric("Signal",  row["Signal"])

    # Snapshot semua saham
    with st.expander(f"🌐 Snapshot Semua {loaded} Saham"):
        snap = []
        for ticker, df in universe_data.items():
            d   = compute_indicators(df).iloc[-1]
            fnd = fetch_fundamentals(ticker)
            snap.append({
                "Ticker":   ticker,
                "Nama":     fnd["name"],
                "Sektor":   fnd["sector"],
                "Close":    round(float(d["Close"]), 0),
                "SMA 20":   round(d.get("SMA_20", float("nan")), 0),
                "SMA 50":   round(d.get("SMA_50", float("nan")), 0),
                "RSI (14)": round(d.get("RSI_14",  float("nan")), 1),
                "PER":      fnd["PER"],
                "PBV":      fnd["PBV"],
            })
        st.dataframe(pd.DataFrame(snap), use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main() 