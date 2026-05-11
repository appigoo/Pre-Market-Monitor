"""
盤前監控 Pre-Market Monitor
美股盤前數據監控 | Fortune Trading Desk
v3: Groq AI + 自動週曆 + 一鍵生成 AI Prompt
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, time, timedelta
import pytz
import time as time_module
import requests
import json
import os

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="盤前監控 Pre-Market",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    :root {
        --bg:#F5F1EA; --bg2:#EDE8DF; --card:#FAF7F2; --border:#D8D0C0;
        --text:#2C2A25; --muted:#8A8278; --accent:#6B7C6E;
        --up:#3A7D5C; --up-bg:#EAF4EE;
        --down:#C0392B; --down-bg:#FDECEA;
        --flat:#8A8278; --flat-bg:#F0EDE8;
        --mono:'IBM Plex Mono',monospace; --sans:'Noto Sans TC',sans-serif;
    }
    html,body,[class*="css"]{font-family:var(--sans);background-color:var(--bg)!important;color:var(--text);}
    .stApp{background-color:var(--bg)!important;}
    #MainMenu,footer,header{visibility:hidden;}
    .block-container{padding-top:1rem!important;}

    /* Header */
    .pm-header{display:flex;align-items:baseline;justify-content:space-between;
        padding:1.2rem 0 0.6rem;border-bottom:2px solid var(--border);margin-bottom:1.2rem;}
    .pm-title{font-family:var(--mono);font-size:1.05rem;font-weight:600;
        letter-spacing:.08em;color:var(--accent);text-transform:uppercase;}
    .pm-subtitle{font-family:var(--sans);font-size:.82rem;color:var(--muted);margin-top:.15rem;}
    .pm-clock{font-family:var(--mono);font-size:.88rem;color:var(--muted);text-align:right;}
    .pm-session-badge{display:inline-block;font-family:var(--mono);font-size:.68rem;
        font-weight:600;letter-spacing:.1em;padding:.18rem .55rem;border-radius:3px;
        margin-left:.5rem;background:var(--accent);color:#FAF7F2;}

    /* Section label */
    .section-label{font-family:var(--mono);font-size:.68rem;font-weight:600;
        letter-spacing:.15em;color:var(--muted);text-transform:uppercase;
        margin:1.3rem 0 .65rem;padding-bottom:.28rem;border-bottom:1px solid var(--border);}

    /* Quote card */
    .quote-card{background:var(--card);border:1px solid var(--border);border-radius:6px;
        padding:.9rem 1.1rem;margin-bottom:.5rem;transition:box-shadow .2s;}
    .quote-card:hover{box-shadow:0 2px 12px rgba(0,0,0,.06);}
    .quote-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.38rem;}
    .quote-ticker{font-family:var(--mono);font-size:.95rem;font-weight:600;color:var(--text);letter-spacing:.05em;}
    .quote-name{font-family:var(--sans);font-size:.7rem;color:var(--muted);margin-top:.1rem;}
    .quote-price{font-family:var(--mono);font-size:1.35rem;font-weight:600;text-align:right;}
    .quote-change{font-family:var(--mono);font-size:.78rem;font-weight:500;text-align:right;margin-top:.05rem;}
    .quote-meta{display:flex;gap:1rem;font-family:var(--mono);font-size:.67rem;
        color:var(--muted);padding-top:.45rem;border-top:1px solid var(--border);flex-wrap:wrap;}
    .quote-meta span b{color:var(--text);font-weight:500;}

    /* Colors */
    .up{color:var(--up);} .down{color:var(--down);} .flat{color:var(--flat);}

    /* Pill */
    .pill{display:inline-block;padding:.12rem .42rem;border-radius:3px;
        font-family:var(--mono);font-size:.62rem;font-weight:600;letter-spacing:.05em;}
    .pill-up{background:var(--up-bg);color:var(--up);}
    .pill-down{background:var(--down-bg);color:var(--down);}
    .pill-flat{background:var(--flat-bg);color:var(--flat);}

    /* Mini cards */
    .mini-card{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.75rem 1rem;text-align:center;}
    .mini-label{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.28rem;}
    .mini-value{font-family:var(--mono);font-size:1.25rem;font-weight:600;}
    .mini-sub{font-family:var(--sans);font-size:.68rem;color:var(--muted);margin-top:.12rem;}

    /* Alert */
    .alert-box{background:#FFF8E8;border-left:3px solid #D4A017;border-radius:0 4px 4px 0;
        padding:.55rem .9rem;font-family:var(--sans);font-size:.78rem;color:#6B5000;margin-bottom:.5rem;}

    /* Signal badge */
    .signal-badge{display:inline-block;font-family:var(--mono);font-size:.6rem;font-weight:700;
        letter-spacing:.06em;padding:.12rem .45rem;border-radius:3px;margin-left:.4rem;}
    .signal-bearish{background:var(--down-bg);color:var(--down);}
    .signal-bullish{background:var(--up-bg);color:var(--up);}
    .signal-neutral{background:var(--flat-bg);color:var(--flat);}

    /* Calendar */
    .cal-wrap{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.9rem 1.1rem;margin-bottom:.6rem;}
    .cal-title{font-family:var(--mono);font-size:.68rem;font-weight:700;letter-spacing:.15em;
        text-transform:uppercase;color:var(--accent);margin-bottom:.7rem;}
    .cal-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;}
    .cal-day{border:1px solid var(--border);border-radius:5px;padding:.55rem .65rem;background:var(--bg);}
    .cal-day.today{border-color:var(--accent);background:var(--card);box-shadow:0 0 0 2px rgba(107,124,110,.15);}
    .cal-day.past{opacity:.45;}
    .cal-dayname{font-family:var(--mono);font-size:.58rem;font-weight:700;letter-spacing:.1em;
        text-transform:uppercase;color:var(--muted);margin-bottom:.08rem;}
    .cal-date{font-family:var(--mono);font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.35rem;}
    .cal-today-badge{font-family:var(--mono);font-size:.52rem;font-weight:700;background:var(--accent);
        color:#FAF7F2;padding:.03rem .32rem;border-radius:2px;letter-spacing:.06em;margin-left:.28rem;}
    .cal-event{font-family:var(--sans);font-size:.66rem;line-height:1.4;margin-bottom:.22rem;
        display:flex;gap:.28rem;align-items:flex-start;}
    .cal-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:.28rem;}
    .cal-dot.red{background:var(--down);} .cal-dot.amber{background:#D4A017;}
    .cal-dot.green{background:var(--up);} .cal-dot.blue{background:#2E6DA4;}
    .cal-dot.purple{background:#7B5EA7;}
    .cal-impact{font-family:var(--mono);font-size:.52rem;font-weight:700;padding:.03rem .28rem;
        border-radius:2px;white-space:nowrap;}
    .imp-high{background:var(--down-bg);color:var(--down);}
    .imp-med{background:#FFF8E8;color:#8B6000;}
    .imp-low{background:var(--flat-bg);color:var(--flat);}
    .cal-alert-strip{background:var(--down-bg);border-left:3px solid var(--down);border-radius:0 4px 4px 0;
        padding:.5rem .8rem;font-size:.76rem;color:var(--down);margin-top:.5rem;font-family:var(--sans);}
    .cal-source{font-family:var(--mono);font-size:.55rem;color:var(--muted);
        margin-top:.4rem;padding-top:.4rem;border-top:1px solid var(--border);}

    /* Oil */
    .oil-card{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.75rem 1rem;}
    .oil-label{font-family:var(--mono);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.22rem;}
    .oil-price{font-family:var(--mono);font-size:1.28rem;font-weight:600;}
    .oil-chg{font-family:var(--mono);font-size:.7rem;margin-top:.08rem;}
    .oil-meta{font-family:var(--mono);font-size:.6rem;color:var(--muted);margin-top:.28rem;}

    /* Intel panel */
    .intel-panel{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:1rem 1.15rem;margin-bottom:.55rem;}
    .intel-header{display:flex;justify-content:space-between;align-items:center;
        margin-bottom:.7rem;padding-bottom:.45rem;border-bottom:1px solid var(--border);}
    .intel-title{font-family:var(--mono);font-size:.72rem;font-weight:600;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;}
    .intel-time{font-family:var(--mono);font-size:.6rem;color:var(--muted);}
    .intel-summary{font-family:var(--sans);font-size:.8rem;line-height:1.7;color:var(--text);margin-bottom:.75rem;}
    .news-item{display:flex;gap:.65rem;padding:.45rem 0;border-bottom:1px solid var(--border);align-items:flex-start;}
    .news-item:last-child{border-bottom:none;}
    .news-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);margin-top:.32rem;flex-shrink:0;}
    .news-dot.red{background:var(--down);} .news-dot.amber{background:#D4A017;}
    .news-text{font-family:var(--sans);font-size:.76rem;line-height:1.5;color:var(--text);}
    .news-source{font-family:var(--mono);font-size:.58rem;color:var(--muted);margin-top:.08rem;}

    /* AI Prompt panel */
    .prompt-panel{background:#F0EDE8;border:1px solid var(--border);border-radius:6px;
        padding:1rem 1.15rem;margin-top:.5rem;}
    .prompt-title{font-family:var(--mono);font-size:.68rem;font-weight:700;letter-spacing:.1em;
        text-transform:uppercase;color:var(--accent);margin-bottom:.6rem;}
    .prompt-text{font-family:var(--mono);font-size:.72rem;line-height:1.8;color:var(--text);
        background:var(--card);border:1px solid var(--border);border-radius:4px;
        padding:.8rem 1rem;white-space:pre-wrap;word-break:break-word;}

    /* Buttons */
    .stButton>button{font-family:var(--mono)!important;font-size:.73rem!important;
        letter-spacing:.08em!important;background:var(--accent)!important;color:#FAF7F2!important;
        border:none!important;border-radius:4px!important;padding:.38rem 1rem!important;}
    [data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--border);}
    </style>
    """, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "auto_refresh": False,
    "refresh_interval": 60,
    "custom_tickers": "",
    "serper_key": os.environ.get("SERPER_API_KEY", ""),
    "groq_key": os.environ.get("GROQ_API_KEY", ""),
    "weekly_events": None,
    "weekly_events_fetched": "",   # date string when last fetched
    "ai_prompt": "",
    "show_prompt": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_num(n, d=2):
    return "—" if n is None else f"{n:,.{d}f}"

def fmt_pct(n):
    if n is None: return "—"
    return ("+" if n >= 0 else "") + f"{n:.2f}%"

def fmt_vol(n):
    if not n: return "—"
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.0f}K"
    return str(n)

def fmt_cap(n):
    if not n: return "—"
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9:  return f"${n/1e9:.1f}B"
    return f"${n/1e6:.0f}M"

def cc(v):
    return "flat" if v is None else ("up" if v > 0 else ("down" if v < 0 else "flat"))

def pc(v):
    return "pill-flat" if v is None else ("pill-up" if v > 0 else ("pill-down" if v < 0 else "pill-flat"))

def get_session_info():
    et = pytz.timezone("America/New_York")
    now_et = datetime.now(et)
    t = now_et.time()
    if   time(4,0)  <= t < time(9,30):  session = "盤前 PRE-MARKET"
    elif time(9,30) <= t < time(16,0):  session = "盤中 REGULAR"
    elif time(16,0) <= t < time(20,0):  session = "盤後 AFTER-HOURS"
    else:                                session = "休市 CLOSED"
    return now_et, session

def week_monday_str():
    et = pytz.timezone("America/New_York")
    today = datetime.now(et).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


# ── Quote fetching ────────────────────────────────────────────────────────────
def _yahoo_chart_api(ticker: str) -> dict:
    """
    Yahoo Finance v8 chart API with 1m bars + includePrePost=true.
    Scans timestamp array to extract real pre/post market closing prices.
    Uses curl_cffi chrome124 impersonation for Streamlit Cloud compatibility.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        "interval": "1m",
        "range": "1d",
        "includePrePost": "true",
        "corsDomain": "finance.yahoo.com",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        from curl_cffi import requests as curl_req
        resp = curl_req.get(url, params=params, headers=headers,
                            impersonate="chrome124", timeout=12)
    except Exception:
        resp = requests.get(url, params=params, headers=headers, timeout=12)

    data   = resp.json()
    result = data["chart"]["result"][0]
    meta   = result["meta"]

    price = meta.get("regularMarketPrice") or meta.get("previousClose")
    prev  = meta.get("chartPreviousClose") or meta.get("previousClose") or price

    # meta fields (may be present)
    pre_price  = meta.get("preMarketPrice")
    post_price = meta.get("postMarketPrice")

    # Scan 1m bars to extract pre/post prices from timestamps
    et     = pytz.timezone("America/New_York")
    now_et = datetime.now(et)
    today  = now_et.date()

    try:
        timestamps = result.get("timestamp", [])
        closes     = result["indicators"]["quote"][0].get("close", [])
        highs      = result["indicators"]["quote"][0].get("high",  [])
        lows       = result["indicators"]["quote"][0].get("low",   [])
        volumes    = result["indicators"]["quote"][0].get("volume",[])

        pre_bars  = []   # (ts, close)
        post_bars = []
        reg_highs = []
        reg_lows  = []
        reg_vols  = []

        for i, ts in enumerate(timestamps):
            cl = closes[i] if i < len(closes) else None
            hi = highs[i]  if i < len(highs)  else None
            lo = lows[i]   if i < len(lows)   else None
            vo = volumes[i]if i < len(volumes) else None
            if cl is None:
                continue
            dt = datetime.fromtimestamp(ts, tz=et)
            if dt.date() != today:
                continue
            t = dt.time()
            if time(4, 0) <= t < time(9, 30):
                pre_bars.append(cl)
            elif time(9, 30) <= t < time(16, 0):
                if hi: reg_highs.append(hi)
                if lo: reg_lows.append(lo)
                if vo: reg_vols.append(vo)
            elif time(16, 0) <= t < time(20, 0):
                post_bars.append(cl)

        if pre_bars  and pre_price  is None: pre_price  = pre_bars[-1]
        if post_bars and post_price is None: post_price = post_bars[-1]

        day_high = max(reg_highs) if reg_highs else None
        day_low  = min(reg_lows)  if reg_lows  else None
        volume   = sum(reg_vols)  if reg_vols  else None


        # Estimate avg_vol: extrapolate current pace to full 390-min session
        reg_bar_count = len(reg_vols) if reg_vols else 0
        frac = reg_bar_count / 390.0
        avg_vol = int(volume / frac) if (volume and frac > 0.05) else None
    except Exception:
        day_high = day_low = volume = avg_vol = None

    def _cp(p, base):
        if p and base:
            return p - base, (p - base) / base * 100
        return None, None

    pre_chg,  pre_pct  = _cp(pre_price,  prev)
    post_chg, post_pct = _cp(post_price, price or prev)
    reg_chg,  reg_pct  = _cp(price, prev)

    return dict(
        ticker    = ticker,
        name      = meta.get("longName") or meta.get("shortName") or ticker,
        price     = price,     prev      = prev,
        reg_chg   = reg_chg,   reg_pct   = reg_pct,
        pre_price = pre_price, pre_chg   = pre_chg,  pre_pct  = pre_pct,
        post_price= post_price,post_chg  = post_chg, post_pct = post_pct,
        high      = day_high,  low       = day_low,
        volume    = volume,    avg_vol   = avg_vol,
        cap       = None,      error     = None,
    )


    def _chg_pct(p, base):
        if p and base:
            chg = p - base
            pct = chg / base * 100
            return chg, pct
        return None, None

    pre_chg,  pre_pct  = _chg_pct(pre_price,  prev)
    post_chg, post_pct = _chg_pct(post_price, price or prev)
    reg_chg,  reg_pct  = _chg_pct(price, prev)

    # Day high/low from indicators if available
    try:
        ind   = data["chart"]["result"][0]["indicators"]["quote"][0]
        highs = [x for x in (ind.get("high") or []) if x]
        lows  = [x for x in (ind.get("low")  or []) if x]
        vols  = [x for x in (ind.get("volume") or []) if x]
        day_high = highs[-1] if highs else None
        day_low  = lows[-1]  if lows  else None
        volume   = int(vols[-1]) if vols else None
    except Exception:
        day_high = day_low = volume = None

    return dict(
        ticker    = ticker,
        name      = meta.get("longName") or meta.get("shortName") or ticker,
        price     = price,
        prev      = prev,
        reg_chg   = reg_chg,   reg_pct   = reg_pct,
        pre_price = pre_price, pre_chg   = pre_chg,  pre_pct  = pre_pct,
        post_price= post_price,post_chg  = post_chg, post_pct = post_pct,
        high      = day_high,  low       = day_low,
        volume    = volume,    avg_vol   = None,
        cap       = None,      error     = None,
    )


def _yf_download_fallback(ticker: str) -> dict:
    """Last-resort: yf.download with prepost=True to get pre/post prices."""
    df = yf.download(ticker, period="5d", interval="1m",
                     prepost=True, progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError("download returned empty")

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    et      = pytz.timezone("America/New_York")
    now_et  = datetime.now(et)
    today   = now_et.date()
    t_now   = now_et.time()

    # Filter to today
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(et)
    else:
        df.index = df.index.tz_convert(et)

    today_df = df[df.index.date == today]
    pre_df   = today_df[today_df.index.time < time(9, 30)]
    reg_df   = today_df[(today_df.index.time >= time(9, 30)) & (today_df.index.time < time(16, 0))]
    post_df  = today_df[today_df.index.time >= time(16, 0)]
    prev_df  = df[df.index.date < today]

    def _last(d, col="Close"):
        return float(d[col].iloc[-1]) if not d.empty and col in d.columns else None

    prev_close = _last(prev_df)
    reg_price  = _last(reg_df) or _last(today_df)
    pre_price  = _last(pre_df)
    post_price = _last(post_df)

    def _cp(p, base):
        if p and base: return p - base, (p - base) / base * 100
        return None, None

    pre_chg,  pre_pct  = _cp(pre_price,  prev_close)
    post_chg, post_pct = _cp(post_price, reg_price or prev_close)
    reg_chg,  reg_pct  = _cp(reg_price,  prev_close)

    return dict(
        ticker    = ticker, name = ticker,
        price     = reg_price or prev_close,
        prev      = prev_close,
        reg_chg   = reg_chg,   reg_pct   = reg_pct,
        pre_price = pre_price, pre_chg   = pre_chg,  pre_pct  = pre_pct,
        post_price= post_price,post_chg  = post_chg, post_pct = post_pct,
        high=None, low=None, volume=None, avg_vol=None, cap=None, error=None,
    )


@st.cache_data(ttl=60, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    # Skip pre/post endpoints for futures (always regular market)
    is_future = ticker.endswith("=F") or ticker.startswith("^")

    # Layer 1: Yahoo chart API (handles pre/post, cloud-friendly)
    try:
        return _yahoo_chart_api(ticker)
    except Exception:
        pass

    # Layer 2: curl_cffi + yfinance .info
    if not is_future:
        try:
            from curl_cffi import requests as curl_req
            session = curl_req.Session(impersonate="chrome110")
            t    = yf.Ticker(ticker, session=session)
            info = t.info
            if info.get("regularMarketPrice") or info.get("previousClose"):
                price     = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                prev      = info.get("previousClose") or price
                pre_price = info.get("preMarketPrice")
                pre_chg   = info.get("preMarketChange")
                pre_pct   = info.get("preMarketChangePercent")
                post_price= info.get("postMarketPrice")
                post_chg  = info.get("postMarketChange")
                post_pct  = info.get("postMarketChangePercent")
                if pre_pct  and abs(pre_pct)  < 1: pre_pct  *= 100
                if post_pct and abs(post_pct) < 1: post_pct *= 100
                reg_chg = (price - prev) if (price and prev) else None
                reg_pct = (reg_chg / prev * 100) if (reg_chg and prev) else None
                return dict(ticker=ticker,
                            name=info.get("shortName") or info.get("longName") or ticker,
                            price=price, prev=prev, reg_chg=reg_chg, reg_pct=reg_pct,
                            pre_price=pre_price, pre_chg=pre_chg, pre_pct=pre_pct,
                            post_price=post_price, post_chg=post_chg, post_pct=post_pct,
                            high=info.get("dayHigh"), low=info.get("dayLow"),
                            volume=info.get("volume"), avg_vol=info.get("averageVolume"),
                            cap=info.get("marketCap"), error=None)
        except Exception:
            pass

    # Layer 3: yf.download with prepost=True (1-min bars)
    try:
        return _yf_download_fallback(ticker)
    except Exception as e:
        return dict(ticker=ticker, error=str(e))

def render_quote_card(data, is_pre, is_post):
    if data.get("error"):
        st.markdown(
            '<div class="quote-card">' +
            f'<div class="quote-ticker">{data["ticker"]}</div>' +
            '<div class="quote-name" style="color:var(--down)">載入失敗</div></div>',
            unsafe_allow_html=True)
        return

    pm_price = data.get("pre_price")
    pm_chg   = data.get("pre_chg")
    pm_pct   = data.get("pre_pct")
    ah_price = data.get("post_price")
    ah_chg   = data.get("post_chg")
    ah_pct   = data.get("post_pct")
    reg_price= data.get("price")
    reg_chg  = data.get("reg_chg")
    reg_pct  = data.get("reg_pct")
    isFut    = data["ticker"].endswith("=F")

    et_now = datetime.now(pytz.timezone("America/New_York"))
    t_now  = et_now.time()
    is_regular = time(9, 30) <= t_now < time(16, 0)

    if is_pre and pm_price:
        dp, dc, dpct, lbl = pm_price, pm_chg, pm_pct, "盤前"
    elif is_post and ah_price:
        dp, dc, dpct, lbl = ah_price, ah_chg, ah_pct, "盤後"
    elif is_regular or isFut:
        dp, dc, dpct, lbl = reg_price, reg_chg, reg_pct, "盤中" if is_regular else "即時"
    else:
        dp, dc, dpct, lbl = reg_price, reg_chg, reg_pct, "收盤"

    sign    = "+" if (dc or 0) >= 0 else ""
    chg_str = f"{sign}{fmt_num(dc)} ({fmt_pct(dpct)})" if dc is not None else "—"

    vol, avg  = data.get("volume"), data.get("avg_vol")
    vol_ratio = f"{vol/avg:.1f}x" if (vol and avg) else "—"
    # Use CSS class instead of inline style to avoid Streamlit escaping
    if vol and avg and vol / avg > 1.5:
        vol_cls = "down"
    elif vol and avg and vol / avg > 1.0:
        vol_cls = "up"
    else:
        vol_cls = "flat"

    # Build meta spans as a single string — no f-string interpolation inside markdown
    meta_parts = [f'<span>收盤 <b>{fmt_num(reg_price)}</b></span>']
    if pm_price:
        meta_parts.append(f'<span>盤前 <b class="up">{fmt_num(pm_price)}</b></span>')
    if ah_price:
        meta_parts.append(f'<span>盤後 <b>{fmt_num(ah_price)}</b></span>')
    meta_parts.append(f'<span>高 <b>{fmt_num(data.get("high"))}</b></span>')
    meta_parts.append(f'<span>低 <b>{fmt_num(data.get("low"))}</b></span>')
    meta_parts.append(f'<span>量 <b class="{vol_cls}">{fmt_vol(vol)}</b></span>')
    meta_parts.append(f'<span>量比 <b class="{vol_cls}">{vol_ratio}</b></span>')
    meta_parts.append(f'<span>市值 <b>{fmt_cap(data.get("cap"))}</b></span>')
    meta_html = " ".join(meta_parts)

    html = (
        '<div class="quote-card">' +
        '<div class="quote-top">' +
        '<div>' +
        f'<div class="quote-ticker">{data["ticker"]} ' +
        f'<span class="pill {pc(dpct)}" style="font-size:.58rem;margin-left:.35rem">{lbl}</span></div>' +
        f'<div class="quote-name">{data["name"]}</div>' +
        '</div>' +
        '<div>' +
        f'<div class="quote-price {cc(dpct)}">{fmt_num(dp)}</div>' +
        f'<div class="quote-change {cc(dpct)}">{chg_str}</div>' +
        '</div></div>' +
        f'<div class="quote-meta">{meta_html}</div>' +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Groq AI call ──────────────────────────────────────────────────────────────
def groq_chat(prompt: str, groq_key: str, model: str = "llama-3.3-70b-versatile",
              max_tokens: int = 1200, temperature: float = 0.3) -> str:
    """Single-turn Groq chat. Returns text or raises."""
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": temperature,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── Weekly events — Groq auto-generate ───────────────────────────────────────
_FALLBACK_EVENTS = [
    {"date":"2026-05-11","weekday":"周一 MON","events":[
        {"text":"Kevin Warsh 就任美聯儲主席","color":"red","impact":"high","note":"Powell 5/15 卸任；Warsh 鷹派傾向，加息預期上移"},
        {"text":"美中貿易談判磋商（日內瓦）","color":"amber","impact":"high","note":"90天關稅暫緩窗口期談判"},
    ]},
    {"date":"2026-05-12","weekday":"周二 TUE","events":[
        {"text":"4月 CPI 數據 08:30 ET","color":"red","impact":"high","note":"預期 YoY 2.4%；低於預期→科技升，高於→沽"},
        {"text":"財政部標債拍賣","color":"blue","impact":"med","note":"結果影響殖利率走勢"},
    ]},
    {"date":"2026-05-13","weekday":"周三 WED","events":[
        {"text":"4月 PPI 數據 08:30 ET","color":"amber","impact":"high","note":"配合 CPI 判斷通脹方向"},
        {"text":"Fed 官員講話","color":"purple","impact":"med","note":"Warsh 首次表態尤其關鍵"},
        {"text":"Trump 赴北京峰會","color":"amber","impact":"high","note":"議題：貿易/台灣/伊朗/稀土"},
    ]},
    {"date":"2026-05-14","weekday":"周四 THU","events":[
        {"text":"初領失業金 08:30 ET","color":"blue","impact":"med","note":"預期 22萬"},
        {"text":"Fed 資產負債表 H.4.1","color":"blue","impact":"low","note":"每週四例行"},
        {"text":"特習峰會主要會談日","color":"red","impact":"high","note":"協議框架若達成 → 大利好 TSLA/科技"},
    ]},
    {"date":"2026-05-15","weekday":"周五 FRI","events":[
        {"text":"Powell 主席任期正式結束","color":"purple","impact":"high","note":"Warsh 接掌"},
        {"text":"4月 零售銷售 08:30 ET","color":"amber","impact":"med","note":"消費數據"},
        {"text":"特習峰會結果公佈","color":"red","impact":"high","note":"週末前最後重磅"},
    ]},
]

_WEEKDAY_MAP = ["周一 MON","周二 TUE","周三 WED","周四 THU","周五 FRI","周六 SAT","周日 SUN"]

def fetch_weekly_events(serper_key: str, groq_key: str) -> list:
    """Fetch news → Groq → structured 5-day calendar. Cached in session_state per week."""
    monday = week_monday_str()
    if st.session_state.weekly_events and st.session_state.weekly_events_fetched == monday:
        return st.session_state.weekly_events

    if not serper_key or not groq_key:
        return _FALLBACK_EVENTS

    # Step 1: Serper news
    queries = [
        "US economic calendar CPI PPI retail sales this week",
        "Federal Reserve Fed chair Warsh Powell this week",
        "Trump China Xi trade tariff meeting this week",
        "Iran war ceasefire oil price this week",
        "Trump executive order market impact this week",
    ]
    snippets = []
    for q in queries:
        try:
            r = requests.post("https://google.serper.dev/news",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": q, "num": 4, "hl": "en", "gl": "us"}, timeout=8)
            for item in r.json().get("news", []):
                snippets.append(f"[{item.get('date','')}] {item.get('title','')} — {item.get('snippet','')}")
        except Exception:
            pass

    if not snippets:
        return _FALLBACK_EVENTS

    # Step 2: Groq structures the calendar
    et = pytz.timezone("America/New_York")
    today = datetime.now(et).date()
    mon   = today - timedelta(days=today.weekday())
    dates = [(mon + timedelta(days=i)).isoformat() for i in range(5)]
    wdays = [_WEEKDAY_MAP[i] for i in range(5)]

    prompt = f"""你是美股宏觀分析師。根據以下本週新聞，為交易員生成一個五天事件日曆。

新聞（最多30條）：
{chr(10).join(snippets[:30])}

本週日期：
{', '.join(f"{d}({w})" for d,w in zip(dates,wdays))}

輸出 **純 JSON**，格式如下（不要任何其他文字或 markdown）：
[
  {{
    "date": "YYYY-MM-DD",
    "weekday": "周X XXX",
    "events": [
      {{
        "text": "事件名稱（繁體中文，含時間如 08:30 ET）",
        "color": "red|amber|blue|purple|green",
        "impact": "high|med|low",
        "note": "一句話市場影響分析（繁體中文）"
      }}
    ]
  }}
]

規則：
- 每天 1-4 個事件，只列重要事件
- color: red=重大風險/央行/地緣, amber=中等/貿易/數據, blue=例行數據, purple=聯儲官員, green=利好
- impact: high=市場必看, med=中等影響, low=參考
- note 要具體，點出對科技股/TSLA 的影響方向
- 必須包含所有五天，即使某天無重大事件也保留（events 可為空陣列）"""

    try:
        raw = groq_chat(prompt, groq_key, max_tokens=1500, temperature=0.2)
        raw = raw.replace("```json","").replace("```","").strip()
        events = json.loads(raw)
        # Validate structure
        for day in events:
            assert "date" in day and "events" in day
        st.session_state.weekly_events = events
        st.session_state.weekly_events_fetched = monday
        return events
    except Exception:
        return _FALLBACK_EVENTS


def render_weekly_calendar(events: list, source_label: str):
    et = pytz.timezone("America/New_York")
    today_str = datetime.now(et).strftime("%Y-%m-%d")

    # Today's high-impact alert strip
    for day in events:
        if day["date"] == today_str:
            high = [e for e in day.get("events",[]) if e.get("impact") == "high"]
            if high:
                alerts = " &nbsp;|&nbsp; ".join([f"⚠️ <b>{e['text']}</b>" for e in high])
                st.markdown(f'<div class="cal-alert-strip">🔔 今日高影響事件：{alerts}</div>',
                            unsafe_allow_html=True)
            break

    st.markdown('<div class="section-label">▸ 📅 本週重磅事件日曆 · 宏觀催化劑追蹤</div>',
                unsafe_allow_html=True)

    imp_map  = {"high":"imp-high","med":"imp-med","low":"imp-low"}
    imp_text = {"high":"高影響","med":"中影響","low":"低影響"}

    # Build calendar title from date range
    if events:
        d0 = datetime.strptime(events[0]["date"],"%Y-%m-%d")
        d4 = datetime.strptime(events[-1]["date"],"%Y-%m-%d")
        cal_title = f"📅 {d0.strftime('%b %-d')}–{d4.strftime('%-d, %Y')} &nbsp;· 重磅事件週"
    else:
        cal_title = "📅 本週事件"

    cal_html = f'<div class="cal-wrap"><div class="cal-title">{cal_title}</div><div class="cal-grid">'

    for day in events:
        is_today = day["date"] == today_str
        is_past  = day["date"] < today_str
        day_cls  = "cal-day today" if is_today else ("cal-day past" if is_past else "cal-day")
        date_obj  = datetime.strptime(day["date"],"%Y-%m-%d")
        date_disp = date_obj.strftime("%-d")
        today_badge = '<span class="cal-today-badge">TODAY</span>' if is_today else ""

        evs_html = ""
        for ev in day.get("events",[]):
            dot = ev.get("color","blue")
            ic  = imp_map.get(ev.get("impact","low"),"imp-low")
            il  = imp_text.get(ev.get("impact","low"),"")
            def _s(t): return (t or "").replace('"','').replace("'",'').replace("<",'').replace(">",'')
            note = _s(ev.get("note",""))
            text = _s(ev.get("text",""))
            evs_html += (
                f'<div class="cal-event" title="{note}">'
                f'<div class="cal-dot {dot}"></div>'
                f'<div><span class="cal-impact {ic}">{il}</span> {text}</div>'
                f'</div>'
            )

        cal_html += f"""
        <div class="{day_cls}">
          <div class="cal-dayname">{day['weekday']}</div>
          <div class="cal-date">{date_disp}{today_badge}</div>
          {evs_html}
        </div>"""

    cal_html += f'</div><div class="cal-source">{source_label}</div></div>'
    st.markdown(cal_html, unsafe_allow_html=True)

    with st.expander("📋 詳細事件影響分析", expanded=False):
        for day in events:
            is_today = day["date"] == today_str
            prefix = "🔴 今日 · " if is_today else ""
            for ev in day.get("events",[]):
                if ev.get("impact") == "high":
                    st.markdown(f"**{prefix}{day['weekday']} — {ev['text']}**\n> {ev.get('note','')}\n")


# ── Oil panel ─────────────────────────────────────────────────────────────────
OIL_TICKERS = {
    "CL=F": {"label":"WTI 原油","unit":"美元/桶"},
    "BZ=F": {"label":"Brent 原油","unit":"美元/桶"},
    "NG=F": {"label":"天然氣","unit":"美元/MMBtu"},
}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_oil_data() -> dict:
    results = {}
    for ticker, meta in OIL_TICKERS.items():
        try:
            info  = yf.Ticker(ticker).info
            price = info.get("regularMarketPrice") or info.get("previousClose")
            prev  = info.get("previousClose") or info.get("regularMarketPreviousClose")
            chg   = (price - prev) if (price and prev) else None
            pct   = (chg / prev * 100) if (chg and prev) else None
            results[ticker] = dict(label=meta["label"], unit=meta["unit"], price=price,
                                   chg=chg, pct=pct,
                                   high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
                                   low =info.get("dayLow")  or info.get("regularMarketDayLow"))
        except Exception as e:
            results[ticker] = dict(label=meta["label"], unit=meta["unit"], error=str(e))
    return results

def render_oil_panel():
    st.markdown('<div class="section-label">▸ 🛢️ 能源價格監控</div>', unsafe_allow_html=True)
    oil  = fetch_oil_data()
    cols = st.columns(3)
    for i, (ticker, d) in enumerate(oil.items()):
        with cols[i]:
            if d.get("error"):
                st.markdown(f'<div class="oil-card"><div class="oil-label">{d["label"]}</div>'
                            f'<div class="oil-price flat">—</div></div>', unsafe_allow_html=True)
                continue
            pct, chg = d.get("pct"), d.get("chg")
            col = "up" if (pct and pct>0) else ("down" if (pct and pct<0) else "flat")
            sign = "+" if (chg or 0) >= 0 else ""
            alert = ""
            if ticker in ("CL=F","BZ=F") and d.get("price"):
                p = d["price"]
                if   p > 100: alert = '<span class="signal-badge signal-bearish">高風險</span>'
                elif p > 90:  alert = '<span class="signal-badge signal-neutral">留意</span>'
                elif p < 80:  alert = '<span class="signal-badge signal-bullish">溫和</span>'
            st.markdown(f"""
            <div class="oil-card">
              <div class="oil-label">{d['label']} {alert}</div>
              <div class="oil-price {col}">${fmt_num(d.get('price'))}</div>
              <div class="oil-chg {col}">{sign}{fmt_num(chg)} ({fmt_pct(pct)})</div>
              <div class="oil-meta">高 {fmt_num(d.get('high'))} · 低 {fmt_num(d.get('low'))} · {d['unit']}</div>
            </div>""", unsafe_allow_html=True)

    wti = oil.get("CL=F",{})
    p, pct = wti.get("price"), wti.get("pct")
    if p and pct is not None:
        if   pct >  2: msg,bg,bc,tc = f"⚠️ WTI 急升 <b>{fmt_pct(pct)}</b>，科技股承壓，注意通脹預期上移", "#FDECEA","#C0392B","#7B1A12"
        elif pct >  0.5: msg,bg,bc,tc = f"🔶 WTI 上漲 <b>{fmt_pct(pct)}</b>，留意 TSLA/科技股壓力", "#FFF8E8","#D4A017","#6B5000"
        elif pct < -2: msg,bg,bc,tc = f"✅ WTI 下跌 <b>{fmt_pct(pct)}</b>，通脹壓力減輕，利好科技/成長股", "#EAF4EE","#3A7D5C","#1E4D35"
        else:          msg,bg,bc,tc = f"WTI 平穩 <b>{fmt_pct(pct)}</b>，能源因素對市場影響中性", "#F0EDE8","#D8D0C0","#8A8278"
        st.markdown(f'<div style="background:{bg};border-left:3px solid {bc};border-radius:0 4px 4px 0;'
                    f'padding:.5rem .85rem;font-size:.76rem;color:{tc};margin-top:.45rem">{msg}</div>',
                    unsafe_allow_html=True)


# ── News intel panel (Groq) ───────────────────────────────────────────────────
def _today_et_str() -> str:
    return datetime.now(pytz.timezone("America/New_York")).strftime("%Y-%m-%d")

@st.cache_data(ttl=180, show_spinner=False)   # 3-min cache (was 5-min)
def fetch_news(query: str, serper_key: str, num: int = 8) -> list:
    """Fetch news with today's date appended to query, filter stale articles."""
    if not serper_key: return []
    today = _today_et_str()
    # Append today's date to bias Serper toward today's results
    dated_query = f"{query} {today}"
    try:
        r = requests.post("https://google.serper.dev/news",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": dated_query, "num": num, "hl": "en", "gl": "us",
                  "tbs": "qdr:d"},   # tbs=qdr:d = past 24 hours filter
            timeout=8)
        articles = r.json().get("news", [])

        # Filter: keep only articles from today or yesterday (recency guard)
        from datetime import timedelta
        et     = pytz.timezone("America/New_York")
        now_et = datetime.now(et)
        cutoff = (now_et - timedelta(hours=36)).strftime("%Y-%m-%d")

        fresh = []
        stale = []
        for a in articles:
            date_str = a.get("date", "")
            # Serper returns relative dates like "3 hours ago", "1 day ago"
            # or absolute like "May 11, 2026" — treat missing/old as stale
            is_fresh = (
                "hour" in date_str or
                "minute" in date_str or
                "just now" in date_str.lower() or
                today in date_str or
                date_str == ""  # unknown date — include with warning
            )
            if is_fresh:
                a["_fresh"] = True
                fresh.append(a)
            else:
                a["_fresh"] = False
                stale.append(a)

        # Return fresh first; if fewer than 3 fresh, pad with stale
        result = fresh + stale
        return result[:6]
    except Exception:
        return []

@st.cache_data(ttl=180, show_spinner=False)
def groq_news_summary(articles: list, topic: str, groq_key: str) -> dict:
    if not articles or not groq_key:
        return {"summary":"","signal":"neutral","signal_reason":"","bullets":[],"tsla_impact":"","stale_warning":False}
    
    today = _today_et_str()
    
    # Tag each article with freshness for Groq context
    tagged = []
    stale_count = 0
    for a in articles[:6]:
        fresh_tag = "🟢 今日" if a.get("_fresh", True) else "🔴 舊聞"
        if not a.get("_fresh", True):
            stale_count += 1
        tagged.append(
            f"[{fresh_tag}] 標題：{a.get('title','')}\n"
            f"來源：{a.get('source','')} | 時間：{a.get('date','未知')}\n"
            f"內容：{a.get('snippet','')}"
        )
    block = "\n\n".join(tagged)
    has_stale = stale_count > len(articles[:6]) // 2  # majority stale

    prompt = f"""你是美股即時交易員分析師。今日日期：{today}（美東時間）

分析以下「{topic}」新聞，**只根據標記為🟢今日的新聞**生成摘要。
若所有新聞都是🔴舊聞，請在 summary 開頭明確說明「⚠️ 未找到今日最新消息，以下為近期背景資訊」。

新聞（已按新舊標記）：
{block}

輸出純 JSON（無其他文字、無 markdown）：
{{
  "signal": "bullish|bearish|neutral",
  "signal_reason": "一句話15字內，必須基於今日消息",
  "news_date": "最新消息的日期（如：May 11, 2026）",
  "summary": "2-3句摘要，若有舊聞混入需明確標注",
  "bullets": [
    {{"text": "重點1（含具體數字，標明來源日期）", "level": "red|amber|green"}},
    {{"text": "重點2", "level": "red|amber|green"}},
    {{"text": "重點3", "level": "red|amber|green"}}
  ],
  "tsla_impact": "對TSLA今日具體影響一句（含方向和幅度估計）",
  "stale_warning": {str(has_stale).lower()}
}}"""

    try:
        raw = groq_chat(prompt, groq_key, max_tokens=900, temperature=0.2)
        raw = raw.replace("```json","").replace("```","").strip()
        result = json.loads(raw)
        result["stale_warning"] = result.get("stale_warning", has_stale)
        return result
    except Exception:
        return {"summary":"AI 摘要失敗","signal":"neutral","signal_reason":"",
                "bullets":[],"tsla_impact":"","stale_warning":False,"news_date":""}

def render_intel_panel(title: str, query: str, serper_key: str, groq_key: str, icon: str = "📡"):
    st.markdown(f'<div class="section-label">▸ {icon} {title}</div>', unsafe_allow_html=True)
    if not serper_key:
        st.markdown('<div class="intel-panel"><div style="font-size:.75rem;color:var(--muted);text-align:center;padding:1rem">請輸入 Serper API Key</div></div>',
                    unsafe_allow_html=True)
        return
    with st.spinner(f"抓取 {title}..."):
        articles = fetch_news(query, serper_key)
    if not articles:
        st.markdown('<div class="intel-panel"><div style="color:var(--muted);font-size:.78rem;padding:.4rem">暫無最新消息</div></div>',
                    unsafe_allow_html=True)
        return
    ai = {}
    if groq_key:
        with st.spinner("Groq 分析中..."):
            ai = groq_news_summary(articles, title, groq_key)

    signal       = ai.get("signal","neutral")
    sig_reason   = ai.get("signal_reason","")
    summary      = ai.get("summary","")
    bullets      = ai.get("bullets",[])
    tsla_imp     = ai.get("tsla_impact","")
    news_date    = ai.get("news_date","")
    stale_warn   = ai.get("stale_warning", False)
    sig_cls  = {"bullish":"signal-bullish","bearish":"signal-bearish"}.get(signal,"signal-neutral")
    sig_text = {"bullish":"▲ 利多","bearish":"▼ 利空","neutral":"◆ 中性"}.get(signal,"◆ 中性")
    now_str  = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M ET")
    today    = _today_et_str()

    # Count fresh vs stale articles
    fresh_count = sum(1 for a in articles if a.get("_fresh", True))
    total_count = len(articles)

    html = '<div class="intel-panel">'
    html += f'<div class="intel-header">'
    html += f'<div class="intel-title">{title}<span class="signal-badge {sig_cls}">{sig_text} {sig_reason}</span></div>'
    
    # Freshness indicator
    if fresh_count == total_count:
        freshness = f'<span style="color:var(--up);font-size:.6rem">● 全部今日</span>'
    elif fresh_count == 0:
        freshness = f'<span style="color:var(--down);font-size:.6rem">⚠ 無今日消息</span>'
    else:
        freshness = f'<span style="color:#D4A017;font-size:.6rem">◑ {fresh_count}/{total_count} 今日</span>'
    html += f'<div class="intel-time">{freshness} &nbsp;Groq · {now_str}</div>'
    html += '</div>'

    # Stale warning banner
    if stale_warn or fresh_count == 0:
        html += ('<div style="background:#FFF3CD;border-left:3px solid #D4A017;border-radius:0 4px 4px 0;'
                 'padding:.4rem .8rem;font-size:.72rem;color:#856404;margin-bottom:.6rem">'
                 f'⚠️ 未找到 {today} 的最新消息，以下為近期背景資訊，請自行核實最新發展</div>')

    if summary:
        html += f'<div class="intel-summary">{summary}</div>'

    if bullets:
        for b in bullets:
            dc = {"red":"red","amber":"amber"}.get(b.get("level",""),"")
            html += (f'<div class="news-item"><div class="news-dot {dc}"></div>'
                     f'<div><div class="news-text">{b.get("text","")}</div></div></div>')
    
    # Always show raw article headlines with date tags
    html += '<div style="margin-top:.6rem;padding-top:.5rem;border-top:1px solid var(--border)">'
    for a in articles[:5]:
        is_fresh = a.get("_fresh", True)
        dot_col  = "var(--up)" if is_fresh else "var(--down)"
        date_col = "var(--up)" if is_fresh else "var(--down)"
        tag      = "今日" if is_fresh else "舊聞"
        html += (f'<div class="news-item">'
                 f'<div class="news-dot" style="background:{dot_col}"></div>'
                 f'<div>'
                 f'<div class="news-text">{a.get("title","")}</div>'
                 f'<div class="news-source" style="color:{date_col}">[{tag}] {a.get("source","")} · {a.get("date","")}</div>'
                 f'</div></div>')
    html += '</div>'

    if tsla_imp:
        html += ('<div style="margin-top:.65rem;padding-top:.55rem;border-top:1px solid var(--border);'
                 'font-family:var(--mono,monospace);font-size:.68rem;color:var(--muted)">'
                 f'🚗 TSLA 影響：<span style="color:var(--text)">{tsla_imp}</span></div>')
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── AI Prompt Generator ───────────────────────────────────────────────────────
def generate_trading_prompt(events: list, oil_data: dict,
                             tsla_data: dict, vix_data: dict,
                             qqq_data: dict, is_pre: bool) -> str:
    """Build a rich, ready-to-paste prompt for any AI chatbot."""
    et       = pytz.timezone("America/New_York")
    now_et   = datetime.now(et)
    today_str = now_et.strftime("%Y-%m-%d")
    time_str  = now_et.strftime("%H:%M ET")
    session   = "盤前" if is_pre else "盤中/盤後"

    # Today's events
    today_events = []
    for day in events:
        if day["date"] == today_str:
            today_events = day.get("events", [])
            break
    events_lines = "\n".join(
        [f"  - [{e.get('impact','').upper()}] {e['text']} — {e.get('note','')}"
         for e in today_events]
    ) or "  （今日無已知重大事件）"

    # Market snapshot — smart: show pre > reg > prev in that priority
    def snap(d):
        if not d or d.get("error"): return "N/A"
        # Pick best available price + pct
        if d.get("pre_price") and d.get("pre_pct") is not None:
            p, pct, tag = d["pre_price"], d["pre_pct"], "盤前"
        elif d.get("post_price") and d.get("post_pct") is not None:
            p, pct, tag = d["post_price"], d["post_pct"], "盤後"
        elif d.get("price") and d.get("reg_pct") is not None:
            p, pct, tag = d["price"], d["reg_pct"], "收盤"
        else:
            p   = d.get("price") or d.get("prev")
            pct = None
            tag = "收盤"
        pct_str = fmt_pct(pct) if pct is not None else "—"
        return f"{fmt_num(p)} {pct_str} [{tag}]"

    wti   = oil_data.get("CL=F", {}) if oil_data else {}
    brent = oil_data.get("BZ=F", {}) if oil_data else {}

    # Today high-impact events for prompt
    high_events = [e for e in today_events if e.get("impact") == "high"]
    _nl = chr(10)
    high_lines = _nl.join(
        [f"  ⚠️ {e['text']} — {e.get('note','')}" for e in high_events]
    ) or "  （今日無已確認高影響事件）"

    tsla_snap = snap(tsla_data) if tsla_data else "N/A"
    qqq_snap  = snap(qqq_data)  if qqq_data  else "N/A"
    vix_val   = fmt_num(vix_data.get("price")) if vix_data and not vix_data.get("error") else "N/A"
    wti_str   = f"${fmt_num(wti.get('price'))} ({fmt_pct(wti.get('pct'))})" if wti.get("price") else "N/A"
    brent_str = f"${fmt_num(brent.get('price'))} ({fmt_pct(brent.get('pct'))})" if brent.get("price") else "N/A"

    prompt = f"""# 美股即時分析請求
日期：{today_str}  時間：{time_str}  時段：{session}

## 今日全部宏觀事件
{events_lines}

## 今日高影響事件（重點）
{high_lines}

## 市場即時快照
| 指標 | 數值 |
|------|------|
| TSLA | {tsla_snap} |
| QQQ  | {qqq_snap} |
| VIX  | {vix_val} |
| WTI 原油 | {wti_str} |
| Brent 原油 | {brent_str} |

## 請幫我分析：
1. **今日最大風險/機會**是什麼？對 TSLA 和納指方向的影響？
2. **油價急升 {wti_str}** 對今日科技股有何具體影響？
3. **TSLA 今日交易策略**：建議入場區間、止損位、目標位（$數字）？
4. **VIX {vix_val}** 顯示市場情緒如何？適合做多/做空/觀望？
5. 今日最需要關注的**時間點**（數據發布/官員講話/峰會消息）？

請用繁體中文回答，要具體，每點包含數字區間。"""
    return prompt


# ── Watchlists ────────────────────────────────────────────────────────────────
WATCHLISTS = {
    "核心持倉": [("TSLA","特斯拉"),("NVDA","輝達"),("AAPL","蘋果"),("MSFT","微軟"),("AMZN","亞馬遜")],
    "指數ETF":  [("QQQ","納指100 ETF"),("SPY","標普500 ETF"),("IWM","羅素2000 ETF"),("DIA","道指 ETF")],
    "波動/恐慌":[("^VIX","VIX 恐慌指數"),("UVXY","短期波動 2x"),("SQQQ","納指3x反向"),("TQQQ","納指3x正向")],
    "槓桿ETF":  [("TSLL","TSLA 2x多"),("SOXL","半導體3x"),("FNGU","科技8x")],
    "期貨代理": [("NQ=F","納指期貨"),("ES=F","標普期貨"),("YM=F","道指期貨"),("GC=F","黃金期貨"),("CL=F","原油期貨")],
}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    now_et, session = get_session_info()
    is_pre  = "盤前" in session
    is_post = "盤後" in session

    # Header
    st.markdown(f"""
    <div class="pm-header">
      <div>
        <div class="pm-title">📅 Pre-Market Monitor
          <span class="pm-session-badge">{session}</span>
        </div>
        <div class="pm-subtitle">美股盤前即時監控 · Fortune Trading Desk · Groq AI</div>
      </div>
      <div class="pm-clock">{now_et.strftime('%Y-%m-%d')}<br><b>{now_et.strftime('%H:%M:%S')} ET</b></div>
    </div>""", unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ 設定")
        auto = st.toggle("自動刷新", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto
        if auto:
            iv = st.selectbox("刷新頻率",[30,60,120,300],index=1,format_func=lambda x:f"{x} 秒")
            st.session_state.refresh_interval = iv

        st.markdown("---")
        st.markdown("### 🔑 API 設定")
        sk = st.text_input("Serper API Key", value=st.session_state.serper_key,
                           type="password", placeholder="新聞抓取 — serper.dev 免費",
                           help="https://serper.dev — 每月 2500 次免費")
        st.session_state.serper_key = sk
        gk = st.text_input("Groq API Key", value=st.session_state.groq_key,
                           type="password", placeholder="AI 摘要 — groq.com 免費",
                           help="https://console.groq.com — 完全免費")
        st.session_state.groq_key = gk

        st.markdown("---")
        st.markdown("### 📋 自訂股票")
        custom = st.text_area("輸入代號（換行分隔）", value=st.session_state.custom_tickers,
                              height=90, placeholder="例如:\nGOOGL\nMETA")
        st.session_state.custom_tickers = custom

        st.markdown("---")
        st.markdown("### 顯示選項")
        show_futures = st.checkbox("期貨代理",      value=True)
        show_vix     = st.checkbox("波動/恐慌",     value=True)
        show_lev     = st.checkbox("槓桿ETF",       value=False)
        show_oil     = st.checkbox("能源價格",       value=True)
        show_trump   = st.checkbox("Trump 消息",    value=True)
        show_iran    = st.checkbox("伊朗/油價新聞", value=True)

        st.markdown("---")
        if st.button("🔄 立即刷新"):
            st.cache_data.clear()
            st.session_state.weekly_events = None
            st.rerun()
        if st.button("🗓️ 重新生成週曆"):
            st.session_state.weekly_events = None
            st.session_state.weekly_events_fetched = ""
            st.rerun()

    # ── Session alert ─────────────────────────────────────────────────────
    if is_pre:
        st.markdown('<div class="alert-box">⏰ <b>盤前交易時段</b> — 流動性較低，請注意風險管理</div>',
                    unsafe_allow_html=True)
    elif is_post:
        st.markdown('<div class="alert-box">🌙 <b>盤後交易時段</b> — 財報/消息驅動，缺口風險較高</div>',
                    unsafe_allow_html=True)

    # ── Weekly calendar (AI auto-generated) ───────────────────────────────
    with st.spinner("📅 載入本週事件日曆..."):
        events = fetch_weekly_events(st.session_state.serper_key, st.session_state.groq_key)
    is_ai = bool(st.session_state.serper_key and st.session_state.groq_key
                 and st.session_state.weekly_events)
    source_label = "✨ Groq AI 自動生成 · 每週一自動更新" if is_ai else "📋 內置數據 · 輸入 Serper + Groq Key 啟用自動更新"
    render_weekly_calendar(events, source_label)

    # ── 🤖 AI Prompt Generator button ─────────────────────────────────────
    st.markdown('<div class="section-label">▸ 🤖 AI 交易分析助手</div>', unsafe_allow_html=True)

    col_btn1, col_btn2, col_space = st.columns([1.5, 1.5, 5])
    with col_btn1:
        if st.button("✨ 一鍵生成 AI Prompt"):
            with st.spinner("整合市場數據中..."):
                oil_data  = fetch_oil_data()
                tsla_data = fetch_quote("TSLA")
                vix_data  = fetch_quote("^VIX")
                qqq_data  = fetch_quote("QQQ")
            prompt = generate_trading_prompt(events, oil_data, tsla_data, vix_data, qqq_data, is_pre)
            st.session_state.ai_prompt = prompt
            st.session_state.show_prompt = True
    with col_btn2:
        if st.session_state.show_prompt and st.button("❌ 隱藏 Prompt"):
            st.session_state.show_prompt = False

    if st.session_state.show_prompt and st.session_state.ai_prompt:
        st.markdown(f"""
        <div class="prompt-panel">
          <div class="prompt-title">📋 複製以下 Prompt，貼入 ChatGPT / Claude / Gemini</div>
          <div class="prompt-text">{st.session_state.ai_prompt}</div>
        </div>""", unsafe_allow_html=True)
        st.code(st.session_state.ai_prompt, language="markdown")
        st.caption("👆 點擊右上角複製圖示即可一鍵複製")

    # ── Stock sections ────────────────────────────────────────────────────
    all_sections = {"核心持倉": WATCHLISTS["核心持倉"], "指數ETF": WATCHLISTS["指數ETF"]}
    if show_vix:     all_sections["波動/恐慌"] = WATCHLISTS["波動/恐慌"]
    if show_lev:     all_sections["槓桿ETF"]   = WATCHLISTS["槓桿ETF"]
    if show_futures: all_sections["期貨代理"]   = WATCHLISTS["期貨代理"]
    if st.session_state.custom_tickers.strip():
        custom_list = [(l.strip().upper(),"") for l in st.session_state.custom_tickers.strip().split("\n") if l.strip()]
        if custom_list: all_sections["自訂監控"] = custom_list

    for sec, tickers in all_sections.items():
        st.markdown(f'<div class="section-label">▸ {sec}</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, (ticker, _) in enumerate(tickers):
            with cols[i % 2]:
                render_quote_card(fetch_quote(ticker), is_pre, is_post)

    # ── Oil panel ─────────────────────────────────────────────────────────
    if show_oil:
        render_oil_panel()

    # ── Intel panels ──────────────────────────────────────────────────────
    sk, gk = st.session_state.serper_key, st.session_state.groq_key
    _today = _today_et_str()
    if show_trump:
        render_intel_panel("Trump 最新表態監控",
            f"Trump Truth Social statement stock market {_today}", sk, gk, "🇺🇸")
    if show_iran:
        render_intel_panel("伊朗戰爭 · 油價消息",
            f"Iran war oil price Hormuz ceasefire {_today}", sk, gk, "🛢️")

    # ── Quick summary bar ─────────────────────────────────────────────────
    st.markdown('<div class="section-label">▸ 快速指標</div>', unsafe_allow_html=True)
    vd = fetch_quote("^VIX"); sd = fetch_quote("SPY")
    qd = fetch_quote("QQQ");  td = fetch_quote("TSLA")
    m1,m2,m3,m4 = st.columns(4)

    def mini(col, lbl, val, sub, col_cls=""):
        col.markdown(f'<div class="mini-card"><div class="mini-label">{lbl}</div>'
                     f'<div class="mini-value {col_cls}">{val}</div>'
                     f'<div class="mini-sub">{sub}</div></div>', unsafe_allow_html=True)

    # Smart pct: pre > reg > post, whichever is available; label follows
    def best_pct(d):
        """Return (pct, price, label) using best available session data."""
        if not d or d.get("error"):
            return None, None, "—"
        et_t = datetime.now(pytz.timezone("America/New_York")).time()
        _is_reg = time(9, 30) <= et_t < time(16, 0)
        if d.get("pre_pct") is not None and not _is_reg:
            return d["pre_pct"], d.get("pre_price") or d.get("price"), "盤前"
        if d.get("reg_pct") is not None:
            return d["reg_pct"], d.get("price"), "盤中" if _is_reg else "收盤"
        if d.get("pre_pct") is not None:
            return d["pre_pct"], d.get("pre_price") or d.get("price"), "盤前"
        if d.get("post_pct") is not None:
            return d["post_pct"], d.get("post_price"), "盤後"
        return None, d.get("price"), "—"

    vp = vd.get("price")
    vc = "down" if (vp and vp>25) else ("up" if (vp and vp<18) else "flat")
    vl = "極度恐慌" if (vp and vp>30) else ("恐慌" if (vp and vp>20) else "平靜")
    mini(m1,"VIX 恐慌",fmt_num(vp),vl,vc)

    sp, sprice, slbl = best_pct(sd)
    mini(m2, f"SPY {slbl}%", fmt_pct(sp),
         f"收盤 {fmt_num(sd.get('price'))}", cc(sp))

    qp, qprice, qlbl = best_pct(qd)
    mini(m3, f"QQQ {qlbl}%", fmt_pct(qp),
         f"收盤 {fmt_num(qd.get('price'))}", cc(qp))

    tp, tprice, tlbl = best_pct(td)
    mini(m4, f"TSLA {tlbl}%", fmt_pct(tp),
         f"收盤 {fmt_num(td.get('price'))}", cc(tp))

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-family:var(--mono,monospace);font-size:.62rem;color:#AAA49C;
         text-align:center;padding:1.8rem 0 .8rem;border-top:1px solid #D8D0C0;margin-top:1.8rem">
      最後更新 {datetime.now().strftime('%H:%M:%S')} · 股價延遲 15-20 分鐘 · Groq AI 免費版 · 僅供參考，不構成投資建議
    </div>""", unsafe_allow_html=True)

    # ── Auto refresh ──────────────────────────────────────────────────────
    if st.session_state.auto_refresh:
        time_module.sleep(st.session_state.refresh_interval)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
