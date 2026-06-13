"""
盤前監控 Pre-Market Monitor
美股盤前數據監控 | Fortune Trading Desk
v4: 全面升級 — st_autorefresh · 價位警報 · VIX歷史對比 · 深色模式
     · 恐懼貪婪指數 · 新聞手動刷新 · 週曆排序 · Prompt複製反饋
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
import html as _html

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="盤前監控 Pre-Market",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "auto_refresh":          False,
    "refresh_interval":      60,
    "custom_tickers":        "",
    "serper_key":            os.environ.get("SERPER_API_KEY", ""),
    "groq_key":              os.environ.get("GROQ_API_KEY", ""),
    "weekly_events":         None,
    "weekly_events_fetched": "",
    "ai_prompt":             "",
    "show_prompt":           False,
    "dark_mode":             False,
    # price alerts: list of {"ticker","direction","price","label"}
    "price_alerts":          [],
    "alert_ticker":          "TSLA",
    "alert_price":           "",
    "alert_dir":             "突破上方",
    # news panel manual-refresh timestamps {panel_title: epoch}
    "news_refresh":          {},
    # copy feedback
    "prompt_copied":         False,
    "prompt_copied_at":      0.0,
    # VIX yesterday cache
    "vix_prev":              None,
    "vix_prev_date":         "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Theme helpers ─────────────────────────────────────────────────────────────
def _theme():
    if st.session_state.dark_mode:
        return {
            "--bg":"#1A1A1A","--bg2":"#141414","--card":"#222222","--border":"#333333",
            "--text":"#E8E4DC","--muted":"#7A7570","--accent":"#7A9E7E",
            "--up":"#4CAF7A","--up-bg":"#0D2B1A",
            "--down":"#E05252","--down-bg":"#2B0D0D",
            "--flat":"#7A7570","--flat-bg":"#2A2A2A",
        }
    return {
        "--bg":"#F5F1EA","--bg2":"#EDE8DF","--card":"#FAF7F2","--border":"#D8D0C0",
        "--text":"#2C2A25","--muted":"#8A8278","--accent":"#6B7C6E",
        "--up":"#3A7D5C","--up-bg":"#EAF4EE",
        "--down":"#C0392B","--down-bg":"#FDECEA",
        "--flat":"#8A8278","--flat-bg":"#F0EDE8",
    }


# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css():
    t = _theme()
    vars_css = "\n".join(f"    {k}:{v};" for k,v in t.items())
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
    :root {{
{vars_css}
        --mono:'IBM Plex Mono',monospace; --sans:'Noto Sans TC',sans-serif;
    }}
    html,body,[class*="css"]{{font-family:var(--sans);background-color:var(--bg)!important;color:var(--text);}}
    .stApp{{background-color:var(--bg)!important;}}
    #MainMenu,footer,header{{visibility:hidden;}}
    .block-container{{padding-top:1rem!important;}}

    .pm-header{{display:flex;align-items:baseline;justify-content:space-between;
        padding:1.2rem 0 0.6rem;border-bottom:2px solid var(--border);margin-bottom:1.2rem;}}
    .pm-title{{font-family:var(--mono);font-size:1.05rem;font-weight:600;
        letter-spacing:.08em;color:var(--accent);text-transform:uppercase;}}
    .pm-subtitle{{font-family:var(--sans);font-size:.82rem;color:var(--muted);margin-top:.15rem;}}
    .pm-clock{{font-family:var(--mono);font-size:.88rem;color:var(--muted);text-align:right;}}
    .pm-session-badge{{display:inline-block;font-family:var(--mono);font-size:.68rem;
        font-weight:600;letter-spacing:.1em;padding:.18rem .55rem;border-radius:3px;
        margin-left:.5rem;background:var(--accent);color:var(--bg);}}

    .section-label{{font-family:var(--mono);font-size:.68rem;font-weight:600;
        letter-spacing:.15em;color:var(--muted);text-transform:uppercase;
        margin:1.3rem 0 .65rem;padding-bottom:.28rem;border-bottom:1px solid var(--border);}}

    .quote-card{{background:var(--card);border:1px solid var(--border);border-radius:6px;
        padding:.9rem 1.1rem;margin-bottom:.5rem;transition:box-shadow .2s;}}
    .quote-card:hover{{box-shadow:0 2px 12px rgba(0,0,0,.1);}}
    .quote-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.38rem;}}
    .quote-ticker{{font-family:var(--mono);font-size:.95rem;font-weight:600;color:var(--text);letter-spacing:.05em;}}
    .quote-name{{font-family:var(--sans);font-size:.7rem;color:var(--muted);margin-top:.1rem;}}
    .quote-price{{font-family:var(--mono);font-size:1.35rem;font-weight:600;text-align:right;}}
    .quote-change{{font-family:var(--mono);font-size:.78rem;font-weight:500;text-align:right;margin-top:.05rem;}}
    .quote-meta{{display:flex;gap:1rem;font-family:var(--mono);font-size:.67rem;
        color:var(--muted);padding-top:.45rem;border-top:1px solid var(--border);flex-wrap:wrap;}}
    .quote-meta span b{{color:var(--text);font-weight:500;}}

    .up{{color:var(--up);}} .down{{color:var(--down);}} .flat{{color:var(--flat);}}

    .pill{{display:inline-block;padding:.12rem .42rem;border-radius:3px;
        font-family:var(--mono);font-size:.62rem;font-weight:600;letter-spacing:.05em;}}
    .pill-up{{background:var(--up-bg);color:var(--up);}}
    .pill-down{{background:var(--down-bg);color:var(--down);}}
    .pill-flat{{background:var(--flat-bg);color:var(--flat);}}

    .mini-card{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.75rem 1rem;text-align:center;}}
    .mini-label{{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.28rem;}}
    .mini-value{{font-family:var(--mono);font-size:1.25rem;font-weight:600;}}
    .mini-sub{{font-family:var(--sans);font-size:.68rem;color:var(--muted);margin-top:.12rem;}}

    .alert-box{{background:var(--flat-bg);border-left:3px solid #D4A017;border-radius:0 4px 4px 0;
        padding:.55rem .9rem;font-family:var(--sans);font-size:.78rem;color:var(--text);margin-bottom:.5rem;}}

    .signal-badge{{display:inline-block;font-family:var(--mono);font-size:.6rem;font-weight:700;
        letter-spacing:.06em;padding:.12rem .45rem;border-radius:3px;margin-left:.4rem;}}
    .signal-bearish{{background:var(--down-bg);color:var(--down);}}
    .signal-bullish{{background:var(--up-bg);color:var(--up);}}
    .signal-neutral{{background:var(--flat-bg);color:var(--flat);}}

    /* PRICE ALERT BANNER */
    .price-alert-banner{{background:var(--down-bg);border:2px solid var(--down);border-radius:6px;
        padding:.7rem 1rem;font-family:var(--mono);font-size:.8rem;font-weight:600;
        color:var(--down);margin-bottom:.5rem;display:flex;align-items:center;gap:.6rem;
        animation:flashAlert 1s ease-in-out 3;}}
    @keyframes flashAlert{{0%,100%{{opacity:1;}}50%{{opacity:.4;}}}}

    /* FEAR & GREED */
    .fg-card{{background:var(--card);border:1px solid var(--border);border-radius:6px;
        padding:.9rem 1.1rem;margin-bottom:.5rem;}}
    .fg-label{{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;
        color:var(--muted);margin-bottom:.5rem;}}
    .fg-meter{{width:100%;height:10px;border-radius:5px;background:linear-gradient(90deg,
        #C0392B 0%,#E67E22 25%,#F1C40F 50%,#27AE60 75%,#2ECC71 100%);
        margin:.4rem 0;position:relative;}}
    .fg-needle{{position:absolute;top:-3px;width:4px;height:16px;background:var(--text);
        border-radius:2px;transform:translateX(-50%);transition:left .5s;}}
    .fg-value{{font-family:var(--mono);font-size:1.4rem;font-weight:700;}}
    .fg-sentiment{{font-family:var(--sans);font-size:.75rem;color:var(--muted);margin-top:.12rem;}}

    /* VIX DELTA */
    .vix-delta{{font-family:var(--mono);font-size:.65rem;margin-top:.08rem;}}

    /* CALENDAR */
    .cal-wrap{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.9rem 1.1rem;margin-bottom:.6rem;}}
    .cal-title{{font-family:var(--mono);font-size:.68rem;font-weight:700;letter-spacing:.15em;
        text-transform:uppercase;color:var(--accent);margin-bottom:.7rem;}}
    .cal-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;}}
    .cal-day{{border:1px solid var(--border);border-radius:5px;padding:.55rem .65rem;background:var(--bg);}}
    .cal-day.today{{border-color:var(--accent);background:var(--card);box-shadow:0 0 0 2px rgba(107,124,110,.15);}}
    .cal-day.past{{opacity:.45;}}
    .cal-dayname{{font-family:var(--mono);font-size:.58rem;font-weight:700;letter-spacing:.1em;
        text-transform:uppercase;color:var(--muted);margin-bottom:.08rem;}}
    .cal-date{{font-family:var(--mono);font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.35rem;}}
    .cal-today-badge{{font-family:var(--mono);font-size:.52rem;font-weight:700;background:var(--accent);
        color:var(--bg);padding:.03rem .32rem;border-radius:2px;letter-spacing:.06em;margin-left:.28rem;}}
    .cal-event{{font-family:var(--sans);font-size:.66rem;line-height:1.4;margin-bottom:.22rem;
        display:flex;gap:.28rem;align-items:flex-start;}}
    .cal-dot{{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:.28rem;}}
    .cal-dot.red{{background:var(--down);}} .cal-dot.amber{{background:#D4A017;}}
    .cal-dot.green{{background:var(--up);}} .cal-dot.blue{{background:#2E6DA4;}}
    .cal-dot.purple{{background:#7B5EA7;}}
    .cal-impact{{font-family:var(--mono);font-size:.52rem;font-weight:700;padding:.03rem .28rem;
        border-radius:2px;white-space:nowrap;}}
    .imp-high{{background:var(--down-bg);color:var(--down);}}
    .imp-med{{background:#FFF8E8;color:#8B6000;}}
    .imp-low{{background:var(--flat-bg);color:var(--flat);}}
    .cal-alert-strip{{background:var(--down-bg);border-left:3px solid var(--down);border-radius:0 4px 4px 0;
        padding:.5rem .8rem;font-size:.76rem;color:var(--down);margin-top:.5rem;font-family:var(--sans);}}
    .cal-source{{font-family:var(--mono);font-size:.55rem;color:var(--muted);
        margin-top:.4rem;padding-top:.4rem;border-top:1px solid var(--border);}}

    .oil-card{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:.75rem 1rem;}}
    .oil-label{{font-family:var(--mono);font-size:.6rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:.22rem;}}
    .oil-price{{font-family:var(--mono);font-size:1.28rem;font-weight:600;}}
    .oil-chg{{font-family:var(--mono);font-size:.7rem;margin-top:.08rem;}}
    .oil-meta{{font-family:var(--mono);font-size:.6rem;color:var(--muted);margin-top:.28rem;}}

    .intel-panel{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:1rem 1.15rem;margin-bottom:.55rem;}}
    .intel-header{{display:flex;justify-content:space-between;align-items:center;
        margin-bottom:.7rem;padding-bottom:.45rem;border-bottom:1px solid var(--border);}}
    .intel-title{{font-family:var(--mono);font-size:.72rem;font-weight:600;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;}}
    .intel-time{{font-family:var(--mono);font-size:.6rem;color:var(--muted);}}
    .intel-summary{{font-family:var(--sans);font-size:.8rem;line-height:1.7;color:var(--text);margin-bottom:.75rem;}}
    .news-item{{display:flex;gap:.65rem;padding:.45rem 0;border-bottom:1px solid var(--border);align-items:flex-start;}}
    .news-item:last-child{{border-bottom:none;}}
    .news-dot{{width:6px;height:6px;border-radius:50%;background:var(--accent);margin-top:.32rem;flex-shrink:0;}}
    .news-dot.red{{background:var(--down);}} .news-dot.amber{{background:#D4A017;}}
    .news-text{{font-family:var(--sans);font-size:.76rem;line-height:1.5;color:var(--text);}}
    .news-source{{font-family:var(--mono);font-size:.58rem;color:var(--muted);margin-top:.08rem;}}

    .prompt-panel{{background:var(--bg2);border:1px solid var(--border);border-radius:6px;
        padding:1rem 1.15rem;margin-top:.5rem;}}
    .prompt-title{{font-family:var(--mono);font-size:.68rem;font-weight:700;letter-spacing:.1em;
        text-transform:uppercase;color:var(--accent);margin-bottom:.6rem;}}

    /* COPY TOAST */
    .copy-toast{{background:var(--up-bg);border:1px solid var(--up);border-radius:4px;
        padding:.35rem .75rem;font-family:var(--mono);font-size:.7rem;color:var(--up);
        display:inline-block;margin-left:.8rem;}}

    /* ALERT PANEL */
    .alert-panel{{background:var(--card);border:1px solid var(--border);border-radius:6px;
        padding:.8rem 1rem;margin-bottom:.5rem;}}
    .alert-row{{display:flex;justify-content:space-between;align-items:center;
        padding:.3rem 0;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:.72rem;}}
    .alert-row:last-child{{border-bottom:none;}}

    .stButton>button{{font-family:var(--mono)!important;font-size:.73rem!important;
        letter-spacing:.08em!important;background:var(--accent)!important;color:var(--bg)!important;
        border:none!important;border-radius:4px!important;padding:.38rem 1rem!important;}}
    [data-testid="stSidebar"]{{background:var(--bg2)!important;border-right:1px solid var(--border);}}
    </style>
    """, unsafe_allow_html=True)


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
    elif time(20,0) <= t or t < time(4,0): session = "隔夜 OVERNIGHT"
    else:                                session = "休市 CLOSED"
    return now_et, session

def week_monday_str():
    et = pytz.timezone("America/New_York")
    today = datetime.now(et).date()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()

def _today_et_str():
    return datetime.now(pytz.timezone("America/New_York")).strftime("%Y-%m-%d")


# ── Quote fetching ────────────────────────────────────────────────────────────
def _yahoo_chart_api(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval":"1m","range":"1d","includePrePost":"true","corsDomain":"finance.yahoo.com"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://finance.yahoo.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        from curl_cffi import requests as curl_req
        resp = curl_req.get(url, params=params, headers=headers, impersonate="chrome124", timeout=12)
    except Exception:
        resp = requests.get(url, params=params, headers=headers, timeout=12)

    data   = resp.json()
    result = data["chart"]["result"][0]
    meta   = result["meta"]
    price  = meta.get("regularMarketPrice") or meta.get("previousClose")
    prev   = meta.get("chartPreviousClose") or meta.get("previousClose") or price
    pre_price  = meta.get("preMarketPrice")
    post_price = meta.get("postMarketPrice")

    et     = pytz.timezone("America/New_York")
    today  = datetime.now(et).date()
    day_high = day_low = volume = avg_vol = None
    try:
        timestamps = result.get("timestamp", [])
        closes  = result["indicators"]["quote"][0].get("close",  [])
        highs   = result["indicators"]["quote"][0].get("high",   [])
        lows    = result["indicators"]["quote"][0].get("low",    [])
        volumes = result["indicators"]["quote"][0].get("volume", [])
        pre_bars = []; post_bars = []
        reg_highs = []; reg_lows = []; reg_vols = []
        for i, ts in enumerate(timestamps):
            cl = closes[i]  if i < len(closes)  else None
            hi = highs[i]   if i < len(highs)   else None
            lo = lows[i]    if i < len(lows)     else None
            vo = volumes[i] if i < len(volumes)  else None
            if cl is None: continue
            dt = datetime.fromtimestamp(ts, tz=et)
            if dt.date() != today: continue
            t = dt.time()
            if t < time(9, 30):               pre_bars.append(cl)
            elif time(9,30) <= t < time(16,0):
                if hi: reg_highs.append(hi)
                if lo: reg_lows.append(lo)
                if vo: reg_vols.append(vo)
            elif time(16,0) <= t < time(20,0): post_bars.append(cl)
        if pre_bars  and pre_price  is None: pre_price  = pre_bars[-1]
        if post_bars and post_price is None: post_price = post_bars[-1]
        day_high = max(reg_highs) if reg_highs else None
        day_low  = min(reg_lows)  if reg_lows  else None
        volume   = sum(reg_vols)  if reg_vols  else None
        frac = len(reg_vols) / 390.0
        avg_vol = int(volume / frac) if (volume and frac > 0.05) else None
    except Exception:
        pass

    def _cp(p, base):
        if p and base: return p - base, (p - base) / base * 100
        return None, None

    pre_chg,  pre_pct  = _cp(pre_price,  prev)
    post_chg, post_pct = _cp(post_price, price or prev)
    reg_chg,  reg_pct  = _cp(price, prev)
    return dict(
        ticker=ticker, name=meta.get("longName") or meta.get("shortName") or ticker,
        price=price, prev=prev, reg_chg=reg_chg, reg_pct=reg_pct,
        pre_price=pre_price, pre_chg=pre_chg, pre_pct=pre_pct,
        post_price=post_price, post_chg=post_chg, post_pct=post_pct,
        high=day_high, low=day_low, volume=volume, avg_vol=avg_vol, cap=None, error=None,
    )


def _yf_download_fallback(ticker: str) -> dict:
    df = yf.download(ticker, period="5d", interval="1m", prepost=True, progress=False, auto_adjust=True)
    if df.empty: raise RuntimeError("download returned empty")
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    et = pytz.timezone("America/New_York")
    today = datetime.now(et).date()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None: df.index = df.index.tz_localize("UTC").tz_convert(et)
    else: df.index = df.index.tz_convert(et)
    today_df = df[df.index.date == today]
    pre_df   = today_df[today_df.index.time < time(9, 30)]
    reg_df   = today_df[(today_df.index.time >= time(9,30)) & (today_df.index.time < time(16,0))]
    post_df  = today_df[today_df.index.time >= time(16, 0)]
    prev_df  = df[df.index.date < today]
    def _last(d, col="Close"):
        return float(d[col].iloc[-1]) if not d.empty and col in d.columns else None
    prev_close = _last(prev_df); reg_price = _last(reg_df) or _last(today_df)
    pre_price = _last(pre_df);   post_price = _last(post_df)
    def _cp(p, base):
        if p and base: return p - base, (p - base) / base * 100
        return None, None
    pre_chg,pre_pct   = _cp(pre_price, prev_close)
    post_chg,post_pct = _cp(post_price, reg_price or prev_close)
    reg_chg,reg_pct   = _cp(reg_price, prev_close)
    return dict(ticker=ticker, name=ticker, price=reg_price or prev_close, prev=prev_close,
                reg_chg=reg_chg, reg_pct=reg_pct, pre_price=pre_price, pre_chg=pre_chg, pre_pct=pre_pct,
                post_price=post_price, post_chg=post_chg, post_pct=post_pct,
                high=None, low=None, volume=None, avg_vol=None, cap=None, error=None)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    try: return _yahoo_chart_api(ticker)
    except Exception: pass
    if not (ticker.endswith("=F") or ticker.startswith("^")):
        try:
            from curl_cffi import requests as curl_req
            sess = curl_req.Session(impersonate="chrome110")
            t = yf.Ticker(ticker, session=sess); info = t.info
            if info.get("regularMarketPrice") or info.get("previousClose"):
                price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                prev  = info.get("previousClose") or price
                pre_price  = info.get("preMarketPrice")
                pre_chg    = info.get("preMarketChange")
                pre_pct    = info.get("preMarketChangePercent")
                post_price = info.get("postMarketPrice")
                post_chg   = info.get("postMarketChange")
                post_pct   = info.get("postMarketChangePercent")
                if pre_pct  and abs(pre_pct)  < 1: pre_pct  *= 100
                if post_pct and abs(post_pct) < 1: post_pct *= 100
                reg_chg = (price - prev) if (price and prev) else None
                reg_pct = (reg_chg / prev * 100) if (reg_chg and prev) else None
                return dict(ticker=ticker, name=info.get("shortName") or ticker,
                            price=price, prev=prev, reg_chg=reg_chg, reg_pct=reg_pct,
                            pre_price=pre_price, pre_chg=pre_chg, pre_pct=pre_pct,
                            post_price=post_price, post_chg=post_chg, post_pct=post_pct,
                            high=info.get("dayHigh"), low=info.get("dayLow"),
                            volume=info.get("volume"), avg_vol=info.get("averageVolume"),
                            cap=info.get("marketCap"), error=None)
        except Exception: pass
    try: return _yf_download_fallback(ticker)
    except Exception as e: return dict(ticker=ticker, error=str(e))


def render_quote_card(data, is_pre, is_post):
    if data.get("error"):
        st.markdown(f'<div class="quote-card"><div class="quote-ticker">{data["ticker"]}</div>'
                    '<div class="quote-name" style="color:var(--down)">載入失敗</div></div>',
                    unsafe_allow_html=True)
        return
    pm_price=data.get("pre_price"); pm_chg=data.get("pre_chg"); pm_pct=data.get("pre_pct")
    ah_price=data.get("post_price"); ah_chg=data.get("post_chg"); ah_pct=data.get("post_pct")
    reg_price=data.get("price"); reg_chg=data.get("reg_chg"); reg_pct=data.get("reg_pct")
    isFut = data["ticker"].endswith("=F")
    t_now = datetime.now(pytz.timezone("America/New_York")).time()
    is_regular = time(9,30) <= t_now < time(16,0)
    if is_pre and pm_price:   dp,dc,dpct,lbl = pm_price,pm_chg,pm_pct,"盤前"
    elif is_post and ah_price: dp,dc,dpct,lbl = ah_price,ah_chg,ah_pct,"盤後"
    elif is_regular or isFut: dp,dc,dpct,lbl = reg_price,reg_chg,reg_pct,"盤中" if is_regular else "即時"
    else:                      dp,dc,dpct,lbl = reg_price,reg_chg,reg_pct,"收盤"
    sign    = "+" if (dc or 0) >= 0 else ""
    chg_str = f"{sign}{fmt_num(dc)} ({fmt_pct(dpct)})" if dc is not None else "—"
    vol,avg = data.get("volume"),data.get("avg_vol")
    vol_ratio = f"{vol/avg:.1f}x" if (vol and avg) else "—"
    vol_cls = "down" if (vol and avg and vol/avg>1.5) else ("up" if (vol and avg and vol/avg>1.0) else "flat")

    # FIX #3: dynamic color for pre/post price in meta row
    pm_cls = cc(pm_pct) if pm_pct is not None else "flat"
    ah_cls = cc(ah_pct) if ah_pct is not None else "flat"

    meta_parts = [f'<span>收盤 <b>{fmt_num(reg_price)}</b></span>']
    if pm_price: meta_parts.append(f'<span>盤前 <b class="{pm_cls}">{fmt_num(pm_price)}</b></span>')
    if ah_price: meta_parts.append(f'<span>盤後 <b class="{ah_cls}">{fmt_num(ah_price)}</b></span>')
    meta_parts += [
        f'<span>高 <b>{fmt_num(data.get("high"))}</b></span>',
        f'<span>低 <b>{fmt_num(data.get("low"))}</b></span>',
        f'<span>量 <b class="{vol_cls}">{fmt_vol(vol)}</b></span>',
        f'<span>量比 <b class="{vol_cls}">{vol_ratio}</b></span>',
        f'<span>市值 <b>{fmt_cap(data.get("cap"))}</b></span>',
    ]
    # Check price alerts for this ticker
    alert_html = _check_price_alert_inline(data["ticker"], dp)
    st.markdown(
        f'<div class="quote-card">'
        f'<div class="quote-top"><div>'
        f'<div class="quote-ticker">{data["ticker"]} '
        f'<span class="pill {pc(dpct)}" style="font-size:.58rem;margin-left:.35rem">{lbl}</span></div>'
        f'<div class="quote-name">{data["name"]}</div></div>'
        f'<div><div class="quote-price {cc(dpct)}">{fmt_num(dp)}</div>'
        f'<div class="quote-change {cc(dpct)}">{chg_str}</div></div></div>'
        f'<div class="quote-meta">{" ".join(meta_parts)}</div>'
        f'{alert_html}</div>',
        unsafe_allow_html=True)


# ── Groq AI call ──────────────────────────────────────────────────────────────
def groq_chat(prompt: str, groq_key: str, model: str = "llama-3.3-70b-versatile",
              max_tokens: int = 1200, temperature: float = 0.3) -> str:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": temperature,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── FIX #1: st_autorefresh — non-blocking ─────────────────────────────────────
def setup_autorefresh():
    """Use streamlit-autorefresh if available, else show a warning."""
    if not st.session_state.auto_refresh:
        return
    interval_ms = st.session_state.refresh_interval * 1000
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=interval_ms, key="auto_refresh_ticker")
    except ImportError:
        # Fallback: JS-based meta refresh (non-blocking, no sleep)
        st.markdown(
            f'<meta http-equiv="refresh" content="{st.session_state.refresh_interval}">',
            unsafe_allow_html=True)


# ── FIX #5: TSLA price alert system ──────────────────────────────────────────
def _check_price_alert_inline(ticker: str, current_price) -> str:
    """Return HTML alert strip if a price alert is triggered for this ticker."""
    if current_price is None: return ""
    fired = []
    for a in st.session_state.price_alerts:
        if a["ticker"].upper() != ticker.upper(): continue
        target = a["price"]
        direction = a["direction"]
        if direction == "突破上方" and current_price >= target:
            fired.append(f'🔔 {ticker} 突破 ${target:.2f} ↑ 現價 ${current_price:.2f}')
        elif direction == "跌破下方" and current_price <= target:
            fired.append(f'🔔 {ticker} 跌破 ${target:.2f} ↓ 現價 ${current_price:.2f}')
    if not fired: return ""
    msgs = " &nbsp;|&nbsp; ".join(fired)
    return f'<div class="price-alert-banner">🚨 {msgs}</div>'

def render_alert_manager():
    """Sidebar alert management UI."""
    st.markdown("### 🔔 價位警報")
    c1,c2,c3 = st.columns([2,2,2])
    with c1:
        ticker_in = st.text_input("代號", value=st.session_state.alert_ticker,
                                   key="alert_ticker_input", placeholder="TSLA").upper()
        st.session_state.alert_ticker = ticker_in
    with c2:
        price_in = st.text_input("價位 $", value=st.session_state.alert_price,
                                  key="alert_price_input", placeholder="400.00")
        st.session_state.alert_price = price_in
    with c3:
        dir_in = st.selectbox("方向", ["突破上方","跌破下方"], key="alert_dir_select")
        st.session_state.alert_dir = dir_in

    if st.button("➕ 加入警報", key="add_alert_btn"):
        try:
            p = float(price_in.replace("$","").replace(",",""))
            new_alert = {"ticker": ticker_in, "direction": dir_in, "price": p}
            # Avoid duplicate
            if new_alert not in st.session_state.price_alerts:
                st.session_state.price_alerts.append(new_alert)
                st.success(f"✅ 已設定：{ticker_in} {dir_in} ${p:.2f}")
        except ValueError:
            st.error("請輸入有效價位數字")

    if st.session_state.price_alerts:
        for i, a in enumerate(st.session_state.price_alerts):
            col_a, col_b = st.columns([4,1])
            with col_a:
                st.markdown(
                    f'<div style="font-family:var(--mono,monospace);font-size:.7rem;'
                    f'color:var(--text,#2C2A25);padding:.2rem 0">'
                    f'{a["ticker"]} {a["direction"]} <b>${a["price"]:.2f}</b></div>',
                    unsafe_allow_html=True)
            with col_b:
                if st.button("✕", key=f"del_alert_{i}"):
                    st.session_state.price_alerts.pop(i)
                    st.rerun()


# ── FIX #8: VIX yesterday fetch ───────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_vix_prev() -> float | None:
    """Fetch yesterday's VIX close for delta display."""
    try:
        df = yf.download("^VIX", period="5d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if len(df) >= 2:
            return float(df["Close"].iloc[-2])
    except Exception:
        pass
    return None


# ── FIX #9: Fear & Greed Index ────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fear_greed() -> dict:
    """
    CNN Fear & Greed Index via alternative.me (free, no key needed).
    Returns {"value": int, "classification": str, "prev_close": int}
    """
    try:
        r = requests.get("https://fear-and-greed-index.p.rapidapi.com/v1/fgi",
                         timeout=6)
    except Exception:
        r = None
    # Try alternative.me (more reliable, truly free)
    try:
        r2 = requests.get("https://api.alternative.me/fng/?limit=2", timeout=6)
        data = r2.json()["data"]
        current = int(data[0]["value"])
        prev    = int(data[1]["value"]) if len(data) > 1 else current
        label   = data[0]["value_classification"]
        return {"value": current, "classification": label, "prev": prev, "source": "alternative.me"}
    except Exception:
        pass
    return {"value": None, "classification": "N/A", "prev": None, "source": "N/A"}

def render_fear_greed():
    fg = fetch_fear_greed()
    val = fg.get("value")
    prev = fg.get("prev")
    label_map = {
        "Extreme Fear":"極度恐懼","Fear":"恐懼","Neutral":"中性",
        "Greed":"貪婪","Extreme Greed":"極度貪婪"
    }
    label_zh = label_map.get(fg.get("classification",""), fg.get("classification","—"))

    if val is None:
        st.markdown('<div class="fg-card"><div class="fg-label">恐懼貪婪指數</div>'
                    '<div class="fg-value flat">—</div></div>', unsafe_allow_html=True)
        return

    # Color based on value
    if   val <= 25: fg_col = "var(--down)"
    elif val <= 45: fg_col = "#E67E22"
    elif val <= 55: fg_col = "#F1C40F"
    elif val <= 75: fg_col = "#27AE60"
    else:           fg_col = "var(--up)"

    delta_str = ""
    if prev is not None:
        d = val - prev
        delta_str = f'<span style="font-size:.65rem;color:{"var(--up)" if d>=0 else "var(--down)"}">'
        delta_str += f'{"+" if d>=0 else ""}{d} vs昨日</span>'

    needle_pct = val  # 0-100 maps directly to 0%-100%
    st.markdown(
        f'<div class="fg-card">'
        f'<div class="fg-label">😱 CNN 恐懼貪婪指數</div>'
        f'<div style="display:flex;align-items:baseline;gap:.5rem">'
        f'<div class="fg-value" style="color:{fg_col}">{val}</div>'
        f'<div class="fg-sentiment">{label_zh} &nbsp;{delta_str}</div></div>'
        f'<div class="fg-meter"><div class="fg-needle" style="left:{needle_pct}%"></div></div>'
        f'<div style="display:flex;justify-content:space-between;font-family:var(--mono,monospace);'
        f'font-size:.55rem;color:var(--muted,#8A8278);margin-top:.18rem">'
        f'<span>極度恐懼</span><span>恐懼</span><span>中性</span><span>貪婪</span><span>極度貪婪</span></div>'
        f'<div style="font-family:var(--mono,monospace);font-size:.55rem;color:var(--muted,#8A8278);'
        f'margin-top:.28rem">來源：alternative.me</div>'
        f'</div>',
        unsafe_allow_html=True)


# ── Weekly events — Groq auto-generate ───────────────────────────────────────
_FALLBACK_EVENTS = [
    {"date":"2026-06-09","weekday":"周一 MON","events":[
        {"text":"Kevin Warsh 就任美聯儲主席","color":"red","impact":"high","note":"Warsh 鷹派傾向，加息預期上移","et_time":""},
        {"text":"美中貿易談判磋商","color":"amber","impact":"high","note":"90天關稅暫緩窗口期","et_time":""},
    ]},
    {"date":"2026-06-10","weekday":"周二 TUE","events":[
        {"text":"5月 CPI 數據","color":"red","impact":"high","note":"YoY 3.8%；偏熱→沽科技","et_time":"08:30"},
    ]},
    {"date":"2026-06-11","weekday":"周三 WED","events":[
        {"text":"5月 PPI 數據","color":"amber","impact":"high","note":"配合CPI判斷通脹方向","et_time":"08:30"},
        {"text":"伊朗/霍爾木茲局勢","color":"red","impact":"high","note":"和平協議談判中，影響油價","et_time":""},
    ]},
    {"date":"2026-06-12","weekday":"周四 THU","events":[
        {"text":"SpaceX (SPCX) Nasdaq IPO","color":"green","impact":"high","note":"$135/股，$1.77T估值","et_time":"09:30"},
        {"text":"密歇根大學消費者信心","color":"amber","impact":"med","note":"通脹預期數據影響Fed路徑","et_time":"10:00"},
        {"text":"Baker Hughes 鑽井數","color":"blue","impact":"low","note":"油市供應端參考","et_time":"13:00"},
    ]},
    {"date":"2026-06-13","weekday":"周五 FRI","events":[
        {"text":"FOMC 靜默期（下週一三）","color":"purple","impact":"high","note":"Warsh 首次FOMC 6/16-17","et_time":""},
        {"text":"美伊和平協議後續","color":"red","impact":"high","note":"若簽署→週一油價急跌","et_time":""},
    ]},
]

_WEEKDAY_MAP = ["周一 MON","周二 TUE","周三 WED","周四 THU","周五 FRI","周六 SAT","周日 SUN"]

def fetch_weekly_events(serper_key: str, groq_key: str) -> list:
    monday = week_monday_str()
    if st.session_state.weekly_events and st.session_state.weekly_events_fetched == monday:
        return st.session_state.weekly_events
    if not serper_key or not groq_key:
        return _FALLBACK_EVENTS
    queries = [
        "US economic calendar CPI PPI retail sales this week",
        "Federal Reserve Fed chair Warsh Powell FOMC this week",
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
        "text": "事件名稱（繁體中文，不含時間）",
        "et_time": "HH:MM 或空字串",
        "color": "red|amber|blue|purple|green",
        "impact": "high|med|low",
        "note": "一句話市場影響分析（繁體中文）"
      }}
    ]
  }}
]

規則：
- 每天 1-4 個事件，只列重要事件，按 ET 時間升序排列
- et_time: 有具體時間填 HH:MM（如 08:30），無具體時間填空字串
- color: red=重大風險/央行/地緣, amber=中等/貿易/數據, blue=例行數據, purple=聯儲官員, green=利好
- impact: high=市場必看, med=中等影響, low=參考
- note 要具體，點出對科技股/TSLA 的影響方向"""
    try:
        raw = groq_chat(prompt, groq_key, max_tokens=1600, temperature=0.2)
        raw = raw.replace("```json","").replace("```","").strip()
        events = json.loads(raw)
        for day in events:
            assert "date" in day and "events" in day
            # FIX #4: sort events by et_time within each day
            day["events"].sort(key=lambda e: e.get("et_time","") or "99:99")
        st.session_state.weekly_events = events
        st.session_state.weekly_events_fetched = monday
        return events
    except Exception:
        return _FALLBACK_EVENTS


def render_weekly_calendar(events: list, source_label: str):
    et = pytz.timezone("America/New_York")
    today_str = datetime.now(et).strftime("%Y-%m-%d")
    for day in events:
        if day["date"] == today_str:
            high = [e for e in day.get("events",[]) if e.get("impact") == "high"]
            if high:
                alerts = " &nbsp;|&nbsp; ".join([f"⚠️ <b>{_html.escape(e['text'])}</b>" for e in high])
                st.markdown(f'<div class="cal-alert-strip">🔔 今日高影響事件：{alerts}</div>',
                            unsafe_allow_html=True)
            break
    st.markdown('<div class="section-label">▸ 📅 本週重磅事件日曆 · 宏觀催化劑追蹤</div>', unsafe_allow_html=True)
    imp_map  = {"high":"imp-high","med":"imp-med","low":"imp-low"}
    imp_text = {"high":"高影響","med":"中影響","low":"低影響"}
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
            text = _html.escape(ev.get("text",""))
            note = _html.escape(ev.get("note",""))
            # FIX #4: show et_time inline
            et_t = ev.get("et_time","")
            time_tag = f'<span style="font-family:var(--mono,monospace);font-size:.55rem;color:var(--muted,#8A8278);margin-right:.2rem">{et_t}</span>' if et_t else ""
            evs_html += (
                f'<div class="cal-event" title="{note}">'
                f'<div class="cal-dot {dot}"></div>'
                f'<div><span class="cal-impact {ic}">{il}</span> {time_tag}{text}</div>'
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
                    et_t = ev.get("et_time","")
                    time_str = f" ({et_t} ET)" if et_t else ""
                    st.markdown(f"**{prefix}{day['weekday']} — {ev['text']}{time_str}**\n> {ev.get('note','')}\n")


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
        d = None
        try: d = _yahoo_chart_api(ticker)
        except Exception: pass
        if d is None or d.get("error") or not d.get("price"):
            try:
                df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    price = float(df["Close"].iloc[-1]); prev = float(df["Close"].iloc[-2]) if len(df) >= 2 else price
                    chg = price - prev; pct = chg/prev*100 if prev else None
                    d = dict(price=price, prev=prev, reg_chg=chg, reg_pct=pct,
                             high=float(df["High"].iloc[-1]) if "High" in df.columns else None,
                             low=float(df["Low"].iloc[-1])  if "Low"  in df.columns else None,
                             error=None)
            except Exception: pass
        if d is None or d.get("error") or not d.get("price"):
            try:
                info = yf.Ticker(ticker).info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                prev  = info.get("previousClose") or info.get("regularMarketPreviousClose")
                if price:
                    chg = (price-prev) if (price and prev) else None
                    pct = (chg/prev*100) if (chg and prev) else None
                    d = dict(price=price, prev=prev, reg_chg=chg, reg_pct=pct,
                             high=info.get("dayHigh"), low=info.get("dayLow"), error=None)
            except Exception as e: d = dict(error=str(e))
        if d and not d.get("error") and d.get("price"):
            price = d["price"]; prev = d.get("prev")
            chg = d.get("reg_chg") or ((price-prev) if (price and prev) else None)
            pct = d.get("reg_pct") or ((chg/prev*100) if (chg and prev) else None)
            results[ticker] = dict(label=meta["label"], unit=meta["unit"],
                                   price=price, chg=chg, pct=pct,
                                   high=d.get("high"), low=d.get("low"))
        else:
            results[ticker] = dict(label=meta["label"], unit=meta["unit"],
                                   error=d.get("error","fetch failed") if d else "fetch failed")
    return results

def _oil_direction_label(pct) -> str:
    if pct is None: return "變動"
    if pct >  2:    return "急升"
    if pct >  0.5:  return "上漲"
    if pct < -2:    return "急跌"
    if pct < -0.5:  return "下跌"
    return "平穩"

def render_oil_panel():
    st.markdown('<div class="section-label">▸ 🛢️ 能源價格監控</div>', unsafe_allow_html=True)
    oil  = fetch_oil_data()
    cols = st.columns(3)
    for i, (ticker, d) in enumerate(oil.items()):
        with cols[i]:
            if d.get("error"):
                st.markdown(f'<div class="oil-card"><div class="oil-label">{d["label"]}</div>'
                            f'<div class="oil-price flat">—</div>'
                            f'<div style="font-size:.6rem;color:var(--muted,#8A8278)">{d["error"][:40]}</div>'
                            f'</div>', unsafe_allow_html=True)
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
            st.markdown(f'<div class="oil-card">'
                        f'<div class="oil-label">{d["label"]} {alert}</div>'
                        f'<div class="oil-price {col}">${fmt_num(d.get("price"))}</div>'
                        f'<div class="oil-chg {col}">{sign}{fmt_num(chg)} ({fmt_pct(pct)})</div>'
                        f'<div class="oil-meta">高 {fmt_num(d.get("high"))} · 低 {fmt_num(d.get("low"))} · {d["unit"]}</div>'
                        f'</div>', unsafe_allow_html=True)
    wti = oil.get("CL=F",{})
    p, pct = wti.get("price"), wti.get("pct")
    if p and pct is not None:
        if   pct >  2:   msg,bg,bc,tc = f"⚠️ WTI 急升 <b>{fmt_pct(pct)}</b>，科技股承壓，注意通脹預期上移","#FDECEA","#C0392B","#7B1A12"
        elif pct >  0.5: msg,bg,bc,tc = f"🔶 WTI 上漲 <b>{fmt_pct(pct)}</b>，留意 TSLA/科技股壓力","#FFF8E8","#D4A017","#6B5000"
        elif pct < -2:   msg,bg,bc,tc = f"✅ WTI 急跌 <b>{fmt_pct(pct)}</b>，通脹壓力減輕，利好科技/成長股","#EAF4EE","#3A7D5C","#1E4D35"
        elif pct < -0.5: msg,bg,bc,tc = f"🔽 WTI 下跌 <b>{fmt_pct(pct)}</b>，能源成本回落，科技股溫和利好","#EAF4EE","#3A7D5C","#1E4D35"
        else:            msg,bg,bc,tc = f"WTI 平穩 <b>{fmt_pct(pct)}</b>，能源因素對市場影響中性","#F0EDE8","#D8D0C0","#8A8278"
        st.markdown(f'<div style="background:{bg};border-left:3px solid {bc};border-radius:0 4px 4px 0;'
                    f'padding:.5rem .85rem;font-size:.76rem;color:{tc};margin-top:.45rem">{msg}</div>',
                    unsafe_allow_html=True)


# ── News intel panel ──────────────────────────────────────────────────────────
@st.cache_data(ttl=180, show_spinner=False)
def fetch_news(query: str, serper_key: str, cache_buster: int = 0) -> list:
    if not serper_key: return []
    today = _today_et_str()
    try:
        r = requests.post("https://google.serper.dev/news",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": f"{query} {today}", "num": 8, "hl": "en", "gl": "us", "tbs": "qdr:d"},
            timeout=8)
        articles = r.json().get("news", [])
        fresh, stale = [], []
        for a in articles:
            ds = a.get("date","")
            is_fresh = ("hour" in ds or "minute" in ds or "just now" in ds.lower()
                        or today in ds or ds == "")
            a["_fresh"] = is_fresh
            (fresh if is_fresh else stale).append(a)
        return (fresh + stale)[:6]
    except Exception:
        return []

@st.cache_data(ttl=180, show_spinner=False)
def groq_news_summary(articles: list, topic: str, groq_key: str, cache_buster: int = 0) -> dict:
    if not articles or not groq_key:
        return {"summary":"","signal":"neutral","signal_reason":"","bullets":[],"tsla_impact":"","stale_warning":False}
    today = _today_et_str()
    tagged = []
    stale_count = 0
    for a in articles[:6]:
        fresh_tag = "🟢 今日" if a.get("_fresh", True) else "🔴 舊聞"
        if not a.get("_fresh", True): stale_count += 1
        tagged.append(f"[{fresh_tag}] 標題：{a.get('title','')}\n來源：{a.get('source','')} | 時間：{a.get('date','未知')}\n內容：{a.get('snippet','')}")
    block = "\n\n".join(tagged)
    has_stale = stale_count > len(articles[:6]) // 2
    prompt = f"""你是美股即時交易員分析師。今日日期：{today}（美東時間）
分析以下「{topic}」新聞，**只根據標記為🟢今日的新聞**生成摘要。
若所有新聞都是🔴舊聞，請在 summary 開頭說明「⚠️ 未找到今日最新消息，以下為近期背景資訊」。
新聞：\n{block}
輸出純 JSON（無其他文字、無 markdown）：
{{"signal":"bullish|bearish|neutral","signal_reason":"15字內","summary":"2-3句","bullets":[{{"text":"重點1","level":"red|amber|green"}},{{"text":"重點2","level":"red|amber|green"}}],"tsla_impact":"TSLA今日一句影響","stale_warning":{str(has_stale).lower()}}}"""
    try:
        raw = groq_chat(prompt, groq_key, max_tokens=900, temperature=0.2)
        raw = raw.replace("```json","").replace("```","").strip()
        result = json.loads(raw)
        result["stale_warning"] = result.get("stale_warning", has_stale)
        return result
    except Exception:
        return {"summary":"AI 摘要失敗","signal":"neutral","signal_reason":"","bullets":[],"tsla_impact":"","stale_warning":False}

def render_intel_panel(title: str, query: str, serper_key: str, groq_key: str, icon: str = "📡"):
    st.markdown(f'<div class="section-label">▸ {icon} {title}</div>', unsafe_allow_html=True)
    if not serper_key:
        st.markdown('<div class="intel-panel"><div style="font-size:.75rem;color:var(--muted);text-align:center;padding:1rem">請輸入 Serper API Key</div></div>',
                    unsafe_allow_html=True)
        return

    # FIX #7: manual refresh button per panel
    refresh_key = f"news_refresh_{title}"
    buster = st.session_state.news_refresh.get(title, 0)
    col_t, col_btn = st.columns([8,1])
    with col_btn:
        if st.button("🔄", key=f"refresh_btn_{title}", help="手動刷新此面板"):
            new_buster = int(time_module.time())
            st.session_state.news_refresh[title] = new_buster
            buster = new_buster

    with st.spinner(f"抓取 {title}..."):
        articles = fetch_news(query, serper_key, cache_buster=buster)
    if not articles:
        st.markdown('<div class="intel-panel"><div style="color:var(--muted);font-size:.78rem;padding:.4rem">暫無最新消息</div></div>',
                    unsafe_allow_html=True)
        return
    ai = {}
    if groq_key:
        with st.spinner("Groq 分析中..."):
            ai = groq_news_summary(articles, title, groq_key, cache_buster=buster)

    signal    = ai.get("signal","neutral")
    sig_cls   = {"bullish":"signal-bullish","bearish":"signal-bearish"}.get(signal,"signal-neutral")
    sig_text  = {"bullish":"▲ 利多","bearish":"▼ 利空","neutral":"◆ 中性"}.get(signal,"◆ 中性")
    sig_reason= ai.get("signal_reason","")
    summary   = ai.get("summary","")
    bullets   = ai.get("bullets",[])
    tsla_imp  = ai.get("tsla_impact","")
    stale_warn= ai.get("stale_warning",False)
    now_str   = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M ET")
    today     = _today_et_str()
    fresh_count = sum(1 for a in articles if a.get("_fresh",True))
    total_count = len(articles)

    html = '<div class="intel-panel">'
    html += f'<div class="intel-header">'
    html += f'<div class="intel-title">{_html.escape(title)}<span class="signal-badge {sig_cls}">{sig_text} {_html.escape(sig_reason)}</span></div>'
    if   fresh_count == total_count: freshness = '<span style="color:var(--up);font-size:.6rem">● 全部今日</span>'
    elif fresh_count == 0:           freshness = '<span style="color:var(--down);font-size:.6rem">⚠ 無今日消息</span>'
    else:                            freshness = f'<span style="color:#D4A017;font-size:.6rem">◑ {fresh_count}/{total_count} 今日</span>'
    html += f'<div class="intel-time">{freshness} &nbsp;Groq · {now_str}</div></div>'
    if stale_warn or fresh_count == 0:
        html += (f'<div style="background:#FFF3CD;border-left:3px solid #D4A017;border-radius:0 4px 4px 0;'
                 f'padding:.4rem .8rem;font-size:.72rem;color:#856404;margin-bottom:.6rem">'
                 f'⚠️ 未找到 {today} 的最新消息，以下為近期背景資訊，請自行核實</div>')
    if summary:
        html += f'<div class="intel-summary">{_html.escape(summary)}</div>'
    if bullets:
        for b in bullets:
            dc = {"red":"red","amber":"amber"}.get(b.get("level",""),"")
            html += (f'<div class="news-item"><div class="news-dot {dc}"></div>'
                     f'<div><div class="news-text">{_html.escape(b.get("text",""))}</div></div></div>')
    html += '<div style="margin-top:.6rem;padding-top:.5rem;border-top:1px solid var(--border)">'
    for a in articles[:5]:
        is_fresh = a.get("_fresh",True)
        dot_col  = "var(--up)" if is_fresh else "var(--down)"
        tag      = "今日" if is_fresh else "舊聞"
        html += (f'<div class="news-item"><div class="news-dot" style="background:{dot_col}"></div>'
                 f'<div><div class="news-text">{_html.escape(a.get("title",""))}</div>'
                 f'<div class="news-source" style="color:{dot_col}">[{tag}] {_html.escape(a.get("source",""))} · {_html.escape(a.get("date",""))}</div>'
                 f'</div></div>')
    html += '</div>'
    if tsla_imp:
        html += (f'<div style="margin-top:.65rem;padding-top:.55rem;border-top:1px solid var(--border);'
                 f'font-family:var(--mono,monospace);font-size:.68rem;color:var(--muted)">'
                 f'🚗 TSLA 影響：<span style="color:var(--text)">{_html.escape(tsla_imp)}</span></div>')
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ── AI Prompt Generator ───────────────────────────────────────────────────────
def generate_trading_prompt(events, oil_data, tsla_data, vix_data, qqq_data, is_pre) -> str:
    et        = pytz.timezone("America/New_York")
    now_et    = datetime.now(et)
    today_str = now_et.strftime("%Y-%m-%d")
    session   = "盤前" if is_pre else "盤中/盤後"
    today_events = next((d.get("events",[]) for d in events if d["date"] == today_str), [])
    events_lines = "\n".join(
        [f"  - [{e.get('impact','').upper()}] {e.get('et_time','')+'ET ' if e.get('et_time') else ''}{e['text']} — {e.get('note','')}"
         for e in today_events]
    ) or "  （今日無已知重大事件）"
    high_events = [e for e in today_events if e.get("impact") == "high"]
    high_lines  = "\n".join([f"  ⚠️ {e.get('et_time','')+'ET ' if e.get('et_time') else ''}{e['text']} — {e.get('note','')}" for e in high_events]) or "  （今日無已確認高影響事件）"

    _et_t = datetime.now(pytz.timezone("America/New_York")).time()
    _is_pre_t  = time(4,0)  <= _et_t < time(9,30)
    _is_reg_t  = time(9,30) <= _et_t < time(16,0)
    _is_post_t = time(16,0) <= _et_t < time(20,0)
    def snap(d):
        if not d or d.get("error"): return "N/A"
        if _is_pre_t and d.get("pre_price") and d.get("pre_pct") is not None:
            p,pct,tag = d["pre_price"],d["pre_pct"],"盤前"
        elif _is_reg_t and d.get("price") and d.get("reg_pct") is not None:
            p,pct,tag = d["price"],d["reg_pct"],"盤中"
        elif _is_post_t and d.get("post_price") and d.get("post_pct") is not None:
            p,pct,tag = d["post_price"],d["post_pct"],"盤後"
        elif d.get("price") and d.get("reg_pct") is not None:
            p,pct,tag = d["price"],d["reg_pct"],"收盤"
        elif d.get("pre_price") and d.get("pre_pct") is not None:
            p,pct,tag = d["pre_price"],d["pre_pct"],"盤前"
        else: p,pct,tag = d.get("price") or d.get("prev"),None,"收盤"
        return f"{fmt_num(p)} {fmt_pct(pct) if pct is not None else '—'} [{tag}]"

    wti   = (oil_data or {}).get("CL=F",{})
    brent = (oil_data or {}).get("BZ=F",{})
    wti_pct   = wti.get("pct")
    wti_str   = f"${fmt_num(wti.get('price'))} ({fmt_pct(wti_pct)})" if wti.get("price") else "N/A"
    brent_str = f"${fmt_num(brent.get('price'))} ({fmt_pct(brent.get('pct'))})" if brent.get("price") else "N/A"
    wti_dir   = _oil_direction_label(wti_pct)
    vix_val   = fmt_num(vix_data.get("price")) if vix_data and not vix_data.get("error") else "N/A"
    fetch_time = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M:%S ET")

    return f"""# 美股即時分析請求
日期：{today_str}  時間：{fetch_time}  時段：{session}  數據抓取：{fetch_time}

## 今日全部宏觀事件
{events_lines}

## 今日高影響事件（重點）
{high_lines}

## 市場即時快照
| 指標 | 數值 |
|------|------|
| TSLA | {snap(tsla_data)} |
| QQQ  | {snap(qqq_data)} |
| VIX  | {vix_val} |
| WTI 原油 | {wti_str} |
| Brent 原油 | {brent_str} |

## 請幫我分析：
1. **今日最大風險/機會**是什麼？對 TSLA 和納指方向的影響？
2. **油價{wti_dir} {wti_str}** 對今日科技股有何具體影響？
3. **TSLA 今日交易策略**：建議入場區間、止損位、目標位（$數字）？
4. **VIX {vix_val}** 顯示市場情緒如何？適合做多/做空/觀望？
5. 今日最需要關注的**時間點**（數據發布/官員講話/峰會消息）？

請用繁體中文回答，要具體，每點包含數字區間。"""


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

    # FIX #1: non-blocking autorefresh (must be called early)
    setup_autorefresh()

    now_et, session = get_session_info()
    is_pre  = "盤前" in session or "隔夜" in session
    is_post = "盤後" in session

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ 設定")

        # FIX #11: dark mode toggle
        dark = st.toggle("🌙 深色模式", value=st.session_state.dark_mode)
        if dark != st.session_state.dark_mode:
            st.session_state.dark_mode = dark
            st.rerun()

        st.markdown("---")
        auto = st.toggle("⏱️ 自動刷新", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto
        if auto:
            iv = st.selectbox("刷新頻率（秒）",[30,60,120,300],index=1,format_func=lambda x:f"{x} 秒")
            st.session_state.refresh_interval = iv
            st.caption(f"下次刷新：每 {iv} 秒自動更新（非阻塞）")

        st.markdown("---")
        st.markdown("### 🔑 API 設定")
        sk = st.text_input("Serper API Key", value=st.session_state.serper_key,
                           type="password", placeholder="新聞抓取 — serper.dev 免費")
        st.session_state.serper_key = sk
        gk = st.text_input("Groq API Key", value=st.session_state.groq_key,
                           type="password", placeholder="AI 摘要 — groq.com 免費")
        st.session_state.groq_key = gk

        st.markdown("---")
        render_alert_manager()

        st.markdown("---")
        st.markdown("### 📋 自訂股票")
        custom = st.text_area("輸入代號（換行分隔）", value=st.session_state.custom_tickers,
                              height=90, placeholder="GOOGL\nMETA")
        st.session_state.custom_tickers = custom

        st.markdown("---")
        st.markdown("### 顯示選項")
        show_futures = st.checkbox("期貨代理",      value=True)
        show_vix     = st.checkbox("波動/恐慌",     value=True)
        show_lev     = st.checkbox("槓桿ETF",       value=False)
        show_oil     = st.checkbox("能源價格",       value=True)
        show_fg      = st.checkbox("恐懼貪婪指數",  value=True)
        show_trump   = st.checkbox("Trump 消息",    value=True)
        show_iran    = st.checkbox("伊朗/油價新聞", value=True)

        st.markdown("---")
        if st.button("🔄 立即刷新全部"):
            st.cache_data.clear()
            st.session_state.weekly_events = None
            st.rerun()
        if st.button("🗓️ 重新生成週曆"):
            st.session_state.weekly_events = None
            st.session_state.weekly_events_fetched = ""
            st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    # Build as string concat — triple-quote f-string with strftime % can break markdown parser
    _iv   = st.session_state.refresh_interval
    _rbadge = (
        '<span style="font-family:var(--mono,monospace);font-size:.6rem;'
        'color:var(--up,#3A7D5C);margin-left:.4rem">&#9203; ' + str(_iv) + 's</span>'
    ) if st.session_state.auto_refresh else ""
    _date = now_et.strftime("%Y-%m-%d")
    _time = now_et.strftime("%H:%M:%S")
    _hdr  = (
        '<div class="pm-header">'
        '<div>'
        '<div class="pm-title">&#128197; Pre-Market Monitor'
        '<span class="pm-session-badge">' + session + '</span>'
        + _rbadge +
        '</div>'
        '<div class="pm-subtitle">美股盤前即時監控 &middot; Fortune Trading Desk &middot; Groq AI &middot; v4</div>'
        '</div>'
        '<div class="pm-clock">' + _date + '<br><b>' + _time + ' ET</b></div>'
        '</div>'
    )
    st.markdown(_hdr, unsafe_allow_html=True)

    if is_pre:
        st.markdown('<div class="alert-box">⏰ <b>盤前交易時段</b> — 流動性較低，請注意風險管理</div>', unsafe_allow_html=True)
    elif is_post:
        st.markdown('<div class="alert-box">🌙 <b>盤後交易時段</b> — 財報/消息驅動，缺口風險較高</div>', unsafe_allow_html=True)

    # ── Weekly calendar ───────────────────────────────────────────────────────
    with st.spinner("📅 載入本週事件日曆..."):
        events = fetch_weekly_events(st.session_state.serper_key, st.session_state.groq_key)
    is_ai = bool(st.session_state.serper_key and st.session_state.groq_key and st.session_state.weekly_events)
    source_label = "✨ Groq AI 自動生成 · 每週一自動更新" if is_ai else "📋 內置數據 · 輸入 Serper + Groq Key 啟用自動更新"
    render_weekly_calendar(events, source_label)

    # ── AI Prompt ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">▸ 🤖 AI 交易分析助手</div>', unsafe_allow_html=True)
    col_btn1, col_btn2, col_toast = st.columns([1.5, 1.5, 5])
    with col_btn1:
        if st.button("✨ 一鍵生成 AI Prompt"):
            with st.spinner("整合最新市場數據中..."):
                fetch_quote.clear(); fetch_oil_data.clear()
                oil_data  = fetch_oil_data()
                tsla_data = fetch_quote("TSLA")
                vix_data  = fetch_quote("^VIX")
                qqq_data  = fetch_quote("QQQ")
            st.session_state.ai_prompt = generate_trading_prompt(events, oil_data, tsla_data, vix_data, qqq_data, is_pre)
            st.session_state.show_prompt = True
            st.session_state.prompt_copied = False
    with col_btn2:
        if st.session_state.show_prompt and st.button("❌ 隱藏 Prompt"):
            st.session_state.show_prompt = False

    if st.session_state.show_prompt and st.session_state.ai_prompt:
        st.markdown(
            '<div class="prompt-panel">'
            '<div class="prompt-title">📋 複製以下 Prompt，貼入 ChatGPT / Claude / Gemini</div>'
            '</div>',
            unsafe_allow_html=True)
        # st.code() provides the native copy icon (top-right of code block) — most reliable in Streamlit Cloud
        st.code(st.session_state.ai_prompt, language="markdown")

        # Secondary copy button using st.components.v1.html() — runs in its own iframe
        # so it has proper clipboard permissions, unlike st.markdown <script> which is stripped
        import streamlit.components.v1 as _stc
        # Escape chars that would break the JS template literal
        _pe = st.session_state.ai_prompt
        _pe = _pe.replace("\\", "\\\\")  # backslash first
        _pe = _pe.replace("`", "\\`")          # backtick
        _pe = _pe.replace("${", "\\${")        # template literal interpolation
        _prompt_escaped = _pe
        _copy_html = f"""
<style>
  #copy-btn {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: .73rem;
    background: #6B7C6E;
    color: #FAF7F2;
    border: none;
    border-radius: 4px;
    padding: .38rem 1.1rem;
    cursor: pointer;
    transition: background .2s;
  }}
  #copy-btn:hover {{ background: #5a6b5d; }}
  #copy-btn.success {{ background: #3A7D5C; }}
  #hint {{ font-family: monospace; font-size: .65rem; color: #8A8278; margin-left: .6rem; }}
</style>
<button id="copy-btn" onclick="doCopy()">📋 複製 Prompt</button>
<span id="hint">或點擊代碼框右上角複製圖示</span>
<script>
function doCopy() {{
  const text = `{_prompt_escaped}`;
  // Method 1: modern clipboard API (works when page has focus)
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(text)
      .then(onSuccess)
      .catch(() => fallback(text));
  }} else {{
    fallback(text);
  }}
}}
function fallback(text) {{
  // Method 2: execCommand — works inside iframes without clipboard permission
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try {{
    document.execCommand('copy');
    onSuccess();
  }} catch(e) {{
    document.getElementById('hint').innerText = '⚠️ 請手動選取代碼框文字複製';
  }}
  document.body.removeChild(ta);
}}
function onSuccess() {{
  const btn = document.getElementById('copy-btn');
  btn.innerText = '✅ 已複製！';
  btn.classList.add('success');
  setTimeout(() => {{
    btn.innerText = '📋 複製 Prompt';
    btn.classList.remove('success');
  }}, 3000);
}}
</script>"""
        _stc.html(_copy_html, height=48)

    # ── Stock sections ────────────────────────────────────────────────────────
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

    if show_oil:
        render_oil_panel()

    # ── FIX #9: Fear & Greed ─────────────────────────────────────────────────
    if show_fg:
        st.markdown('<div class="section-label">▸ 😱 市場情緒指標</div>', unsafe_allow_html=True)
        render_fear_greed()

    # ── News panels ───────────────────────────────────────────────────────────
    sk, gk = st.session_state.serper_key, st.session_state.groq_key
    _today = _today_et_str()
    if show_trump:
        render_intel_panel("Trump 最新表態監控", f"Trump Truth Social statement stock market {_today}", sk, gk, "🇺🇸")
    if show_iran:
        render_intel_panel("伊朗戰爭 · 油價消息", f"Iran war oil price Hormuz ceasefire {_today}", sk, gk, "🛢️")

    # ── Quick metrics bar ─────────────────────────────────────────────────────
    st.markdown('<div class="section-label">▸ 快速指標</div>', unsafe_allow_html=True)
    vd = fetch_quote("^VIX"); sd = fetch_quote("SPY")
    qd = fetch_quote("QQQ");  td = fetch_quote("TSLA")
    m1,m2,m3,m4 = st.columns(4)

    def mini(col, lbl, val, sub, col_cls=""):
        col.markdown(f'<div class="mini-card"><div class="mini-label">{lbl}</div>'
                     f'<div class="mini-value {col_cls}">{val}</div>'
                     f'<div class="mini-sub">{sub}</div></div>', unsafe_allow_html=True)

    def best_pct(d):
        if not d or d.get("error"): return None, None, "—"
        et_t = datetime.now(pytz.timezone("America/New_York")).time()
        _is_reg = time(9,30) <= et_t < time(16,0)
        if d.get("pre_pct") is not None and not _is_reg: return d["pre_pct"], d.get("pre_price") or d.get("price"), "盤前"
        if d.get("reg_pct") is not None: return d["reg_pct"], d.get("price"), "盤中" if _is_reg else "收盤"
        if d.get("pre_pct") is not None: return d["pre_pct"], d.get("pre_price") or d.get("price"), "盤前"
        if d.get("post_pct") is not None: return d["post_pct"], d.get("post_price"), "盤後"
        return None, d.get("price"), "—"

    # FIX #8: VIX with yesterday delta
    vp = vd.get("price")
    vp_prev = fetch_vix_prev()
    vc = "down" if (vp and vp>25) else ("up" if (vp and vp<18) else "flat")
    vl = "極度恐慌" if (vp and vp>30) else ("恐慌" if (vp and vp>20) else "平靜")
    vix_delta = ""
    if vp and vp_prev:
        d_val = vp - vp_prev
        vix_delta = f' ({"+" if d_val>=0 else ""}{d_val:.2f} vs昨)'
    mini(m1, "VIX 恐慌", fmt_num(vp), f"{vl}{vix_delta}", vc)

    sp, _, slbl = best_pct(sd)
    mini(m2, f"SPY {slbl}%", fmt_pct(sp), f"收盤 {fmt_num(sd.get('price'))}", cc(sp))
    qp, _, qlbl = best_pct(qd)
    mini(m3, f"QQQ {qlbl}%", fmt_pct(qp), f"收盤 {fmt_num(qd.get('price'))}", cc(qp))
    tp, _, tlbl = best_pct(td)
    mini(m4, f"TSLA {tlbl}%", fmt_pct(tp), f"收盤 {fmt_num(td.get('price'))}", cc(tp))

    # ── Footer ────────────────────────────────────────────────────────────────
    next_refresh = f" · ⏱ 自動刷新每 {st.session_state.refresh_interval}s" if st.session_state.auto_refresh else ""
    st.markdown(f"""
    <div style="font-family:var(--mono,monospace);font-size:.62rem;color:var(--muted,#AAA49C);
         text-align:center;padding:1.8rem 0 .8rem;border-top:1px solid var(--border,#D8D0C0);margin-top:1.8rem">
      最後更新 {datetime.now().strftime('%H:%M:%S')}{next_refresh}
      · 股價延遲 15-20 分鐘 · Groq AI 免費版 · 僅供參考，不構成投資建議
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
