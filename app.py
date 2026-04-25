"""
SmartStock — Premium Trading Terminal
Webull-style charts · Clean legends · No overlaps · Built-in AI thesis
Run: streamlit run app.py
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
from datetime import datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
import html
import time
import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None
import hashlib
import json, re, copy, math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── FMP-only compatibility helpers ────────────────────────────────
# All market/fundamental/news data is routed through Financial Modeling Prep.
# The compatibility _fmp_ticker() name is kept only so the rest of the app UI can stay unchanged.
def _fmp_ticker(symbol, proxy=None):
    return _FMPTicker(symbol)

def _fmp_history_safe(ticker_obj, retries=3, **kwargs):
    try:
        return ticker_obj.history(**kwargs)
    except Exception:
        return pd.DataFrame()

st.set_page_config(
    page_title="SmartStock",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
  --bg:#0d0f14; --bg2:#13161e; --bg3:#1a1e2a;
  --border:#252a38; --border2:#2e3448;
  --text:#e2e8f0; --muted:#64748b; --accent:#3b82f6;
  --green:#10b981; --red:#ef4444; --amber:#f59e0b;
  --purple:#8b5cf6; --teal:#06b6d4;
}
.stApp,[data-testid="stAppViewContainer"],
[data-testid="stMain"],[data-testid="block-container"]{background:var(--bg)!important;}
[data-testid="stSidebar"]{
  background:#10131a!important;
  border-right:1px solid #1d2430!important;
  min-width:340px!important;
  max-width:340px!important;
}
[data-testid="stSidebar"] > div:first-child{width:340px!important;}
[data-testid="stSidebar"] *{color:#cbd5e1!important;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:0.48rem!important;}
[data-testid="stSidebar"] [data-testid="block-container"]{
  padding-top:0.85rem!important;
  padding-left:1.15rem!important;
  padding-right:1.15rem!important;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown{font-size:12px!important;}
[data-testid="stSidebar"] .stCheckbox{margin-bottom:0.16rem!important;}
[data-testid="stSidebar"] [data-baseweb="select"]{margin-bottom:0.20rem!important;}
[data-testid="stSidebar"] [data-testid="stTextInput"]{margin-bottom:0.25rem!important;}
[data-testid="stSidebar"] [data-testid="stExpander"]{margin-top:0.20rem!important;margin-bottom:0.20rem!important;}
body,p,li,span,label,div{color:var(--text);}
h1,h2,h3,h4{color:#f1f5f9!important;font-weight:600;}
.block-container{padding:7.5rem 2rem 3rem!important;max-width:1600px!important;}

/* Main content top clearance: prevents Streamlit's fixed top toolbar/header from covering page headers */
[data-testid="stMain"] [data-testid="block-container"]{
  padding-top:8.25rem!important;
  padding-left:2rem!important;
  padding-right:2rem!important;
  padding-bottom:3rem!important;
  max-width:1600px!important;
}
header[data-testid="stHeader"]{
  background:rgba(13,15,20,0.96)!important;
  backdrop-filter:blur(8px)!important;
  border-bottom:1px solid #1d2430!important;
}
[data-testid="stToolbar"]{right:0.75rem!important;top:0.35rem!important;}

/* Extra fixed-header safety spacing for newer Streamlit versions */
section.main > div { padding-top: 7.5rem !important; }
[data-testid="stAppViewContainer"] > .main .block-container { padding-top: 8.25rem !important; }
div[data-testid="stVerticalBlock"]:first-child { scroll-margin-top: 8rem !important; }

[data-testid="metric-container"]{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;padding:14px 18px!important;transition:border-color 0.2s;}
[data-testid="metric-container"]:hover{border-color:var(--border2)!important;}
[data-testid="stMetricLabel"]>div{color:var(--muted)!important;font-size:11px!important;
  text-transform:uppercase;letter-spacing:0.07em;}
[data-testid="stMetricValue"]>div{color:#f1f5f9!important;font-size:1.15rem!important;
  font-weight:600;font-family:'SF Mono','Fira Code',monospace;}

.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;
  border:1px solid var(--border)!important;border-radius:10px!important;
  padding:4px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--muted)!important;
  border-radius:7px!important;padding:8px 20px!important;font-size:13px!important;
  font-weight:500!important;border:none!important;transition:all 0.15s!important;}
.stTabs [aria-selected="true"]{background:var(--bg3)!important;color:#f1f5f9!important;
  border:1px solid var(--border2)!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding:0!important;}
.stTabs [data-baseweb="tab-border"]{display:none!important;}

[data-testid="stTextInput"] input{background:var(--bg3)!important;
  border:1px solid var(--border2)!important;color:var(--text)!important;
  border-radius:8px!important;font-family:'SF Mono',monospace!important;
  font-size:15px!important;letter-spacing:0.06em!important;}
[data-testid="stTextInput"] input:focus{border-color:var(--accent)!important;
  box-shadow:0 0 0 2px rgba(59,130,246,0.15)!important;}

[data-testid="stButton"]>button{background:var(--bg3)!important;
  border:1px solid var(--border2)!important;color:var(--text)!important;
  border-radius:8px!important;font-size:13px!important;transition:all 0.15s!important;}
[data-testid="stButton"]>button:hover{border-color:var(--accent)!important;color:#f1f5f9!important;}
button[kind="primary"]{background:var(--accent)!important;border-color:var(--accent)!important;
  color:white!important;font-weight:600!important;}

[data-testid="stCheckbox"]>label{font-size:13px!important;color:var(--muted)!important;}
[data-testid="stDataFrame"]{border:1px solid var(--border)!important;
  border-radius:10px!important;overflow:hidden!important;}
[data-testid="stExpander"]{background:var(--bg2)!important;
  border:1px solid var(--border)!important;border-radius:10px!important;}
[data-testid="stAlert"]{background:var(--bg2)!important;
  border-color:var(--border2)!important;border-radius:10px!important;}

/* Legend pills row */
.legend-row{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 14px;padding-left:2px;}
.legend-pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;
  color:#94a3b8;padding:3px 10px;background:#13161e;
  border:1px solid #252a38;border-radius:20px;}
.legend-line{display:inline-block;width:18px;height:2px;border-radius:1px;vertical-align:middle;}
.legend-dash{display:inline-block;width:18px;height:0;border-top:2px dashed;vertical-align:middle;}

/* Chart window selector pills */
.window-row{display:flex;gap:6px;margin-bottom:12px;}
.window-pill{padding:4px 14px;border-radius:20px;font-size:11px;font-weight:500;
  cursor:pointer;border:1px solid #252a38;background:#13161e;color:#64748b;}
.window-pill.active{background:#3b82f6;border-color:#3b82f6;color:white;}

.ticker-badge{display:inline-flex;align-items:center;background:rgba(59,130,246,0.12);
  border:1px solid rgba(59,130,246,0.3);color:#60a5fa;border-radius:6px;
  padding:2px 10px;font-family:monospace;font-size:13px;font-weight:600;letter-spacing:0.06em;}
.exchange-badge{display:inline-flex;align-items:center;background:rgba(100,116,139,0.15);
  border:1px solid rgba(100,116,139,0.25);color:#94a3b8;border-radius:6px;
  padding:2px 10px;font-size:12px;}
.section-head{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;
  color:#475569;border-bottom:1px solid #1e2433;padding-bottom:8px;margin:1.5rem 0 1rem;}
.stat-label{font-size:10px;color:#475569;text-transform:uppercase;
  letter-spacing:0.08em;margin-bottom:4px;}
.signal-row{display:flex;align-items:center;gap:10px;background:#13161e;
  border:1px solid #1e2433;border-radius:8px;padding:10px 14px;
  margin-bottom:6px;font-size:13px;color:#94a3b8;}
.bull-card{background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);
  border-radius:12px;padding:1.2rem;}
.bear-card{background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);
  border-radius:12px;padding:1.2rem;}
.verdict-card{border-radius:14px;border-width:1px;border-style:solid;
  padding:1.4rem;text-align:center;}
.score-bar-wrap{margin-bottom:10px;}
.score-bar-label{display:flex;justify-content:space-between;font-size:12px;
  color:#64748b;margin-bottom:5px;}
.score-bar-track{height:5px;background:#1e2433;border-radius:3px;}
.sidebar-divider{height:1px;background:#1b2230;margin:0.95rem 0;}
.header-divider{height:1px;
  background:linear-gradient(90deg,#3b82f620,#8b5cf620,transparent);margin:1rem 0 1.5rem;}


/* Responsive header: prevents company name and price from overlapping */
.top-header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:start;padding-right:8px;margin-bottom:0.5rem;}
.top-header-name{font-size:clamp(20px,2.5vw,28px);font-weight:700;color:#f1f5f9;letter-spacing:-0.02em;margin-bottom:8px;line-height:1.15;white-space:normal;overflow-wrap:anywhere;word-break:normal;}
.top-header-price{text-align:right;min-width:190px;}
.top-header-price-main{font-size:clamp(28px,4vw,46px);font-weight:700;font-family:monospace;color:#f1f5f9;line-height:1;letter-spacing:-0.02em;white-space:nowrap;}
.news-card{background:#13161e;border:1px solid #252a38;border-radius:12px;padding:14px 16px;margin-bottom:10px;}
.news-meta{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;}
.news-title{font-size:15px;color:#f1f5f9;font-weight:700;line-height:1.35;margin-bottom:6px;}
.news-summary{font-size:13px;color:#94a3b8;line-height:1.55;margin-top:6px;}
.news-pill{display:inline-block;border-radius:999px;padding:2px 8px;font-size:10px;font-weight:700;margin-right:6px;border:1px solid #334155;color:#94a3b8;}
.news-positive{border-color:rgba(16,185,129,.35);color:#10b981;background:rgba(16,185,129,.08);}
.news-negative{border-color:rgba(239,68,68,.35);color:#ef4444;background:rgba(239,68,68,.08);}
.news-neutral{border-color:rgba(245,158,11,.35);color:#f59e0b;background:rgba(245,158,11,.08);}
@media(max-width:900px){.top-header{grid-template-columns:1fr}.top-header-price{text-align:left;min-width:0}}


.market-impact-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:10px;}
.market-impact-box{background:#0f131b;border:1px solid #243044;border-radius:10px;padding:10px 12px;min-height:76px;}
.market-impact-label{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.10em;font-weight:800;margin-bottom:6px;}
.market-impact-good{color:#10b981;font-size:12px;line-height:1.55;}
.market-impact-bad{color:#ef4444;font-size:12px;line-height:1.55;}
.market-impact-watch{color:#f59e0b;font-size:12px;line-height:1.55;}
.market-source-link{display:inline-flex;align-items:center;gap:4px;margin-top:9px;color:#60a5fa!important;text-decoration:none!important;font-size:12px;font-weight:700;}
.market-card-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:6px;}
.market-score-ring{min-width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle at center,#13161e 55%,transparent 56%),conic-gradient(#3b82f6 calc(var(--score)*1%),#252a38 0);font-family:monospace;font-size:13px;font-weight:800;color:#e2e8f0;}
@media(max-width:950px){.market-impact-grid{grid-template-columns:1fr;}.market-score-ring{width:46px;height:46px;min-width:46px;}}

.comment-box{background:#10131a;border:1px solid #243044;border-radius:12px;padding:13px 15px;margin-top:18px;color:#94a3b8;font-size:12px;line-height:1.65;}
.comment-box b{color:#e2e8f0;}
.comment-title{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#64748b;font-weight:800;margin-bottom:6px;}


/* Premium interaction polish */
*{scroll-behavior:smooth;}
[data-testid="stButton"]>button,[data-baseweb="select"]>div,[data-testid="stTextInput"] input,[data-testid="stCheckbox"] label,[data-testid="stExpander"],[data-testid="metric-container"],.news-card,.bull-card,.bear-card,.verdict-card{transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease,background .18s ease,opacity .18s ease!important;}
[data-testid="stButton"]>button{min-height:38px!important;box-shadow:0 8px 22px rgba(0,0,0,.18)!important;}
[data-testid="stButton"]>button:hover{transform:translateY(-1px)!important;box-shadow:0 12px 28px rgba(0,0,0,.28),0 0 0 1px rgba(59,130,246,.18)!important;}
[data-testid="stButton"]>button:active{transform:translateY(0)!important;filter:brightness(.96)!important;}
button[kind="primary"]{background:linear-gradient(135deg,#2563eb,#3b82f6,#06b6d4)!important;box-shadow:0 12px 32px rgba(59,130,246,.24)!important;}
[data-testid="metric-container"]:hover,.news-card:hover,.bull-card:hover,.bear-card:hover,.verdict-card:hover{transform:translateY(-1px);box-shadow:0 16px 34px rgba(0,0,0,.22);}
[data-testid="stDataFrame"],.js-plotly-plot{border-radius:14px!important;overflow:hidden!important;animation:fadeSlideIn .24s ease both;}
@keyframes fadeSlideIn{from{opacity:.0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.pro-chart-shell{background:linear-gradient(180deg,rgba(19,22,30,.92),rgba(13,15,20,.92));border:1px solid #252a38;border-radius:16px;padding:10px 10px 2px;margin-bottom:6px;box-shadow:0 18px 44px rgba(0,0,0,.18);}
.pro-subnav{background:#10131a;border:1px solid #252a38;border-radius:16px;padding:10px 12px;margin:-2px 0 18px;box-shadow:0 12px 30px rgba(0,0,0,.16);}
.pro-subnav-title{font-size:10px;text-transform:uppercase;letter-spacing:.14em;color:#64748b;margin-bottom:8px;font-weight:800;}
.pro-back-row{display:flex;justify-content:flex-end;margin:-4px 0 12px;}
.stRadio [role="radiogroup"]{gap:.38rem!important;flex-wrap:wrap!important;}
.stRadio [role="radiogroup"] label{background:#13161e!important;border:1px solid #252a38!important;border-radius:999px!important;padding:7px 13px!important;margin:0!important;min-height:34px!important;transition:all .18s ease!important;}
.stRadio [role="radiogroup"] label:hover{border-color:#3b82f6!important;transform:translateY(-1px);}
.stRadio [role="radiogroup"] label[data-checked="true"]{background:rgba(59,130,246,.18)!important;border-color:#3b82f6!important;box-shadow:0 0 0 1px rgba(59,130,246,.18)!important;}
.stRadio [role="radiogroup"] label p{font-size:12px!important;font-weight:700!important;color:#cbd5e1!important;}
.stSpinner > div{border-color:#3b82f6 transparent transparent transparent!important;}


/* Investor View */
.investor-card{background:linear-gradient(135deg,rgba(59,130,246,.10),rgba(139,92,246,.07));border:1px solid #263248;border-radius:16px;padding:18px 20px;margin-bottom:14px;box-shadow:0 12px 30px rgba(0,0,0,.18);}
.investor-title{font-size:22px;font-weight:800;color:#f8fafc;letter-spacing:-.02em;margin-bottom:4px;}
.investor-subtitle{font-size:13px;color:#94a3b8;line-height:1.55;}
.investor-pill-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;}
.investor-pill{display:inline-flex;align-items:center;gap:6px;border:1px solid #334155;background:#111827;border-radius:999px;padding:5px 10px;font-size:11px;color:#cbd5e1;font-weight:700;}
.investor-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:10px 0 24px;}
.investor-allocation-section{margin-top:8px;}
.investor-allocation-section .section-head{margin-top:0.25rem!important;margin-bottom:0.55rem!important;}
.investor-mini{background:#111827;border:1px solid #243044;border-radius:14px;padding:14px 15px;transition:all .18s ease;}
.investor-mini:hover{transform:translateY(-2px);border-color:#3b82f6;box-shadow:0 12px 24px rgba(0,0,0,.20);}
.investor-mini-label{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;font-weight:800;}
.investor-mini-value{font-size:18px;color:#f8fafc;font-weight:800;font-family:monospace;line-height:1.15;}
.investor-note{background:#0f172a;border:1px solid #263248;border-radius:14px;padding:14px 16px;color:#94a3b8;font-size:13px;line-height:1.65;margin:10px 0;}
.investor-note b{color:#e2e8f0;}
.investor-ai-box{background:linear-gradient(135deg,rgba(15,23,42,.98),rgba(30,41,59,.82));border:1px solid #334155;border-radius:16px;padding:17px 19px;margin:12px 0 18px;box-shadow:0 14px 34px rgba(0,0,0,.22);}
.investor-ai-kicker{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.14em;font-weight:900;margin-bottom:7px;}
.investor-ai-headline{font-size:19px;color:#f8fafc;font-weight:850;letter-spacing:-.015em;line-height:1.25;margin-bottom:8px;}
.investor-ai-body{font-size:13px;color:#cbd5e1;line-height:1.72;}
.investor-ai-body b{color:#f8fafc;}
@media(max-width:1100px){.investor-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:700px){.investor-grid{grid-template-columns:1fr;}}

</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════
PLOT_BG  = "#0d0f14"
GRID_COL = "#1a1e2a"
TICK_COL = "#475569"
TEXT_COL = "#64748b"
GREEN    = "#10b981"; RED  = "#ef4444"; BLUE  = "#3b82f6"
AMBER    = "#f59e0b"; PURPLE="#8b5cf6"; TEAL  = "#06b6d4"


# ══════════════════════════════════════════════════════════════════
#  ENGLISH-ONLY TEXT HELPERS
# ══════════════════════════════════════════════════════════════════
# Chinese translation/deep-translator support was removed for speed.
# These tiny compatibility helpers let the existing UI code stay unchanged.

def lang_code():
    return "en"

def tr(text):
    return text

def translate_text_optional(text, target_lang="en"):
    return text or ""


MA_COLORS = {
    "MA5":  "#f8fafc",  # default white
    "MA10": "#06b6d4",
    "MA20": "#facc15",  # default yellow
    "MA50": "#f472b6",
    "MA120":"#22c55e",  # default green
    "MA200":"#fb923c",
}

# Shared plotly layout — NO internal legend, clean axes
def base_layout(height=300, title=""):
    layout = dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PLOT_BG,
        font=dict(family="'SF Mono','Fira Code',monospace", size=11, color=TEXT_COL),
        margin=dict(l=60, r=20, t=36 if title else 16, b=36),
        showlegend=False,          # ← all legends are HTML below the chart
        hovermode="x",
        hoverlabel=dict(
            bgcolor="#1e2433", bordercolor="#2e3448",
            font=dict(color="#e2e8f0", size=11, family="monospace"),
            namelength=20,
        ),
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(color=TICK_COL, size=10),
            linecolor="#252a38", showline=True,
            showspikes=True, spikecolor="#334155",
            spikethickness=1, spikedash="dot", spikemode="across",
        ),
        yaxis=dict(
            showgrid=True, gridcolor=GRID_COL, zeroline=False,
            tickfont=dict(color=TICK_COL, size=10),
            linecolor="#252a38", showline=True, side="right",
        ),
        height=height,
        xaxis_rangeslider_visible=False,
    )
    if title:
        layout["title"] = dict(text=title, font=dict(size=11, color="#475569"), x=0.01, y=0.98)
    return layout


def legend_html(items):
    """
    items = list of (label, color, style)
    style = "line" | "dash" | "dot" | "bar"
    Returns HTML string for a legend row below a chart.
    """
    pills = []
    for label, color, style in items:
        if style == "line":
            icon = f'<span class="legend-line" style="background:{color}"></span>'
        elif style in ("dash", "dot"):
            icon = f'<span class="legend-dash" style="border-color:{color}"></span>'
        elif style == "bar":
            icon = f'<span class="legend-line" style="background:{color};height:8px;border-radius:2px"></span>'
        else:
            icon = f'<span class="legend-line" style="background:{color}"></span>'
        pills.append(f'<span class="legend-pill">{icon}{label}</span>')
    return f'<div class="legend-row">{"".join(pills)}</div>'


# ══════════════════════════════════════════════════════════════════
#  DATA LAYER — FMP ONLY, YFINANCE-COMPATIBLE FIELD MAP
# ══════════════════════════════════════════════════════════════════
import os as _os
_FMP_V3_BASE = "https://financialmodelingprep.com/api/v3"
_FMP_STABLE_BASE = "https://financialmodelingprep.com/stable"
_FMP_BASE = _FMP_V3_BASE


# ── Performance / API-limit controls ──────────────────────────────
# Default FAST mode uses first successful FMP endpoint in each fallback group
# instead of calling every possible endpoint. Set SMARTSTOCK_DEEP_FMP=1 only
# when you want maximum field coverage and can tolerate many more API calls.
def _secret_or_env_bool(name, default=False):
    try:
        val = st.secrets.get(name, None)
    except Exception:
        val = None
    if val is None:
        val = _os.environ.get(name, None)
    if val is None:
        return bool(default)
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

SMARTSTOCK_FAST_MODE = not _secret_or_env_bool("SMARTSTOCK_DEEP_FMP", default=False)
FMP_TIMEOUT_SECONDS = float(_os.environ.get("SMARTSTOCK_FMP_TIMEOUT", "6"))
FMP_RAW_CACHE_TTL = int(_os.environ.get("SMARTSTOCK_FMP_RAW_CACHE_TTL", "3600"))
# Realized risk metrics should not silently depend on a stale hard-coded
# treasury rate. Set SMARTSTOCK_RISK_FREE_RATE=0.045 for 4.5%, etc.
RISK_FREE_ANNUAL_RATE = float(_os.environ.get("SMARTSTOCK_RISK_FREE_RATE", "0.00"))
_FMP_V4_BASE = "https://financialmodelingprep.com/api/v4"

# ── Thread-safe warmup cache ───────────────────────────────────────
# _fmp_warmup_parallel() fires a batch of FMP requests concurrently and stores
# raw results here. _fmp_get() checks this dict first so the subsequent
# sequential merge_records / rows_all calls are instant cache hits.
_WARMUP: dict = {}
_WARMUP_LOCK = threading.Lock()

def _fmp_warmup_parallel(endpoint_list):
    """
    Fire every (endpoint, params, base) request in parallel.
    Results land in _WARMUP so that the _fmp_get() calls that follow
    immediately find their data without making a second HTTP round-trip.
    Uses a plain thread pool — no Streamlit context required.
    """
    key = _get_fmp_key()
    if not key:
        return

    base_url_map = {
        "stable": _FMP_STABLE_BASE,
        "v4":     _FMP_V4_BASE,
        "v3":     _FMP_V3_BASE,
    }

    def _one(ep, params_items, base_str):
        wkey = (ep, params_items, base_str)
        with _WARMUP_LOCK:
            if wkey in _WARMUP:
                return
        base_url = base_url_map.get(base_str, _FMP_V3_BASE)
        p = {k: v for k, v in params_items}
        p["apikey"] = key
        try:
            r = _http_session().get(
                f"{base_url}/{ep.lstrip('/')}",
                params=p,
                timeout=FMP_TIMEOUT_SECONDS,
            )
            data = r.json() if r.status_code == 200 else {}
        except Exception:
            data = {}
        with _WARMUP_LOCK:
            _WARMUP[wkey] = data

    jobs = []
    for ep, params, base in endpoint_list:
        ep_clean = str(ep).lstrip("/")
        pi = _params_items(params or {})
        bs = str(base or "v3").lower()
        jobs.append((ep_clean, pi, bs))

    with ThreadPoolExecutor(max_workers=min(len(jobs), 10)) as ex:
        list(ex.map(lambda j: _one(*j), jobs))

@st.cache_resource(show_spinner=False)
def _http_session():
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "SmartStock/2.1 (+https://streamlit.io)",
        "Accept": "application/json,text/plain,*/*",
        "Connection": "keep-alive",
    })
    try:
        if Retry is not None:
            retry = Retry(
                total=2,
                connect=2,
                read=2,
                backoff_factor=0.25,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32, max_retries=retry)
            sess.mount("https://", adapter)
            sess.mount("http://", adapter)
    except Exception:
        pass
    return sess

def _params_items(params):
    return tuple(sorted((str(k), "" if v is None else str(v)) for k, v in dict(params or {}).items()))

def _key_fingerprint(key):
    return hashlib.sha1(str(key or "").encode("utf-8")).hexdigest()[:10]

@st.cache_data(ttl=FMP_RAW_CACHE_TTL, show_spinner=False)
def _fmp_get_cached(endpoint, params_items, base, key_fingerprint):
    """Cached raw FMP/RSS HTTP layer. Keeps repeated reruns from burning API limits."""
    del key_fingerprint
    key = _get_fmp_key()
    if not key:
        return {"__smartstock_error__": "FMP_API_KEY is missing in Streamlit Secrets/environment."}

    endpoint = str(endpoint).lstrip("/")
    base_l = str(base or "v3").lower()
    if base_l == "stable":
        base_url = _FMP_STABLE_BASE
    elif base_l == "v4":
        base_url = _FMP_V4_BASE
    else:
        base_url = _FMP_V3_BASE

    p = {k: v for k, v in tuple(params_items or ())}
    p["apikey"] = key
    try:
        r = _http_session().get(f"{base_url}/{endpoint}", params=p, timeout=FMP_TIMEOUT_SECONDS)
        if r.status_code != 200:
            return {"__smartstock_error__": f"FMP HTTP {r.status_code} from /{endpoint}: {r.text[:500]}"}
        try:
            data = r.json()
        except Exception:
            return {"__smartstock_error__": f"FMP returned non-JSON from /{endpoint}: {r.text[:500]}"}
        return data
    except Exception as e:
        return {"__smartstock_error__": f"FMP request failed for {endpoint}: {e}"}


def _get_fmp_key():
    """Load the FMP key for Streamlit Cloud or local runs.

    Streamlit Cloud secrets:
        FMP_API_KEY = "your_key"

    Local PowerShell:
        $env:FMP_API_KEY="your_key"
    """
    # Streamlit Secrets: flat keys
    try:
        for name in ("FMP_API_KEY", "fmp_api_key", "FINANCIAL_MODELING_PREP_API_KEY"):
            try:
                key = st.secrets.get(name, "")
            except Exception:
                key = ""
            if key:
                return str(key).strip()
    except Exception:
        pass

    # Streamlit Secrets: nested section [fmp]
    try:
        section = st.secrets.get("fmp", {})
        if isinstance(section, dict):
            for name in ("api_key", "FMP_API_KEY", "key"):
                key = section.get(name, "")
                if key:
                    return str(key).strip()
    except Exception:
        pass

    # Local environment variables
    for name in ("FMP_API_KEY", "fmp_api_key", "FINANCIAL_MODELING_PREP_API_KEY"):
        key = _os.environ.get(name, "")
        if key:
            return str(key).strip()
    return ""


_FMP_SYMBOL_MAP = {
    # Keep external/Yahoo-style commodity and crypto tickers compatible, but map
    # them to FMP's native symbols instead of ETF proxies. This makes the
    # Commodities tab show the actual commodity curves when the FMP plan allows it.
    "CL=F": "CLUSD", "BZ=F": "BZUSD", "GC=F": "GCUSD", "SI=F": "SIUSD", "HG=F": "HGUSD", "NG=F": "NGUSD",
    "BTC-USD": "BTCUSD", "ETH-USD": "ETHUSD",
}


def _fmp_symbol(symbol):
    s = str(symbol or "").upper().strip()
    return _FMP_SYMBOL_MAP.get(s, s)


def _period_to_days(period, default=730):
    txt = str(period or "2y").lower().strip()
    if txt == "max":
        return 7300
    m = re.fullmatch(r"(\d+)(d|mo|y)", txt)
    if not m:
        return default
    n, unit = int(m.group(1)), m.group(2)
    return n if unit == "d" else n * 30 if unit == "mo" else n * 365


def _remember_fmp_error(message):
    try:
        st.session_state["_last_fmp_error"] = clean_text(str(message))[:800]
    except Exception:
        pass


def _fmp_get(endpoint, params=None, base="v3"):
    """Call FMP and return JSON, rejecting API-error payloads.

    Uses a cached, pooled HTTP layer to avoid repeating identical requests on
    every Streamlit rerun. Supports base="v3", base="v4", and base="stable".
    Checks the parallel warmup cache (_WARMUP) first so that pre-warmed
    endpoints are served instantly without a second HTTP round-trip.
    """
    try:
        key = _get_fmp_key()
        if not key:
            _remember_fmp_error("FMP_API_KEY is missing in Streamlit Secrets/environment.")
            return None

        # ── Fast path: warmup cache ────────────────────────────────
        ep_clean  = str(endpoint).lstrip("/")
        pi        = _params_items(params)
        base_str  = str(base or "v3").lower()
        wkey      = (ep_clean, pi, base_str)
        with _WARMUP_LOCK:
            if wkey in _WARMUP:
                data = copy.deepcopy(_WARMUP.pop(wkey))
                # Reuse the validation logic below without re-fetching
                if isinstance(data, dict):
                    lowered = {str(k).lower(): v for k, v in data.items()}
                    if "error" in lowered or "error message" in lowered:
                        _remember_fmp_error(str(data)[:800])
                        return None
                    if "message" in lowered and not any(k in lowered for k in ("historical", "symbol", "date", "price", "results", "data")):
                        _remember_fmp_error(str(data)[:800])
                        return None
                    return copy.deepcopy(data) if data else None
                if isinstance(data, list):
                    return copy.deepcopy(data) if len(data) else None
                return None

        # ── Normal path: Streamlit cached HTTP layer ───────────────
        data = _fmp_get_cached(
            ep_clean,
            pi,
            base_str,
            _key_fingerprint(key),
        )
        if isinstance(data, dict) and "__smartstock_error__" in data:
            _remember_fmp_error(data.get("__smartstock_error__", "Unknown FMP error"))
            return None

        if isinstance(data, dict):
            lowered = {str(k).lower(): v for k, v in data.items()}
            if "error" in lowered or "error message" in lowered:
                _remember_fmp_error(str(data)[:800])
                return None
            if "message" in lowered and not any(k in lowered for k in ("historical", "symbol", "date", "price", "results", "data")):
                _remember_fmp_error(str(data)[:800])
                return None
            return copy.deepcopy(data) if data else None
        if isinstance(data, list):
            return copy.deepcopy(data) if len(data) else None
        return None
    except Exception as e:
        _remember_fmp_error(f"FMP request failed for {endpoint}: {e}")
        return None


def _fmp_get_stable(endpoint, params=None):
    return _fmp_get(endpoint, params=params, base="stable")


def _records(data):
    """Normalize common FMP response shapes to a list of dicts."""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("historical", "results", "data", "values"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        # Some stable endpoints return one record as a dict.
        if any(k in data for k in ("symbol", "date", "price", "marketCap", "mktCap", "companyName")):
            return [data]
    return []


def _first(data):
    rows = _records(data)
    return rows[0] if rows else {}


def _num(*values, default=None):
    for v in values:
        if v is None or v == "" or v == "None":
            continue
        try:
            if isinstance(v, str):
                v = v.replace(",", "").replace("$", "").replace("%", "").strip()
            x = float(v)
            if np.isfinite(x):
                return x
        except Exception:
            continue
    return default


def _text(*values, default=""):
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in {"none", "nan", "null"}:
            return s
    return default


def _pct_to_decimal(v):
    x = _num(v, default=None)
    if x is None:
        return None
    # FMP ratios usually return decimals already. If something comes as 12.3, treat it as percent.
    return x / 100 if abs(x) > 3 else x


def _parse_range_high_low(range_value):
    if not range_value:
        return None, None
    try:
        parts = str(range_value).replace(" ", "").split("-")
        if len(parts) >= 2:
            lo = _num(parts[0], default=None)
            hi = _num(parts[-1], default=None)
            return hi, lo
    except Exception:
        pass
    return None, None


def _estimate_row_date(row):
    """Best-effort date parser for analyst-estimate rows."""
    for key in ("date", "fiscalDateEnding", "calendarDate", "periodEndDate"):
        val = (row or {}).get(key)
        if val not in (None, ""):
            try:
                dt = pd.to_datetime(val, errors="coerce")
                if pd.notna(dt):
                    return dt.tz_localize(None) if getattr(dt, "tzinfo", None) else dt
            except Exception:
                pass
    # calendarYear alone is less precise; place it at fiscal-year end.
    y = _num((row or {}).get("calendarYear"), (row or {}).get("year"), default=None)
    if y:
        try:
            return pd.Timestamp(int(y), 12, 31)
        except Exception:
            pass
    return pd.NaT


def _select_forward_estimate_record(rows, metric_keys=("estimatedEpsAvg", "epsAvg", "epsAverage")):
    """Select the most appropriate forward analyst-estimate row.

    FMP can return multiple annual/quarterly estimate rows. For Forward EPS we
    want the nearest future fiscal period, not an arbitrary older or far-future
    row. If no future-dated estimate exists, use the newest row with a usable
    EPS estimate.
    """
    usable = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if _num(*(row.get(k) for k in metric_keys), default=None) is None:
            continue
        dt = _estimate_row_date(row)
        usable.append((dt, row))
    if not usable:
        return {}

    today = pd.Timestamp.today().normalize()
    future = [(dt, row) for dt, row in usable if pd.notna(dt) and dt >= today]
    if future:
        future.sort(key=lambda x: x[0])
        return future[0][1]

    dated = [(dt, row) for dt, row in usable if pd.notna(dt)]
    if dated:
        dated.sort(key=lambda x: x[0], reverse=True)
        return dated[0][1]

    return usable[0][1]


def _merge_nonempty(target, updates):
    for k, v in (updates or {}).items():
        if v is None or v == "" or (isinstance(v, float) and not np.isfinite(v)):
            continue
        # Do not overwrite a real nonzero value with zero from a weaker endpoint.
        if k in target and target[k] not in (None, "", 0, 0.0) and v in (0, 0.0):
            continue
        target[k] = v
    return target


def _normalize_ohlcv(df):
    """Normalize FMP price rows to OHLCV.

    If FMP returns adjusted columns, prefer them for the canonical OHLC fields.
    This keeps returns, moving averages, risk, and backtests split-adjusted when
    adjusted prices are available. If only adjClose is available, Close uses it
    while Open/High/Low remain the raw fields; this is still safer for return
    math than mixing old split-unadjusted closes into performance metrics.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    raw = df.copy()

    # Preserve adjusted close separately for future diagnostics.
    out = pd.DataFrame(index=raw.index)

    def pick(*cols):
        vals = []
        for c in cols:
            if c in raw.columns:
                vals.append(raw[c])
        if not vals:
            return None
        block = pd.concat(vals, axis=1)
        return block.bfill(axis=1).iloc[:, 0]

    date_col = pick("date", "label")
    if date_col is not None:
        out["date"] = pd.to_datetime(date_col, errors="coerce")
    elif isinstance(raw.index, pd.DatetimeIndex):
        out.index = raw.index
    else:
        return pd.DataFrame()

    # Prefer adjusted OHLC when provided. FMP stable stock full commonly returns
    # adjClose; some historical/legacy shapes also include adjusted OHLC aliases.
    out["Open"] = pick("adjOpen", "adjustedOpen", "open", "Open")
    out["High"] = pick("adjHigh", "adjustedHigh", "high", "High")
    out["Low"] = pick("adjLow", "adjustedLow", "low", "Low")
    out["Close"] = pick("adjClose", "adjustedClose", "close", "price", "Close")
    out["Volume"] = pick("volume", "Volume")
    adj_close = pick("adjClose", "adjustedClose")
    raw_close = pick("close", "Close")
    if adj_close is not None:
        out["Adj Close"] = adj_close
        # If FMP gives adjusted close but not adjusted OHLC, scale raw OHLC by
        # adjClose / raw close. This prevents split-adjusted closes from being
        # plotted against unadjusted opens/highs/lows on long-range candles.
        has_adj_ohl = any(c in raw.columns for c in ("adjOpen", "adjustedOpen", "adjHigh", "adjustedHigh", "adjLow", "adjustedLow"))
        if raw_close is not None and not has_adj_ohl:
            try:
                factor = pd.to_numeric(adj_close, errors="coerce") / pd.to_numeric(raw_close, errors="coerce").replace(0, np.nan)
                for _col in ("Open", "High", "Low"):
                    out[_col] = pd.to_numeric(out[_col], errors="coerce") * factor
            except Exception:
                pass

    if "date" in out.columns:
        out = out.dropna(subset=["date"]).set_index("date")
    out = out.sort_index()

    if "Close" not in out.columns or out["Close"].isna().all():
        return pd.DataFrame()

    for col in ["Open", "High", "Low"]:
        if col not in out.columns:
            out[col] = out["Close"]
    if "Volume" not in out.columns:
        out["Volume"] = 0

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["Open", "High", "Low"]:
        out[col] = out[col].fillna(out["Close"])
    out["Volume"] = out["Volume"].fillna(0)

    cols = ["Open", "High", "Low", "Close", "Volume"]
    if "Adj Close" in out.columns:
        out["Adj Close"] = pd.to_numeric(out["Adj Close"], errors="coerce")
        cols.append("Adj Close")
    return out[cols].dropna(subset=["Close"])

def _resample_ohlcv(df, rule):
    """Resample daily OHLCV data to weekly/monthly bars for yfinance-style intervals."""
    if df is None or df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df
    try:
        out = df.resample(rule).agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Close"])
        return out if not out.empty else df
    except Exception:
        return df


def _fmp_build_hist(ticker, period="2y"):
    """Fetch daily OHLCV history from FMP across stocks, indexes, commodities, crypto, and FX."""
    raw_symbol = str(ticker or "").upper().strip()
    sym = _fmp_symbol(raw_symbol)
    days = _period_to_days(period, default=730)
    try:
        date_to = pd.Timestamp.today().strftime("%Y-%m-%d")
        date_from = (pd.Timestamp.today() - pd.Timedelta(days=days + 10)).strftime("%Y-%m-%d")
        sym_path = quote_plus(sym)

        # Stable EOD is the current FMP route for stocks, indexes, commodities,
        # forex, and crypto. Legacy v3 is kept as a fallback for plans/accounts
        # where old endpoints are still enabled.
        attempts = [
            ("historical-price-eod/full", {"symbol": sym, "from": date_from, "to": date_to}, "stable"),
            ("historical-price-eod/light", {"symbol": sym, "from": date_from, "to": date_to}, "stable"),
            ("historical-price-full/" + sym_path, {"from": date_from, "to": date_to}, "v3"),
            ("historical-price-full/" + sym_path, {"timeseries": days}, "v3"),
        ]
        if sym.startswith("^"):
            attempts.extend([
                ("historical-price-full/index/" + sym_path, {"from": date_from, "to": date_to}, "v3"),
                ("historical-price-full/index/" + sym_path, {"timeseries": days}, "v3"),
            ])

        # Final no-date stable fallback can return the longest available series;
        # we trim it locally to the requested period.
        attempts.extend([
            ("historical-price-eod/full", {"symbol": sym}, "stable"),
            ("historical-price-eod/light", {"symbol": sym}, "stable"),
        ])

        for endpoint, params, base in attempts:
            data = _fmp_get(endpoint, params=params, base=base)
            rows = _records(data)
            if not rows:
                continue
            df = _normalize_ohlcv(pd.DataFrame(rows))
            if not df.empty:
                if len(df) > days + 5:
                    df = df.tail(days)
                return df

        # Last-resort one-row quote so the UI does not fully break.
        q = (_first(_fmp_get("quote", {"symbol": sym}, base="stable"))
             or _first(_fmp_get("quote-short", {"symbol": sym}, base="stable"))
             or _first(_fmp_get("quote/" + sym_path, base="v3")))
        price = _num(q.get("price"), q.get("previousClose"), q.get("close"), default=None)
        if price is not None:
            idx = [pd.Timestamp.today().normalize()]
            return pd.DataFrame({
                "Open": [_num(q.get("open"), default=price)],
                "High": [_num(q.get("dayHigh"), q.get("high"), default=price)],
                "Low": [_num(q.get("dayLow"), q.get("low"), default=price)],
                "Close": [price],
                "Volume": [_num(q.get("volume"), default=0)],
            }, index=idx)
        return pd.DataFrame()
    except Exception as e:
        _remember_fmp_error(f"FMP historical loader failed for {sym}: {e}")
        return pd.DataFrame()

def _fmp_build_intraday(ticker, period="5d", interval="5m"):
    interval_map = {
        "1m": "1min", "2m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
        "60m": "1hour", "90m": "1hour", "1h": "1hour", "1hour": "1hour", "4h": "4hour", "4hour": "4hour",
    }
    fmp_interval = interval_map.get(str(interval).lower(), str(interval).lower())
    sym = _fmp_symbol(ticker)
    try:
        attempts = [
            (f"historical-chart/{fmp_interval}", {"symbol": sym}, "stable"),
            (f"historical-chart/{fmp_interval}/{quote_plus(sym)}", {}, "v3"),
        ]
        for endpoint, params, base in attempts:
            data = _fmp_get(endpoint, params=params, base=base)
            df = _normalize_ohlcv(pd.DataFrame(_records(data))) if data else pd.DataFrame()
            if df.empty:
                continue
            cutoff = pd.Timestamp.today() - pd.Timedelta(days=_period_to_days(period, default=30))
            return df[df.index >= cutoff]
        return pd.DataFrame()
    except Exception as e:
        _remember_fmp_error(f"FMP intraday loader failed for {sym}: {e}")
        return pd.DataFrame()

def _fmp_statement_rows(endpoint, ticker, limit=8, period=None):
    sym = _fmp_symbol(ticker)
    rows = []
    params = {"limit": limit}
    if period:
        params["period"] = period
    # Try stable first, then v3.
    stable_params = {"symbol": sym, "limit": limit}
    if period:
        stable_params["period"] = period
    rows = _records(_fmp_get(endpoint, stable_params, base="stable"))
    if not rows:
        rows = _records(_fmp_get(f"{endpoint}/{sym}", params, base="v3"))
    return rows


def _fmp_statement_df(endpoint, ticker, limit=8, period=None):
    rows = _fmp_statement_rows(endpoint, ticker, limit=limit, period=period)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()
    drop_cols = {"date", "symbol", "reportedCurrency", "cik", "fillingDate", "acceptedDate", "calendarYear", "period", "link", "finalLink"}
    value_cols = [c for c in df.columns if c not in drop_cols]
    out = df[["date"] + value_cols].set_index("date").T
    out.columns = pd.to_datetime(out.columns, errors="ignore")
    return out



@st.cache_data(ttl=3600, show_spinner=False)
def _fmp_build_info(ticker):
    """Build a Yahoo-compatible info dict from FMP.

    This is the main data adapter for the app. The UI and models were originally
    built around yfinance's ``Ticker.info`` keys, so this function intentionally
    returns those same key names while sourcing data only from FMP.

    Important design choice:
    FMP's stable, legacy v3, annual, quarterly, and TTM endpoints can each return
    different subsets depending on plan and endpoint availability. We therefore
    merge all usable records instead of stopping at the first successful response.
    """
    sym = _fmp_symbol(ticker)
    info = {"symbol": sym, "quoteType": "EQUITY"}

    # ── Parallel pre-warm: fire all needed FMP endpoints concurrently ──
    # By the time merge_records / rows_all run sequentially below, every
    # response is already sitting in _WARMUP and is served instantly.
    _fmp_warmup_parallel([
        ("profile",                          {"symbol": sym},                    "stable"),
        (f"profile/{sym}",                   {},                                 "v3"),
        ("quote",                            {"symbol": sym},                    "stable"),
        ("quote-short",                      {"symbol": sym},                    "stable"),
        (f"quote/{sym}",                     {},                                 "v3"),
        ("key-metrics-ttm",                  {"symbol": sym},                    "stable"),
        (f"key-metrics-ttm/{sym}",           {},                                 "v3"),
        ("ratios-ttm",                       {"symbol": sym},                    "stable"),
        (f"ratios-ttm/{sym}",                {},                                 "v3"),
        ("financial-growth",                 {"symbol": sym, "limit": 4},        "stable"),
        (f"financial-growth/{sym}",          {"limit": 4},                       "v3"),
        ("income-statement-ttm",             {"symbol": sym},                    "stable"),
        (f"income-statement-ttm/{sym}",      {},                                 "v3"),
        ("balance-sheet-statement-ttm",      {"symbol": sym},                    "stable"),
        (f"balance-sheet-statement-ttm/{sym}", {},                               "v3"),
        ("cash-flow-statement-ttm",          {"symbol": sym},                    "stable"),
        (f"cash-flow-statement-ttm/{sym}",   {},                                 "v3"),
        ("income-statement",                 {"symbol": sym, "limit": 6, "period": "annual"},   "stable"),
        ("income-statement",                 {"symbol": sym, "limit": 8, "period": "quarter"},  "stable"),
        ("balance-sheet-statement",          {"symbol": sym, "limit": 6, "period": "annual"},   "stable"),
        ("cash-flow-statement",              {"symbol": sym, "limit": 6, "period": "annual"},   "stable"),
        ("enterprise-values",                {"symbol": sym, "limit": 4},        "stable"),
        (f"enterprise-values/{sym}",         {"limit": 4},                       "v3"),
        ("price-target-consensus",           {"symbol": sym},                    "stable"),
        ("grades-consensus",                 {"symbol": sym},                    "stable"),
        ("analyst-estimates",                {"symbol": sym, "period": "annual",  "page": 0, "limit": 10}, "stable"),
        ("analyst-estimates",                {"symbol": sym, "period": "quarter", "page": 0, "limit": 10}, "stable"),
        ("shares-float",                     {"symbol": sym},                    "stable"),
        ("short-interest",                   {"symbol": sym, "limit": 4},        "stable"),
    ])

    def N(*vals, default=None):
        return _num(*vals, default=default)

    def T(*vals, default=""):
        return _text(*vals, default=default)

    def P(*vals):
        for v in vals:
            x = _pct_to_decimal(v)
            if x is not None:
                return x
        return None

    def rows_all(attempts, stop_after_first=None, latest_only=True):
        """Return records from FMP fallback endpoints.

        In normal FAST mode this stops after the first endpoint that returns
        usable rows. This cuts first-load API calls dramatically while keeping
        fallback behavior. Set SMARTSTOCK_DEEP_FMP=1 to merge every fallback
        endpoint for maximum data coverage.
        """
        if stop_after_first is None:
            stop_after_first = SMARTSTOCK_FAST_MODE
        out = []
        seen = set()
        for endpoint, params, base in attempts:
            try:
                data = _fmp_get(endpoint, params=params or {}, base=base)
                rows = _records(data)
                if not rows:
                    continue
                # Most FMP endpoints return latest-first time-series rows. For Yahoo-style
                # ``info`` fields, using older rows can silently overwrite current data,
                # so only merge the latest row from each endpoint unless explicitly asked.
                if latest_only:
                    rows = rows[:1]
                for row in rows:
                    key = (endpoint, base, str(row.get("date", "")), str(row.get("calendarYear", "")), str(row.get("symbol", "")))
                    if key in seen and len(row) < 5:
                        continue
                    seen.add(key)
                    out.append(row)
                if stop_after_first and out:
                    return out
            except Exception:
                continue
        return out

    def merge_records(attempts, prefer="later"):
        """Merge multiple endpoint records into one dict, keeping non-empty values."""
        merged = {}
        records = rows_all(attempts)
        if prefer == "earlier":
            records = list(reversed(records))
        for row in records:
            for k, v in (row or {}).items():
                if v is None or v == "" or str(v).lower() in {"nan", "none", "null"}:
                    continue
                # Keep existing good nonzero value against a weaker zero value.
                if k in merged and merged[k] not in (None, "", 0, 0.0) and v in (0, 0.0, "0", "0.0"):
                    continue
                merged[k] = v
        return merged

    def first_rows(endpoint, limit=8, period=None):
        return _fmp_statement_rows(endpoint, sym, limit=limit, period=period)

    try:
        # ── Profile / quote / market data ───────────────────────────────
        profile = merge_records([
            ("profile", {"symbol": sym}, "stable"),
            (f"profile/{sym}", {}, "v3"),
            ("company/profile", {"symbol": sym}, "v3"),
        ])
        quote = merge_records([
            ("quote", {"symbol": sym}, "stable"),
            ("quote-short", {"symbol": sym}, "stable"),
            (f"quote/{sym}", {}, "v3"),
            (f"quote-short/{sym}", {}, "v3"),
        ])
        market_cap_row = merge_records([
            ("market-capitalization", {"symbol": sym}, "stable"),
            (f"market-capitalization/{sym}", {}, "v3"),
            ("market-capitalization-batch", {"symbols": sym}, "stable"),
        ])
        ev = merge_records([
            ("enterprise-values", {"symbol": sym, "limit": 4}, "stable"),
            (f"enterprise-values/{sym}", {"limit": 4}, "v3"),
        ])

        hi_from_range, lo_from_range = _parse_range_high_low(profile.get("range"))
        price = N(
            quote.get("price"), quote.get("currentPrice"), quote.get("lastSalePrice"),
            profile.get("price"), quote.get("previousClose"), quote.get("close"),
            default=None
        )
        market_cap = N(
            quote.get("marketCap"), quote.get("marketCapitalization"),
            profile.get("mktCap"), profile.get("marketCap"),
            market_cap_row.get("marketCap"), market_cap_row.get("marketCapTTM"),
            ev.get("marketCapitalization"), ev.get("marketCap"),
            default=None
        )

        _merge_nonempty(info, {
            "shortName": T(profile.get("companyName"), profile.get("name"), quote.get("name"), sym),
            "longName": T(profile.get("companyName"), profile.get("name"), quote.get("name"), sym),
            "symbol": T(profile.get("symbol"), quote.get("symbol"), sym),
            "sector": T(profile.get("sector"), quote.get("sector"), default=""),
            "industry": T(profile.get("industry"), quote.get("industry"), default=""),
            "country": T(profile.get("country"), default=""),
            "website": T(profile.get("website"), default=""),
            "longBusinessSummary": T(profile.get("description"), profile.get("companyDescription"), default=""),
            "fullTimeEmployees": N(profile.get("fullTimeEmployees"), profile.get("employees"), default=None),
            "exchange": T(profile.get("exchangeShortName"), profile.get("exchange"), quote.get("exchange"), quote.get("exchangeShortName"), default=""),
            "currency": T(profile.get("currency"), quote.get("currency"), default="USD"),
            "ceo": T(profile.get("ceo"), default=""),
            "logo_url": T(profile.get("image"), default=""),
            "regularMarketPrice": price,
            "currentPrice": price,
            "previousClose": N(quote.get("previousClose"), quote.get("previous_close"), default=None),
            "open": N(quote.get("open"), default=None),
            "dayHigh": N(quote.get("dayHigh"), quote.get("high"), default=None),
            "dayLow": N(quote.get("dayLow"), quote.get("low"), default=None),
            "marketCap": market_cap,
            "volume": N(quote.get("volume"), profile.get("volAvg"), default=None),
            "averageVolume": N(quote.get("avgVolume"), quote.get("avgVolume10D"), profile.get("volAvg"), default=None),
            "beta": N(profile.get("beta"), quote.get("beta"), default=None),
            "fiftyTwoWeekHigh": N(quote.get("yearHigh"), quote.get("fiftyTwoWeekHigh"), profile.get("fiftyTwoWeekHigh"), hi_from_range, default=None),
            "fiftyTwoWeekLow": N(quote.get("yearLow"), quote.get("fiftyTwoWeekLow"), profile.get("fiftyTwoWeekLow"), lo_from_range, default=None),
            "trailingPE": N(quote.get("pe"), quote.get("peRatio"), profile.get("pe"), default=None),
            "trailingEps": N(quote.get("eps"), quote.get("epsTTM"), profile.get("eps"), default=None),
        })
        last_div = N(profile.get("lastDiv"), quote.get("lastDiv"), default=None)
        if last_div is not None and price not in (None, 0):
            info["dividendYield"] = last_div / price

        # ── Ratios / key metrics / estimates ────────────────────────────
        km = merge_records([
            ("key-metrics-ttm", {"symbol": sym}, "stable"),
            ("key-metrics", {"symbol": sym, "limit": 4}, "stable"),
            (f"key-metrics-ttm/{sym}", {}, "v3"),
            (f"key-metrics/{sym}", {"limit": 4}, "v3"),
        ])
        ratios = merge_records([
            ("ratios-ttm", {"symbol": sym}, "stable"),
            ("metrics-ratios-ttm", {"symbol": sym}, "stable"),
            ("ratios", {"symbol": sym, "limit": 4}, "stable"),
            ("metrics-ratios", {"symbol": sym, "limit": 4}, "stable"),
            (f"ratios-ttm/{sym}", {}, "v3"),
            (f"ratios/{sym}", {"limit": 4}, "v3"),
        ])
        growth = merge_records([
            ("financial-growth", {"symbol": sym, "limit": 4}, "stable"),
            ("income-statement-growth", {"symbol": sym, "limit": 4}, "stable"),
            (f"financial-growth/{sym}", {"limit": 4}, "v3"),
            (f"income-statement-growth/{sym}", {"limit": 4}, "v3"),
        ])

        pe = N(km.get("peRatioTTM"), ratios.get("priceEarningsRatioTTM"), km.get("peRatio"), ratios.get("priceEarningsRatio"), info.get("trailingPE"), default=None)
        # Forward P/E must not fall back to trailing P/E/TTM P/E. It is only
        # trusted if a direct forward P/E field exists, otherwise reconstructed
        # later from current price / selected Forward EPS.
        fpe = N(quote.get("forwardPE"), quote.get("forwardPe"), default=None)
        ps = N(km.get("priceToSalesRatioTTM"), ratios.get("priceToSalesRatioTTM"), km.get("priceToSalesRatio"), ratios.get("priceToSalesRatio"), default=None)
        pb = N(km.get("pbRatioTTM"), km.get("priceToBookRatioTTM"), ratios.get("priceToBookRatioTTM"), km.get("pbRatio"), km.get("priceToBookRatio"), ratios.get("priceBookValueRatio"), default=None)
        peg = N(km.get("pegRatioTTM"), km.get("pegRatio"), ratios.get("priceEarningsToGrowthRatioTTM"), ratios.get("pegRatio"), default=None)
        ev_to_ebitda = N(km.get("evToEBITDATTM"), km.get("enterpriseValueOverEBITDATTM"), km.get("enterpriseValueOverEBITDA"), ratios.get("enterpriseValueMultipleTTM"), default=None)
        ev_to_rev = N(km.get("evToSalesRatioTTM"), km.get("evToSalesRatio"), km.get("enterpriseValueOverRevenue"), default=None)

        _merge_nonempty(info, {
            "trailingPE": pe,
            "forwardPE": fpe,
            "priceToSalesTrailing12Months": ps,
            "priceToBook": pb,
            "pegRatio": peg,
            "enterpriseToEbitda": ev_to_ebitda,
            "enterpriseToRevenue": ev_to_rev,
            "returnOnEquity": P(km.get("roeTTM"), km.get("returnOnEquityTTM"), km.get("roe"), ratios.get("returnOnEquityTTM"), ratios.get("returnOnEquity")),
            "returnOnAssets": P(km.get("roaTTM"), km.get("returnOnAssetsTTM"), km.get("roa"), ratios.get("returnOnAssetsTTM"), ratios.get("returnOnAssets")),
            "currentRatio": N(km.get("currentRatioTTM"), km.get("currentRatio"), ratios.get("currentRatioTTM"), ratios.get("currentRatio"), default=None),
            "quickRatio": N(km.get("quickRatioTTM"), km.get("quickRatio"), ratios.get("quickRatioTTM"), ratios.get("quickRatio"), default=None),
            "payoutRatio": P(km.get("payoutRatioTTM"), km.get("payoutRatio"), ratios.get("payoutRatioTTM"), ratios.get("payoutRatio")),
            "dividendYield": P(km.get("dividendYieldTTM"), km.get("dividendYield"), ratios.get("dividendYieldTTM"), info.get("dividendYield")),
        })

        debt_equity_raw = N(km.get("debtToEquityTTM"), km.get("debtToEquity"), ratios.get("debtEquityRatioTTM"), ratios.get("debtToEquityRatioTTM"), ratios.get("debtEquityRatio"), ratios.get("debtToEquityRatio"), default=None)
        if debt_equity_raw is not None:
            info["debtToEquity"] = debt_equity_raw * 100 if abs(debt_equity_raw) < 20 else debt_equity_raw

        # ── Financial statements: TTM + latest annual + latest quarterly ─
        income_ttm = merge_records([
            ("income-statement-ttm", {"symbol": sym}, "stable"),
            (f"income-statement-ttm/{sym}", {}, "v3"),
        ])
        balance_ttm = merge_records([
            ("balance-sheet-statement-ttm", {"symbol": sym}, "stable"),
            (f"balance-sheet-statement-ttm/{sym}", {}, "v3"),
        ])
        cash_ttm = merge_records([
            ("cash-flow-statement-ttm", {"symbol": sym}, "stable"),
            (f"cash-flow-statement-ttm/{sym}", {}, "v3"),
        ])

        income_annual = first_rows("income-statement", limit=6, period="annual")
        income_quarter = first_rows("income-statement", limit=8, period="quarter")
        balance_annual = first_rows("balance-sheet-statement", limit=6, period="annual")
        balance_quarter = first_rows("balance-sheet-statement", limit=8, period="quarter")
        cash_annual = first_rows("cash-flow-statement", limit=6, period="annual")
        cash_quarter = first_rows("cash-flow-statement", limit=8, period="quarter")

        # Prefer TTM for flow items, otherwise annual, otherwise latest quarter.
        latest_income = {}
        for row in ([income_quarter[0]] if income_quarter else []) + ([income_annual[0]] if income_annual else []) + ([income_ttm] if income_ttm else []):
            _merge_nonempty(latest_income, row)
        # For balance sheet, latest quarter is usually more current than annual/TTM.
        latest_balance = {}
        for row in ([balance_annual[0]] if balance_annual else []) + ([balance_ttm] if balance_ttm else []) + ([balance_quarter[0]] if balance_quarter else []):
            _merge_nonempty(latest_balance, row)
        latest_cash = {}
        for row in ([cash_quarter[0]] if cash_quarter else []) + ([cash_annual[0]] if cash_annual else []) + ([cash_ttm] if cash_ttm else []):
            _merge_nonempty(latest_cash, row)

        prev_income = income_annual[1] if len(income_annual) > 1 else (income_quarter[4] if len(income_quarter) > 4 else income_quarter[1] if len(income_quarter) > 1 else {})

        shares = N(
            quote.get("sharesOutstanding"), profile.get("sharesOutstanding"),
            ev.get("numberOfShares"), ev.get("sharesNumber"),
            km.get("weightedAverageShsOutTTM"), latest_income.get("weightedAverageShsOut"),
            latest_income.get("weightedAverageShsOutDil"), market_cap and price and market_cap / price,
            default=None
        )
        rev_now = N(latest_income.get("revenue"), latest_income.get("revenueTTM"), km.get("revenueTTM"), (km.get("revenuePerShareTTM") * shares if N(km.get("revenuePerShareTTM"), default=None) is not None and shares else None), default=None)
        rev_prev = N(prev_income.get("revenue"), default=None)
        eps_now = N(latest_income.get("eps"), latest_income.get("epsTTM"), latest_income.get("epsdiluted"), latest_income.get("epsDiluted"), km.get("netIncomePerShareTTM"), info.get("trailingEps"), default=None)
        eps_prev = N(prev_income.get("eps"), prev_income.get("epsdiluted"), prev_income.get("epsDiluted"), default=None)
        net_income = N(latest_income.get("netIncome"), latest_income.get("netIncomeTTM"), latest_income.get("netIncomeCommonStockholders"), latest_income.get("netIncomeAvailableToCommonShareholders"), default=None)
        ebitda = N(latest_income.get("ebitda"), latest_income.get("ebitdaTTM"), km.get("ebitdaTTM"), default=None)
        if ebitda is None:
            oi = N(latest_income.get("operatingIncome"), default=None)
            da = N(latest_income.get("depreciationAndAmortization"), latest_cash.get("depreciationAndAmortization"), default=None)
            if oi is not None and da is not None:
                ebitda = oi + da

        std = N(latest_balance.get("shortTermDebt"), latest_balance.get("shortTermBorrowings"), default=0) or 0
        ltd = N(latest_balance.get("longTermDebt"), latest_balance.get("longTermDebtNoncurrent"), default=0) or 0
        total_debt = N(latest_balance.get("totalDebt"), latest_balance.get("totalDebtTTM"), std + ltd if (std or ltd) else None, default=None)
        total_cash = N(latest_balance.get("cashAndCashEquivalents"), latest_balance.get("cashAndShortTermInvestments"), latest_balance.get("cashCashEquivalentsAndShortTermInvestments"), default=None)
        total_equity = N(latest_balance.get("totalStockholdersEquity"), latest_balance.get("totalShareholdersEquity"), latest_balance.get("totalEquity"), default=None)
        total_assets = N(latest_balance.get("totalAssets"), default=None)
        current_assets = N(latest_balance.get("totalCurrentAssets"), default=None)
        current_liabilities = N(latest_balance.get("totalCurrentLiabilities"), default=None)

        ocf = N(latest_cash.get("operatingCashFlow"), latest_cash.get("netCashProvidedByOperatingActivities"), latest_cash.get("netCashProvidedByOperatingActivitiesTTM"), default=None)
        capex = N(latest_cash.get("capitalExpenditure"), latest_cash.get("capitalExpenditures"), latest_cash.get("capitalExpenditureTTM"), default=None)
        fcf = N(latest_cash.get("freeCashFlow"), latest_cash.get("freeCashFlowTTM"), km.get("freeCashFlowTTM"), default=None)
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex

        # Prefer FMP's own growth endpoint. Manual growth fallback only compares
        # like-for-like annual rows, otherwise latest TTM vs old annual rows can
        # produce misleading growth rates.
        revenue_growth = P(growth.get("revenueGrowth"), growth.get("growthRevenue"), growth.get("growthRevenueTTM"))
        earnings_growth = P(growth.get("epsgrowth"), growth.get("epsGrowth"), growth.get("growthEPS"), growth.get("growthEPSDiluted"))
        if revenue_growth is None and len(income_annual) > 1:
            a0, a1 = income_annual[0], income_annual[1]
            r0, r1 = N(a0.get("revenue"), default=None), N(a1.get("revenue"), default=None)
            revenue_growth = (r0 - r1) / abs(r1) if r0 is not None and r1 not in (None, 0) else None
        if earnings_growth is None and len(income_annual) > 1:
            a0, a1 = income_annual[0], income_annual[1]
            e0 = N(a0.get("eps"), a0.get("epsdiluted"), a0.get("epsDiluted"), default=None)
            e1 = N(a1.get("eps"), a1.get("epsdiluted"), a1.get("epsDiluted"), default=None)
            earnings_growth = (e0 - e1) / abs(e1) if e0 is not None and e1 not in (None, 0) else None
        if revenue_growth is None and len(income_quarter) > 4:
            q0, q4 = income_quarter[0], income_quarter[4]
            r0, r4 = N(q0.get("revenue"), default=None), N(q4.get("revenue"), default=None)
            revenue_growth = (r0 - r4) / abs(r4) if r0 is not None and r4 not in (None, 0) else None
        if earnings_growth is None and len(income_quarter) > 4:
            q0, q4 = income_quarter[0], income_quarter[4]
            e0 = N(q0.get("eps"), q0.get("epsdiluted"), q0.get("epsDiluted"), default=None)
            e4 = N(q4.get("eps"), q4.get("epsdiluted"), q4.get("epsDiluted"), default=None)
            earnings_growth = (e0 - e4) / abs(e4) if e0 is not None and e4 not in (None, 0) else None

        book_value_per_share = N(km.get("bookValuePerShareTTM"), km.get("bookValuePerShare"), ratios.get("bookValuePerShare"), default=None)
        if book_value_per_share is None and total_equity is not None and shares not in (None, 0):
            book_value_per_share = total_equity / shares

        _merge_nonempty(info, {
            "totalRevenue": rev_now,
            "netIncomeToCommon": net_income,
            "ebitda": ebitda,
            "trailingEps": eps_now,
            # Forward EPS should come from direct quote fields or the analyst-estimates endpoint below.
            "forwardEps": N(quote.get("epsEstimatedNextYear"), quote.get("forwardEps"), default=None),
            "revenueGrowth": revenue_growth,
            "earningsGrowth": earnings_growth,
            "totalDebt": total_debt,
            "totalCash": total_cash,
            "bookValue": book_value_per_share,
            "freeCashflow": fcf,
            "operatingCashflow": ocf,
            "sharesOutstanding": shares,
            "interestExpense": N(latest_income.get("interestExpense"), default=None),
        })

        # ── Margins and fallback computations ───────────────────────────
        gross_margin = P(ratios.get("grossProfitMarginTTM"), ratios.get("grossProfitMargin"), km.get("grossProfitMarginTTM"), km.get("grossProfitMargin"))
        op_margin = P(ratios.get("operatingProfitMarginTTM"), ratios.get("operatingProfitMargin"), km.get("operatingProfitMarginTTM"), km.get("operatingProfitMargin"))
        net_margin = P(ratios.get("netProfitMarginTTM"), ratios.get("netProfitMargin"), km.get("netProfitMarginTTM"), km.get("netProfitMargin"))
        ebitda_margin = P(ratios.get("ebitdaMarginTTM"), ratios.get("ebitdaMargin"), km.get("ebitdaMarginTTM"), km.get("ebitdaMargin"))

        if rev_now not in (None, 0):
            gp = N(latest_income.get("grossProfit"), default=None)
            oi = N(latest_income.get("operatingIncome"), default=None)
            if gross_margin is None and gp is not None:
                gross_margin = gp / rev_now
            if op_margin is None and oi is not None:
                op_margin = oi / rev_now
            if net_margin is None and net_income is not None:
                net_margin = net_income / rev_now
            if ebitda_margin is None and ebitda is not None:
                ebitda_margin = ebitda / rev_now

        if info.get("returnOnEquity") is None and net_income is not None and total_equity not in (None, 0):
            info["returnOnEquity"] = net_income / total_equity
        if info.get("returnOnAssets") is None and net_income is not None and total_assets not in (None, 0):
            info["returnOnAssets"] = net_income / total_assets
        if info.get("currentRatio") is None and current_assets is not None and current_liabilities not in (None, 0):
            info["currentRatio"] = current_assets / current_liabilities
        if info.get("quickRatio") is None and current_liabilities not in (None, 0):
            cash = N(latest_balance.get("cashAndCashEquivalents"), default=0) or 0
            sti = N(latest_balance.get("shortTermInvestments"), default=0) or 0
            ar = N(latest_balance.get("netReceivables"), latest_balance.get("accountReceivables"), default=0) or 0
            info["quickRatio"] = (cash + sti + ar) / current_liabilities
        if info.get("debtToEquity") is None and total_debt is not None and total_equity not in (None, 0):
            info["debtToEquity"] = (total_debt / total_equity) * 100

        _merge_nonempty(info, {
            "grossMargins": gross_margin,
            "operatingMargins": op_margin,
            "profitMargins": net_margin,
            "ebitdaMargins": ebitda_margin,
        })

        # ── Shares float and short interest ─────────────────────────────
        shares_float = merge_records([
            ("shares-float", {"symbol": sym}, "stable"),
            ("shares_float", {"symbol": sym}, "v4"),
            ("shares_float", {"symbol": sym}, "v3"),
            (f"shares_float/{sym}", {}, "v4"),
        ])
        float_shares = N(shares_float.get("floatShares"), shares_float.get("float"), shares_float.get("freeFloat"), shares_float.get("freeFloatShares"), default=None)
        short_row = merge_records([
            ("short-interest", {"symbol": sym, "limit": 4}, "stable"),
            ("short_interest", {"symbol": sym, "limit": 4}, "v4"),
            (f"short_interest/{sym}", {"limit": 4}, "v4"),
        ])
        short_pct = P(short_row.get("shortPercentOfFloat"), short_row.get("shortFloatPercent"), short_row.get("shortPercent"))
        if short_pct is None and float_shares not in (None, 0):
            short_interest = N(short_row.get("shortInterest"), short_row.get("sharesShort"), default=None)
            if short_interest is not None:
                short_pct = short_interest / float_shares

        _merge_nonempty(info, {
            "floatShares": float_shares,
            "shortPercentOfFloat": short_pct,
        })

        # ── Analyst targets / recommendations ──────────────────────────
        target = merge_records([
            ("price-target-consensus", {"symbol": sym}, "stable"),
            (f"price-target-consensus/{sym}", {}, "v3"),
            ("price-target-summary", {"symbol": sym}, "stable"),
        ])
        analyst_est_rows_annual = rows_all([
            # Stable docs require symbol + period + page + limit. Keep v3 as a fallback.
            ("analyst-estimates", {"symbol": sym, "period": "annual", "page": 0, "limit": 10}, "stable"),
            (f"analyst-estimates/{sym}", {"period": "annual", "limit": 10}, "v3"),
        ], stop_after_first=False, latest_only=False)
        analyst_est_rows_quarter = rows_all([
            ("analyst-estimates", {"symbol": sym, "period": "quarter", "page": 0, "limit": 10}, "stable"),
            (f"analyst-estimates/{sym}", {"period": "quarter", "limit": 10}, "v3"),
        ], stop_after_first=False, latest_only=False)
        # Use annual Forward EPS first; quarter estimates are a fallback only.
        analyst_est = (_select_forward_estimate_record(analyst_est_rows_annual)
                       or _select_forward_estimate_record(analyst_est_rows_quarter))
        rec_rows = rows_all([
            # Current stable analyst-rating consensus endpoint.
            ("grades-consensus", {"symbol": sym}, "stable"),
            # Legacy fallback. Do not use ratings-snapshot here: that is a financial health grade, not analyst consensus.
            (f"analyst-stock-recommendations/{sym}", {"limit": 5}, "v3"),
        ], stop_after_first=False)
        rec_key, rec_mean, rec_total, rec_source = None, None, None, ""
        if rec_rows:
            r = rec_rows[0]
            strong_buys = N(r.get("strongBuy"), r.get("analystRatingsStrongBuy"), r.get("strong_buy"), default=0) or 0
            buys = N(r.get("buy"), r.get("analystRatingsBuy"), r.get("analystRatingsbuy"), default=0) or 0
            holds = N(r.get("hold"), r.get("analystRatingsHold"), default=0) or 0
            sells = N(r.get("sell"), r.get("analystRatingsSell"), default=0) or 0
            strong_sells = N(r.get("strongSell"), r.get("analystRatingsStrongSell"), r.get("strong_sell"), default=0) or 0
            rec_total = strong_buys + buys + holds + sells + strong_sells
            if rec_total:
                # Yahoo-style score where 1=Strong Buy and 5=Strong Sell.
                rec_mean = (1 * strong_buys + 2 * buys + 3 * holds + 4 * sells + 5 * strong_sells) / rec_total
                if rec_mean <= 1.5:
                    rec_key = "strong buy"
                elif rec_mean <= 2.5:
                    rec_key = "buy"
                elif rec_mean < 3.5:
                    rec_key = "hold"
                elif rec_mean < 4.5:
                    rec_key = "sell"
                else:
                    rec_key = "strong sell"
                rec_source = "FMP grades-consensus" if any(k in r for k in ("strongBuy", "strongSell")) else "FMP legacy analyst-stock-recommendations"

        if rec_total:
            info["recommendationAnalystCount"] = rec_total

        if info.get("forwardEps") is None:
            _merge_nonempty(info, {
                "forwardEps": N(
                    analyst_est.get("estimatedEpsAvg"), analyst_est.get("epsAvg"), analyst_est.get("epsAverage"),
                    analyst_est.get("estimatedEpsHigh"), analyst_est.get("estimatedEpsLow"), default=None
                )
            })

        _merge_nonempty(info, {
            "targetLowPrice": N(target.get("targetLow"), target.get("targetLowPrice"), target.get("priceTargetLow"), target.get("targetLowEstimate"), default=None),
            "targetMeanPrice": N(target.get("targetConsensus"), target.get("targetMeanPrice"), target.get("priceTargetAverage"), target.get("targetPrice"), target.get("priceTargetConsensus"), default=None),
            "targetHighPrice": N(target.get("targetHigh"), target.get("targetHighPrice"), target.get("priceTargetHigh"), target.get("targetHighEstimate"), default=None),
            "numberOfAnalystOpinions": N(target.get("numberOfAnalysts"), target.get("analystCount"), target.get("priceTargetAnalystCount"), rec_total, default=None),
            "recommendationKey": rec_key or "",
            "recommendationMean": rec_mean,
            "recommendationSource": rec_source,
            "recommendationAnalystCount": rec_total,
        })
        if info.get("numberOfAnalystOpinions") in (None, "", 0, 0.0) and rec_total:
            info["numberOfAnalystOpinions"] = rec_total
        fwd_eps_for_pe = N(info.get("forwardEps"), default=None)
        if fwd_eps_for_pe is not None and fwd_eps_for_pe <= 0:
            info["forwardEps"] = None
            info["forwardPE"] = None
        elif info.get("forwardPE") in (None, "", 0, 0.0):
            if price not in (None, 0) and fwd_eps_for_pe not in (None, 0):
                info["forwardPE"] = price / fwd_eps_for_pe
        if N(info.get("forwardPE"), default=None) is not None and N(info.get("forwardPE"), default=None) <= 0:
            info["forwardPE"] = None


        # Final fallback computations that help old model calculations.
        if info.get("sharesOutstanding") is None and market_cap not in (None, 0) and price not in (None, 0):
            info["sharesOutstanding"] = market_cap / price
        if info.get("priceToSalesTrailing12Months") is None and market_cap not in (None, 0) and info.get("totalRevenue") not in (None, 0):
            info["priceToSalesTrailing12Months"] = market_cap / info["totalRevenue"]
        # Enterprise value and EV multiples can be reconstructed when FMP key-metrics misses them.
        if info.get("enterpriseValue") is None and market_cap not in (None, 0):
            td = N(info.get("totalDebt"), default=0) or 0
            cash = N(info.get("totalCash"), default=0) or 0
            info["enterpriseValue"] = market_cap + td - cash
        if info.get("enterpriseToRevenue") is None and info.get("enterpriseValue") not in (None, 0) and info.get("totalRevenue") not in (None, 0):
            info["enterpriseToRevenue"] = info["enterpriseValue"] / info["totalRevenue"]
        if info.get("enterpriseToEbitda") is None and info.get("enterpriseValue") not in (None, 0) and info.get("ebitda") not in (None, 0):
            info["enterpriseToEbitda"] = info["enterpriseValue"] / info["ebitda"]
        if info.get("payoutRatio") is None:
            div_paid = N(latest_cash.get("dividendsPaid"), latest_cash.get("commonDividendsPaid"), latest_cash.get("dividendsPaidTTM"), default=None)
            ni = N(info.get("netIncomeToCommon"), default=None)
            if div_paid is not None and ni not in (None, 0) and ni > 0:
                info["payoutRatio"] = abs(div_paid) / ni
            elif info.get("dividendYield") not in (None, 0) and price not in (None, 0) and info.get("trailingEps") not in (None, 0) and info.get("trailingEps") > 0:
                info["payoutRatio"] = (info["dividendYield"] * price) / info["trailingEps"]
        if info.get("trailingPE") is None and price not in (None, 0) and info.get("trailingEps") not in (None, 0):
            info["trailingPE"] = price / info["trailingEps"]
        if info.get("priceToBook") is None and price not in (None, 0) and info.get("bookValue") not in (None, 0):
            info["priceToBook"] = price / info["bookValue"]

        info.setdefault("shortName", sym)
        info.setdefault("longName", info.get("shortName", sym))
        return info

    except Exception as e:
        _remember_fmp_error(f"FMP info builder failed for {sym}: {e}")
        info.setdefault("shortName", sym)
        info.setdefault("longName", info.get("shortName", sym))
        return info


def _fmp_repair_ui_fields(info, ticker, hist=None):
    """Repair final Yahoo-style fields that the old UI expects."""
    info = dict(info or {})
    sym = _fmp_symbol(ticker)

    # ── Fast-path: skip re-fetching when _fmp_build_info already filled
    # all critical fields.  The repair is only for genuine gaps.
    _REPAIR_CRITICAL = {
        "currentPrice", "marketCap", "totalRevenue",
        "grossMargins", "profitMargins", "returnOnEquity",
    }
    if all(info.get(f) not in (None, "", 0, 0.0) for f in _REPAIR_CRITICAL):
        # Still do the lightweight averageVolume fallback from hist
        if info.get("averageVolume") in (None, "", 0, 0.0) and hist is not None and not getattr(hist, "empty", True) and "Volume" in hist.columns:
            try:
                av = pd.to_numeric(hist["Volume"], errors="coerce").dropna().tail(60).mean()
                if np.isfinite(av) and av > 0:
                    info["averageVolume"] = float(av)
            except Exception:
                pass
        return info

    def n(*vals, default=None):
        return _num(*vals, default=default)

    def pct(*vals):
        for v in vals:
            x = _pct_to_decimal(v)
            if x is not None:
                return x
        return None

    def one(endpoint, params=None, base="v3"):
        try:
            rs = _records(_fmp_get(endpoint, params or {}, base=base))
            return rs[0] if rs else {}
        except Exception:
            return {}

    def merge_one(attempts, latest_only=True):
        merged = {}
        for endpoint, params, base in attempts:
            try:
                rows = _records(_fmp_get(endpoint, params or {}, base=base))
                if latest_only:
                    rows = rows[:1]
                for row in rows:
                    for k, v in (row or {}).items():
                        if v is None or v == "" or str(v).lower() in {"nan", "none", "null"}:
                            continue
                        if k in merged and merged[k] not in (None, "", 0, 0.0) and v in (0, 0.0, "0", "0.0"):
                            continue
                        merged[k] = v
                if SMARTSTOCK_FAST_MODE and merged:
                    break          # stop after first endpoint that returned data
            except Exception:
                continue
        return merged

    def set_missing(k, *vals, pctval=False):
        if info.get(k) not in (None, "", 0, 0.0):
            return
        v = pct(*vals) if pctval else n(*vals, default=None)
        if v not in (None, ""):
            info[k] = v

    q = merge_one([("quote", {"symbol": sym}, "stable"), ("quote-short", {"symbol": sym}, "stable"), (f"quote/{sym}", {}, "v3")])
    prof = merge_one([("profile", {"symbol": sym}, "stable"), (f"profile/{sym}", {}, "v3")])
    km = merge_one([("key-metrics-ttm", {"symbol": sym}, "stable"), (f"key-metrics-ttm/{sym}", {}, "v3")])
    rt = merge_one([("ratios-ttm", {"symbol": sym}, "stable"), ("metrics-ratios-ttm", {"symbol": sym}, "stable"), (f"ratios-ttm/{sym}", {}, "v3")])
    inc = merge_one([("income-statement-ttm", {"symbol": sym}, "stable"), (f"income-statement-ttm/{sym}", {}, "v3"), (f"income-statement/{sym}", {"limit": 1}, "v3")])
    bal = merge_one([("balance-sheet-statement", {"symbol": sym, "limit": 1, "period": "quarter"}, "stable"), (f"balance-sheet-statement/{sym}", {"limit": 1, "period": "quarter"}, "v3"), (f"balance-sheet-statement/{sym}", {"limit": 1}, "v3")])
    cf = merge_one([("cash-flow-statement-ttm", {"symbol": sym}, "stable"), (f"cash-flow-statement-ttm/{sym}", {}, "v3"), (f"cash-flow-statement/{sym}", {"limit": 1}, "v3")])
    gr = merge_one([("financial-growth", {"symbol": sym, "limit": 1}, "stable"), (f"financial-growth/{sym}", {"limit": 1}, "v3")])

    ae_annual_rows = []
    ae_quarter_rows = []
    for endpoint, params, base in [
        ("analyst-estimates", {"symbol": sym, "period": "annual", "page": 0, "limit": 10}, "stable"),
        (f"analyst-estimates/{sym}", {"period": "annual", "limit": 10}, "v3"),
    ]:
        ae_annual_rows.extend(_records(_fmp_get(endpoint, params, base=base)) or [])
    for endpoint, params, base in [
        ("analyst-estimates", {"symbol": sym, "period": "quarter", "page": 0, "limit": 10}, "stable"),
        (f"analyst-estimates/{sym}", {"period": "quarter", "limit": 10}, "v3"),
    ]:
        ae_quarter_rows.extend(_records(_fmp_get(endpoint, params, base=base)) or [])
    ae = _select_forward_estimate_record(ae_annual_rows) or _select_forward_estimate_record(ae_quarter_rows)

    evrow = merge_one([("enterprise-values", {"symbol": sym, "limit": 1}, "stable"), (f"enterprise-values/{sym}", {"limit": 1}, "v3")])
    share_float_row = merge_one([("shares-float", {"symbol": sym}, "stable"), ("shares_float", {"symbol": sym}, "v4"), (f"shares_float/{sym}", {}, "v4")])
    short_row = merge_one([("short-interest", {"symbol": sym, "limit": 4}, "stable"), ("short_interest", {"symbol": sym, "limit": 1}, "v4"), (f"short_interest/{sym}", {"limit": 1}, "v4")])
    recrow = merge_one([("grades-consensus", {"symbol": sym}, "stable"), (f"analyst-stock-recommendations/{sym}", {"limit": 5}, "v3")])
    targetrow = merge_one([("price-target-consensus", {"symbol": sym}, "stable"), ("price-target-summary", {"symbol": sym}, "stable")])

    hi, lo = _parse_range_high_low(prof.get("range"))
    set_missing("regularMarketPrice", q.get("price"), prof.get("price"))
    info["currentPrice"] = info.get("currentPrice") or info.get("regularMarketPrice")
    set_missing("marketCap", q.get("marketCap"), q.get("marketCapitalization"), prof.get("mktCap"), prof.get("marketCap"))
    set_missing("volume", q.get("volume"), prof.get("volAvg"))
    set_missing("averageVolume", q.get("avgVolume"), q.get("avgVolume10D"), q.get("averageVolume"), prof.get("volAvg"))
    if info.get("averageVolume") in (None, "", 0, 0.0) and hist is not None and not getattr(hist, "empty", True) and "Volume" in hist.columns:
        try:
            av = pd.to_numeric(hist["Volume"], errors="coerce").dropna().tail(60).mean()
            if np.isfinite(av) and av > 0:
                info["averageVolume"] = float(av)
        except Exception:
            pass
    set_missing("beta", prof.get("beta"), q.get("beta"))
    set_missing("fiftyTwoWeekHigh", q.get("yearHigh"), q.get("fiftyTwoWeekHigh"), prof.get("fiftyTwoWeekHigh"), hi)
    set_missing("fiftyTwoWeekLow", q.get("yearLow"), q.get("fiftyTwoWeekLow"), prof.get("fiftyTwoWeekLow"), lo)
    set_missing("sharesOutstanding", q.get("sharesOutstanding"), prof.get("sharesOutstanding"))

    set_missing("trailingEps", q.get("eps"), inc.get("eps"), inc.get("epsTTM"), km.get("netIncomePerShareTTM"))
    set_missing("forwardEps", ae.get("estimatedEpsAvg"), ae.get("epsAvg"), ae.get("epsAverage"), ae.get("estimatedEpsHigh"), ae.get("estimatedEpsLow"))
    set_missing("trailingPE", q.get("pe"), q.get("peRatio"), prof.get("pe"), km.get("peRatioTTM"), rt.get("priceEarningsRatioTTM"))
    # Do not use trailing/TTM P/E as Forward P/E. If direct forward P/E is missing,
    # reconstruct it later from current price and forward EPS.
    set_missing("forwardPE", q.get("forwardPE"), q.get("forwardPe"))
    set_missing("pegRatio", km.get("pegRatioTTM"), rt.get("priceEarningsToGrowthRatioTTM"))
    set_missing("priceToSalesTrailing12Months", km.get("priceToSalesRatioTTM"), rt.get("priceToSalesRatioTTM"))
    set_missing("priceToBook", km.get("pbRatioTTM"), km.get("priceToBookRatioTTM"), rt.get("priceToBookRatioTTM"))
    set_missing("enterpriseToEbitda", km.get("evToEBITDATTM"), km.get("enterpriseValueOverEBITDATTM"), rt.get("enterpriseValueMultipleTTM"))
    set_missing("enterpriseToRevenue", km.get("evToSalesRatioTTM"))
    set_missing("totalRevenue", inc.get("revenue"), inc.get("revenueTTM"), km.get("revenueTTM"))
    set_missing("netIncomeToCommon", inc.get("netIncome"), inc.get("netIncomeTTM"))
    set_missing("ebitda", inc.get("ebitda"), inc.get("ebitdaTTM"), km.get("ebitdaTTM"))
    set_missing("grossMargins", rt.get("grossProfitMarginTTM"), km.get("grossProfitMarginTTM"), pctval=True)
    set_missing("operatingMargins", rt.get("operatingProfitMarginTTM"), km.get("operatingProfitMarginTTM"), pctval=True)
    set_missing("profitMargins", rt.get("netProfitMarginTTM"), km.get("netProfitMarginTTM"), pctval=True)
    set_missing("returnOnEquity", rt.get("returnOnEquityTTM"), km.get("roeTTM"), km.get("returnOnEquityTTM"), pctval=True)
    set_missing("returnOnAssets", rt.get("returnOnAssetsTTM"), km.get("roaTTM"), km.get("returnOnAssetsTTM"), pctval=True)
    set_missing("currentRatio", rt.get("currentRatioTTM"), km.get("currentRatioTTM"))
    set_missing("quickRatio", rt.get("quickRatioTTM"), km.get("quickRatioTTM"))
    set_missing("payoutRatio", rt.get("payoutRatioTTM"), km.get("payoutRatioTTM"), pctval=True)
    if info.get("payoutRatio") in (None, "", 0, 0.0):
        div_paid = n(cf.get("dividendsPaid"), cf.get("commonDividendsPaid"), cf.get("dividendsPaidTTM"), default=None)
        ni = n(info.get("netIncomeToCommon"), inc.get("netIncome"), inc.get("netIncomeTTM"), default=None)
        eps_for_payout = n(info.get("trailingEps"), q.get("eps"), inc.get("eps"), default=None)
        div_yield = pct(info.get("dividendYield"), rt.get("dividendYieldTTM"), km.get("dividendYieldTTM"))
        price_for_payout = n(info.get("regularMarketPrice"), q.get("price"), prof.get("price"), default=None)
        if div_paid is not None and ni not in (None, 0) and ni > 0:
            info["payoutRatio"] = abs(div_paid) / ni
        elif div_yield not in (None, 0) and price_for_payout not in (None, 0) and eps_for_payout not in (None, 0) and eps_for_payout > 0:
            info["payoutRatio"] = (div_yield * price_for_payout) / eps_for_payout
    de = n(rt.get("debtEquityRatioTTM"), rt.get("debtToEquityRatioTTM"), km.get("debtToEquityTTM"), default=None)
    if info.get("debtToEquity") in (None, "", 0, 0.0) and de is not None:
        info["debtToEquity"] = de * 100 if abs(de) < 20 else de
    std_repair = n(bal.get("shortTermDebt"), bal.get("shortTermBorrowings"), default=0) or 0
    ltd_repair = n(bal.get("longTermDebt"), bal.get("longTermDebtNoncurrent"), default=0) or 0
    set_missing("totalDebt", bal.get("totalDebt"), (std_repair + ltd_repair if (std_repair or ltd_repair) else None))
    set_missing("totalCash", bal.get("cashAndCashEquivalents"), bal.get("cashAndShortTermInvestments"))
    set_missing("enterpriseValue", evrow.get("enterpriseValue"), evrow.get("enterpriseValueTTM"), km.get("enterpriseValue"), km.get("enterpriseValueTTM"))
    # Reconstruct enterprise value and EV multiples if FMP's key-metrics endpoint omits them.
    mcap_for_ev = n(info.get("marketCap"), q.get("marketCap"), prof.get("mktCap"), default=None)
    debt_for_ev = n(info.get("totalDebt"), default=0) or 0
    cash_for_ev = n(info.get("totalCash"), default=0) or 0
    if info.get("enterpriseValue") in (None, "", 0, 0.0) and mcap_for_ev not in (None, 0):
        info["enterpriseValue"] = mcap_for_ev + debt_for_ev - cash_for_ev
    rev_for_ev = n(info.get("totalRevenue"), inc.get("revenue"), inc.get("revenueTTM"), km.get("revenueTTM"), default=None)
    ebitda_for_ev = n(info.get("ebitda"), inc.get("ebitda"), inc.get("ebitdaTTM"), km.get("ebitdaTTM"), default=None)
    if info.get("enterpriseToRevenue") in (None, "", 0, 0.0) and info.get("enterpriseValue") not in (None, 0) and rev_for_ev not in (None, 0):
        info["enterpriseToRevenue"] = info["enterpriseValue"] / rev_for_ev
    if info.get("enterpriseToEbitda") in (None, "", 0, 0.0) and info.get("enterpriseValue") not in (None, 0) and ebitda_for_ev not in (None, 0):
        info["enterpriseToEbitda"] = info["enterpriseValue"] / ebitda_for_ev
    set_missing("freeCashflow", cf.get("freeCashFlow"), cf.get("freeCashFlowTTM"), km.get("freeCashFlowTTM"))
    set_missing("operatingCashflow", cf.get("operatingCashFlow"), cf.get("netCashProvidedByOperatingActivities"))
    set_missing("revenueGrowth", gr.get("revenueGrowth"), gr.get("growthRevenue"), pctval=True)
    set_missing("earningsGrowth", gr.get("epsgrowth"), gr.get("epsGrowth"), gr.get("growthEPS"), pctval=True)

    equity = n(bal.get("totalStockholdersEquity"), bal.get("totalShareholdersEquity"), default=None)
    shares = n(info.get("sharesOutstanding"), q.get("sharesOutstanding"), prof.get("sharesOutstanding"), default=None)
    if info.get("bookValue") in (None, "", 0, 0.0):
        bvps = n(km.get("bookValuePerShareTTM"), default=None)
        if bvps is not None:
            info["bookValue"] = bvps
        elif equity is not None and shares not in (None, 0):
            info["bookValue"] = equity / shares

    # Float and short-interest fields are plan-dependent on FMP; use only source values, never fabricate.
    set_missing("floatShares", share_float_row.get("floatShares"), share_float_row.get("float"), share_float_row.get("freeFloatShares"), share_float_row.get("freeFloat"))
    short_pct = pct(short_row.get("shortPercentOfFloat"), short_row.get("shortFloatPercent"), short_row.get("shortPercent"), short_row.get("shortPercentFloat"))
    if info.get("shortPercentOfFloat") in (None, "", 0, 0.0):
        if short_pct is not None:
            info["shortPercentOfFloat"] = short_pct
        else:
            short_interest = n(short_row.get("shortInterest"), short_row.get("sharesShort"), default=None)
            flt = n(info.get("floatShares"), share_float_row.get("floatShares"), share_float_row.get("float"), default=None)
            if short_interest is not None and flt not in (None, 0):
                info["shortPercentOfFloat"] = short_interest / flt

    price = n(info.get("regularMarketPrice"), info.get("currentPrice"), default=None)
    eps = n(info.get("trailingEps"), default=None)
    mcap = n(info.get("marketCap"), default=None)
    rev = n(info.get("totalRevenue"), default=None)
    if info.get("sharesOutstanding") in (None, "", 0, 0.0) and mcap not in (None, 0) and price not in (None, 0):
        info["sharesOutstanding"] = mcap / price
    if info.get("trailingPE") in (None, "", 0, 0.0) and price not in (None, 0) and eps not in (None, 0):
        info["trailingPE"] = price / eps
    fwd_eps_for_pe = n(info.get("forwardEps"), default=None)
    if fwd_eps_for_pe is not None and fwd_eps_for_pe <= 0:
        info["forwardEps"] = None
        info["forwardPE"] = None
    elif info.get("forwardPE") in (None, "", 0, 0.0):
        if price not in (None, 0) and fwd_eps_for_pe not in (None, 0):
            info["forwardPE"] = price / fwd_eps_for_pe
    if n(info.get("forwardPE"), default=None) is not None and n(info.get("forwardPE"), default=None) <= 0:
        info["forwardPE"] = None
    if info.get("priceToSalesTrailing12Months") in (None, "", 0, 0.0) and mcap not in (None, 0) and rev not in (None, 0):
        info["priceToSalesTrailing12Months"] = mcap / rev
    if info.get("pegRatio") in (None, "", 0, 0.0):
        pe = n(info.get("trailingPE"), default=None)
        eg = n(info.get("earningsGrowth"), default=None)
        if pe is not None and eg not in (None, 0):
            info["pegRatio"] = pe / (eg * 100 if abs(eg) < 3 else eg)

    # Repair analyst targets/consensus with current FMP endpoints.
    set_missing("targetLowPrice", targetrow.get("targetLow"), targetrow.get("targetLowPrice"), targetrow.get("priceTargetLow"), targetrow.get("targetLowEstimate"))
    set_missing("targetMeanPrice", targetrow.get("targetConsensus"), targetrow.get("targetMeanPrice"), targetrow.get("priceTargetAverage"), targetrow.get("targetPrice"), targetrow.get("priceTargetConsensus"))
    set_missing("targetHighPrice", targetrow.get("targetHigh"), targetrow.get("targetHighPrice"), targetrow.get("priceTargetHigh"), targetrow.get("targetHighEstimate"))
    if info.get("numberOfAnalystOpinions") in (None, "", 0, 0.0):
        ac = n(targetrow.get("numberOfAnalysts"), targetrow.get("analystCount"), targetrow.get("priceTargetAnalystCount"), default=None)
        if ac not in (None, 0):
            info["numberOfAnalystOpinions"] = ac
    sb = n(recrow.get("strongBuy"), recrow.get("analystRatingsStrongBuy"), recrow.get("strong_buy"), default=0) or 0
    by = n(recrow.get("buy"), recrow.get("analystRatingsBuy"), recrow.get("analystRatingsbuy"), default=0) or 0
    hd = n(recrow.get("hold"), recrow.get("analystRatingsHold"), default=0) or 0
    sl = n(recrow.get("sell"), recrow.get("analystRatingsSell"), default=0) or 0
    ss = n(recrow.get("strongSell"), recrow.get("analystRatingsStrongSell"), recrow.get("strong_sell"), default=0) or 0
    total_rec = sb + by + hd + sl + ss
    if total_rec:
        rm = (1 * sb + 2 * by + 3 * hd + 4 * sl + 5 * ss) / total_rec
        info["recommendationMean"] = rm
        info["recommendationAnalystCount"] = total_rec
        info["numberOfAnalystOpinions"] = info.get("numberOfAnalystOpinions") or total_rec
        info["recommendationKey"] = "strong buy" if rm <= 1.5 else "buy" if rm <= 2.5 else "hold" if rm < 3.5 else "sell" if rm < 4.5 else "strong sell"
        info["recommendationSource"] = "FMP grades-consensus" if any(k in recrow for k in ("strongBuy", "strongSell")) else "FMP legacy analyst-stock-recommendations"
    return info


def _fmp_news_items(ticker="", limit=50):
    params = {"limit": int(limit)}
    if ticker:
        params["tickers"] = _fmp_symbol(ticker)
    data = _fmp_get("stock_news", params, base="v3")
    if not data:
        data = _fmp_get("news/stock", {"symbols": _fmp_symbol(ticker), "limit": int(limit)} if ticker else {"limit": int(limit)}, base="stable")
    rows = []
    for item in _records(data):
        rows.append({
            "ticker": ticker or clean_text(item.get("symbol") or item.get("symbols") or ""),
            "title": clean_text(item.get("title", "")),
            "summary": clean_text(item.get("text") or item.get("summary") or item.get("site") or ""),
            "publisher": clean_text(item.get("site") or item.get("publisher") or "FMP"),
            "link": clean_text(item.get("url") or item.get("link") or ""),
            "ts": _news_timestamp(item.get("publishedDate") or item.get("date")),
            "source_rank": 1,
        })
    return rows


class _FMPTicker:
    """Small yfinance-like wrapper backed entirely by FMP."""
    def __init__(self, symbol):
        self.symbol = str(symbol or "").upper().strip()

    @property
    def info(self):
        return self.get_info()

    def get_info(self):
        return _fmp_build_info(self.symbol) or {"symbol": self.symbol, "shortName": self.symbol, "longName": self.symbol}

    def history(self, period="1y", interval="1d", auto_adjust=True, prepost=False, **kwargs):
        del auto_adjust, prepost, kwargs
        interval_l = str(interval).lower()
        if interval_l in {"1d", "5d", "1wk", "1mo", "3mo"}:
            h = _fmp_build_hist(self.symbol, period=period)
            if interval_l == "1wk":
                return _resample_ohlcv(h, "W-FRI")
            if interval_l == "1mo":
                return _resample_ohlcv(h, "ME")
            if interval_l == "3mo":
                return _resample_ohlcv(h, "QE")
            return h
        return _fmp_build_intraday(self.symbol, period=period, interval=interval)

    @property
    def news(self):
        return _fmp_news_items(self.symbol, limit=50)



def _fetch_stock_uncached(ticker, period="2y"):
    try:
        if not _get_fmp_key():
            return None, "FMP_API_KEY is missing. Add it to Streamlit Secrets, then reboot the app."

        hist = _fmp_build_hist(ticker, period)
        if hist.empty:
            last_err = ""
            try:
                last_err = st.session_state.get("_last_fmp_error", "")
            except Exception:
                pass
            detail = f" Last FMP message: {last_err}" if last_err else ""
            return None, f"No FMP price history returned for '{ticker}'. Check your FMP key/plan or endpoint access.{detail}"

        info = _fmp_build_info(ticker)
        if not info:
            info = {"symbol": _fmp_symbol(ticker), "shortName": _fmp_symbol(ticker), "longName": _fmp_symbol(ticker)}
        info = _fmp_repair_ui_fields(info, ticker, hist)
        return {"info": info, "hist": hist}, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock(ticker, period="2y"):
    try:
        return _fetch_stock_uncached(ticker, period)
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_chart_history(ticker, period="1y", interval="1d", prepost=False):
    del prepost
    try:
        interval_l = str(interval).lower()
        h = _fmp_build_hist(ticker, period) if interval_l in ("1d", "5d", "1wk", "1mo", "3mo") else _fmp_build_intraday(ticker, period=period, interval=interval)
        if h is not None and not h.empty:
            if interval_l == "1wk":
                h = _resample_ohlcv(h, "W-FRI")
            elif interval_l == "1mo":
                h = _resample_ohlcv(h, "ME")
            elif interval_l == "3mo":
                h = _resample_ohlcv(h, "QE")
            return h, None
    except Exception as e:
        return None, str(e)
    return None, "No FMP chart history returned. Check your FMP plan, ticker, or interval."
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_peers(tickers: tuple, period="1y"):
    def _one(t):
        try:
            s = _fmp_ticker(t)
            h = s.history(period=period, auto_adjust=True)
            if h is not None and not h.empty:
                return t, {"info": s.info, "hist": h}
        except Exception:
            pass
        return t, None

    out = {}
    with ThreadPoolExecutor(max_workers=min(len(tickers), 6)) as ex:
        for t, result in ex.map(_one, tickers):
            if result is not None:
                out[t] = result
    return out

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_peers(tickers: tuple, period="1y"):
    out = {}
    for t in tickers:
        try:
            s = _fmp_ticker(t)
            h = s.history(period=period, auto_adjust=True)
            if not h.empty:
                out[t] = {"info": s.info, "hist": h}
        except Exception:
            pass
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_spy(period="2y"):
    return _fmp_ticker("SPY").history(period=period, auto_adjust=True)


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies_by_keyword(keyword, max_results=12):
    keyword = clean_text(keyword or "").strip() if "clean_text" in globals() else str(keyword or "").strip()
    if len(keyword) < 2:
        return []
    rows = []
    try:
        data = _fmp_get("search", {"query": keyword, "limit": max_results * 3}, base="v3")
        if not data:
            data = _fmp_get("search-symbol", {"query": keyword, "limit": max_results * 3}, base="stable")
        for q in _records(data):
            symbol = str(q.get("symbol") or "").upper().strip()
            if not symbol or symbol.startswith("^"):
                continue
            name = _text(q.get("name"), q.get("companyName"), symbol)
            exch = _text(q.get("exchangeShortName"), q.get("stockExchange"), q.get("exchange"), default="FMP")
            # Keep company search lightweight: do not call the full fundamentals
            # builder for every keystroke/result. The selected ticker is fetched
            # fully only after the user clicks "Use selected company".
            rows.append({
                "Ticker": symbol,
                "Company": name,
                "Exchange": exch,
                "Market Cap": safe_float(q.get("marketCap") or q.get("mktCap") or 0, 0) if "safe_float" in globals() else _num(q.get("marketCap"), q.get("mktCap"), default=0),
                "Quote Type": "EQUITY",
            })
    except Exception:
        pass

    by_symbol = {}
    for row in rows:
        sym = row["Ticker"]
        if sym not in by_symbol or row.get("Market Cap", 0) > by_symbol[sym].get("Market Cap", 0):
            by_symbol[sym] = row
    rows = sorted(by_symbol.values(), key=lambda x: (safe_float(x.get("Market Cap", 0), 0), x.get("Company", "")), reverse=True)
    return rows[:max_results]
def _format_market_cap_short(value):
    value = safe_float(value, 0)
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    if value >= 1e9:
        return f"${value/1e9:.1f}B"
    if value >= 1e6:
        return f"${value/1e6:.0f}M"
    return "Mkt cap n/a"


def _company_search_label(row):
    cap = _format_market_cap_short(row.get("Market Cap"))
    exch = row.get("Exchange") or "FMP"
    return f"{row.get('Ticker','')} · {row.get('Company','')} · {exch} · {cap}"


def _finite(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else np.nan
    except Exception:
        return np.nan


def _score_color_label(score):
    if score >= 80:
        return "Strongly Bullish", GREEN
    if score >= 62:
        return "Bullish", GREEN
    if score >= 48:
        return "Neutral / Mixed", AMBER
    if score >= 32:
        return "Bearish", RED
    return "Strongly Bearish", RED


def technical_signal_model(df, fallback_price=None):
    """Weighted technical signal model.

    The old version counted green icons equally. This version weights trend,
    momentum, overextension, trend strength, and volume confirmation. Scores are
    normalized only across indicators that have enough valid data, so a short
    chart window does not create false bullish/bearish readings.
    """
    if df is None or df.empty:
        return {"score": 50.0, "label": "Neutral / Mixed", "color": AMBER, "components": [], "usable_weight": 0.0}

    clean = df.copy()
    last = clean.iloc[-1]
    close = pd.to_numeric(clean.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    price = _finite(close.iloc[-1]) if len(close) else _finite(fallback_price)

    components = []

    def add(name, weight, value, detail, bullish=True):
        if value is None or not np.isfinite(value):
            return
        value = max(0.0, min(1.0, float(value)))
        emoji = "🟢" if value >= 0.67 else "🟡" if value >= 0.34 else "🔴"
        components.append({"name": name, "weight": float(weight), "value": value, "emoji": emoji, "detail": detail})

    def val(col):
        return _finite(last.get(col))

    ma20, ma50, ma200 = val("MA20"), val("MA50"), val("MA200")
    ma5, ma10 = val("MA5"), val("MA10")
    rsi, adx, macd, macd_sig, macd_h = val("RSI"), val("ADX"), val("MACD"), val("MACD_SIG"), val("MACD_H")
    stoch_k, stoch_d = val("STOCH_K"), val("STOCH_D")
    bb_p = val("BB_P")

    def price_vs_ma_score(ma):
        if not np.isfinite(price) or not np.isfinite(ma) or ma == 0:
            return np.nan, "insufficient data"
        dist = (price / ma - 1) * 100
        if dist >= 3:
            sc = 1.0
        elif dist >= 0:
            sc = 0.78
        elif dist >= -2:
            sc = 0.42
        else:
            sc = 0.12
        return sc, f"Price {dist:+.1f}% vs MA"

    for ma_name, ma_val, wt in [("Price vs MA20", ma20, 12), ("Price vs MA50", ma50, 12), ("Price vs MA200", ma200, 14)]:
        sc, detail = price_vs_ma_score(ma_val)
        add(ma_name, wt, sc, detail)

    if np.isfinite(ma50) and np.isfinite(ma200) and ma200 != 0:
        spread = (ma50 / ma200 - 1) * 100
        sc = 1.0 if spread >= 2 else 0.75 if spread >= 0 else 0.25 if spread > -2 else 0.0
        add("MA50 vs MA200", 9, sc, f"MA50 is {spread:+.1f}% vs MA200")

    try:
        ma20_clean = pd.to_numeric(clean["MA20"], errors="coerce").dropna()
        if len(ma20_clean) >= 11 and ma20_clean.iloc[-11] != 0:
            slope = (ma20_clean.iloc[-1] / ma20_clean.iloc[-11] - 1) * 100
            sc = 1.0 if slope > 1.0 else 0.70 if slope > 0 else 0.30 if slope > -1.0 else 0.05
            add("MA20 Slope", 7, sc, f"20-day average changed {slope:+.1f}% over ~10 bars")
    except Exception:
        pass

    if np.isfinite(macd) and np.isfinite(macd_sig):
        diff = macd - macd_sig
        hist_change = np.nan
        try:
            mh = pd.to_numeric(clean["MACD_H"], errors="coerce").dropna()
            if len(mh) >= 2:
                hist_change = mh.iloc[-1] - mh.iloc[-2]
        except Exception:
            pass
        sc = 0.95 if diff > 0 and (not np.isfinite(hist_change) or hist_change >= 0) else 0.75 if diff > 0 else 0.35 if np.isfinite(hist_change) and hist_change > 0 else 0.08
        add("MACD Momentum", 14, sc, f"MACD {'above' if diff > 0 else 'below'} signal; histogram {'improving' if np.isfinite(hist_change) and hist_change > 0 else 'not improving'}")

    if np.isfinite(rsi):
        # RSI is not automatically bullish when oversold; oversold is a bounce setup but weak trend confirmation.
        if 50 <= rsi <= 65:
            sc, note = 1.0, "healthy bullish momentum"
        elif 45 <= rsi < 50 or 65 < rsi <= 70:
            sc, note = 0.72, "constructive but not ideal"
        elif 35 <= rsi < 45 or 70 < rsi <= 78:
            sc, note = 0.42, "mixed / stretched"
        else:
            sc, note = 0.18, "extreme oversold or overbought"
        add("RSI Regime", 10, sc, f"RSI {rsi:.1f} — {note}")

    if np.isfinite(stoch_k):
        if 20 <= stoch_k <= 80:
            sc = 0.60
        elif stoch_k < 20:
            sc = 0.35
        else:
            sc = 0.30
        if np.isfinite(stoch_d):
            sc += 0.20 if stoch_k > stoch_d else -0.10
        add("Stochastic", 6, sc, f"%K {stoch_k:.1f}" + (f" vs %D {stoch_d:.1f}" if np.isfinite(stoch_d) else ""))

    if np.isfinite(adx):
        bullish_trend = (np.isfinite(ma20) and np.isfinite(ma50) and price > ma20 >= ma50) or (np.isfinite(ma50) and price > ma50)
        bearish_trend = (np.isfinite(ma20) and np.isfinite(ma50) and price < ma20 <= ma50) or (np.isfinite(ma50) and price < ma50)
        if adx >= 25 and bullish_trend:
            sc, note = 1.0, "strong trend confirms bullish direction"
        elif adx >= 25 and bearish_trend:
            sc, note = 0.05, "strong trend confirms bearish direction"
        elif adx >= 20:
            sc, note = 0.50, "trend exists but direction is mixed"
        else:
            sc, note = 0.45, "weak/ranging trend"
        add("ADX Trend Strength", 8, sc, f"ADX {adx:.1f} — {note}")

    try:
        vol = pd.to_numeric(clean["Volume"], errors="coerce")
        vol_ma = pd.to_numeric(clean["VOL_MA"], errors="coerce")
        ret = pd.to_numeric(clean["RET"], errors="coerce")
        if np.isfinite(vol.iloc[-1]) and np.isfinite(vol_ma.iloc[-1]) and vol_ma.iloc[-1] > 0 and np.isfinite(ret.iloc[-1]):
            vr = vol.iloc[-1] / vol_ma.iloc[-1]
            if vr >= 1.15 and ret.iloc[-1] > 0:
                sc, note = 1.0, "up move confirmed by above-average volume"
            elif vr >= 1.15 and ret.iloc[-1] < 0:
                sc, note = 0.05, "selling pressure on above-average volume"
            else:
                sc, note = 0.50, "no strong volume confirmation"
            add("Volume Confirmation", 5, sc, f"Volume {vr:.2f}× 20-day average — {note}")
    except Exception:
        pass

    if np.isfinite(bb_p):
        if 0.20 <= bb_p <= 0.80:
            sc, note = 0.62, "inside normal Bollinger range"
        elif bb_p > 0.80:
            sc, note = 0.55, "near upper band; trend can continue but risk is stretched"
        else:
            sc, note = 0.32, "near lower band; weak unless reversal confirms"
        add("Bollinger Position", 3, sc, f"%B {bb_p:.2f} — {note}")

    total_w = sum(c["weight"] for c in components)
    score = sum(c["weight"] * c["value"] for c in components) / total_w * 100 if total_w else 50.0
    label, color = _score_color_label(score)
    return {"score": round(score, 1), "label": label, "color": color, "components": components, "usable_weight": total_w}


# ══════════════════════════════════════════════════════════════════
#  TECHNICALS
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def calc_ta(df):
    """Calculate indicators safely, even on short daily/intraday windows."""
    df = df.copy()
    if df is None or df.empty:
        return df

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    nrows = len(df)

    def blank(name):
        df[name] = np.nan

    def try_set(name, func, min_rows=1):
        try:
            if nrows >= min_rows and c.notna().sum() >= min_rows:
                df[name] = func()
            else:
                blank(name)
        except Exception:
            blank(name)

    for n in [5, 10, 20, 50, 120, 200]:
        df[f"MA{n}"] = c.rolling(n, min_periods=n).mean()

    try:
        if nrows >= 20:
            bb = ta.volatility.BollingerBands(c, window=20, window_dev=2)
            df["BB_U"] = bb.bollinger_hband()
            df["BB_L"] = bb.bollinger_lband()
            df["BB_M"] = bb.bollinger_mavg()
            df["BB_P"] = bb.bollinger_pband()
        else:
            for col in ["BB_U", "BB_L", "BB_M", "BB_P"]:
                blank(col)
    except Exception:
        for col in ["BB_U", "BB_L", "BB_M", "BB_P"]:
            blank(col)

    try_set("RSI", lambda: ta.momentum.rsi(c, window=14), min_rows=15)
    df["RSI_MA"] = df["RSI"].rolling(9, min_periods=9).mean() if "RSI" in df else np.nan

    try:
        if nrows >= 26:
            macd = ta.trend.MACD(c)
            df["MACD"] = macd.macd()
            df["MACD_SIG"] = macd.macd_signal()
            df["MACD_H"] = macd.macd_diff()
        else:
            for col in ["MACD", "MACD_SIG", "MACD_H"]:
                blank(col)
    except Exception:
        for col in ["MACD", "MACD_SIG", "MACD_H"]:
            blank(col)

    # ADX can crash on short windows. It needs more than one full 14-period window.
    try:
        if nrows >= 28:
            adx = ta.trend.ADXIndicator(h, l, c, window=14)
            df["ADX"] = adx.adx()
        else:
            blank("ADX")
    except Exception:
        blank("ADX")

    try:
        if nrows >= 17:
            sto = ta.momentum.StochasticOscillator(h, l, c, window=14, smooth_window=3)
            df["STOCH_K"] = sto.stoch()
            df["STOCH_D"] = sto.stoch_signal()
        else:
            blank("STOCH_K"); blank("STOCH_D")
    except Exception:
        blank("STOCH_K"); blank("STOCH_D")

    try_set("ATR", lambda: ta.volatility.average_true_range(h, l, c, window=14), min_rows=15)
    try_set("OBV", lambda: ta.volume.on_balance_volume(c, v), min_rows=2)
    df["VOL_MA"] = v.rolling(20, min_periods=20).mean()
    try_set("WILLR", lambda: ta.momentum.williams_r(h, l, c, lbp=14), min_rows=15)
    try_set("CCI", lambda: ta.trend.cci(h, l, c, window=20), min_rows=20)

    df["RET"] = c.pct_change()
    df["RVOL20"] = df["RET"].rolling(20, min_periods=20).std() * np.sqrt(252) * 100
    df["RVOL60"] = df["RET"].rolling(60, min_periods=60).std() * np.sqrt(252) * 100
    return df
def find_sr(df, window=15, n=3):
    if df is None or df.empty or "Close" not in df.columns:
        return [], []
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(close) < max(3, window * 2 + 1):
        return [], []
    c = close.values
    highs, lows = [], []
    for i in range(window, len(c) - window):
        seg = c[i-window:i+window+1]
        if len(seg) and c[i] == np.nanmax(seg):
            highs.append(float(c[i]))
        if len(seg) and c[i] == np.nanmin(seg):
            lows.append(float(c[i]))
    def cluster(pts, tol=0.01):
        pts = [p for p in pts if np.isfinite(p) and p > 0]
        if not pts:
            return []
        pts = sorted(set(pts))
        out = [pts[0]]
        for p in pts[1:]:
            base = out[-1]
            if base <= 0 or (p - base) / base > tol:
                out.append(p)
        return out
    cur = float(c[-1])
    return (sorted([x for x in cluster(lows)  if x < cur], reverse=True)[:n],
            sorted([x for x in cluster(highs) if x > cur])[:n])


# ══════════════════════════════════════════════════════════════════
#  RISK
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=1800, show_spinner=False)
def calc_risk(hist, spy):
    """Risk metrics using date-aligned daily returns.

    Notes:
    - Uses adjusted close from FMP histories.
    - Aligns stock and SPY returns by timestamp before beta/alpha/R² calculations.
    - Annualization uses 252 trading days, which is standard for U.S. equities.
    """
    def _empty_series():
        return pd.Series(dtype=float)

    if hist is None or hist.empty or "Close" not in hist.columns:
        ret_s = _empty_series()
        return dict(beta=0, alpha=0, vol=0, ret1y=0, sharpe=0, sortino=0, calmar=0,
                    max_dd=0, var95=0, cvar95=0, win=0, r2=0, te=0, ir=0,
                    ret_s=ret_s, cum_s=ret_s, dd_s=ret_s, roll_sh=ret_s)

    ret_s = pd.to_numeric(hist["Close"], errors="coerce").pct_change().dropna()
    if ret_s.empty:
        return dict(beta=0, alpha=0, vol=0, ret1y=0, sharpe=0, sortino=0, calmar=0,
                    max_dd=0, var95=0, cvar95=0, win=0, r2=0, te=0, ir=0,
                    ret_s=ret_s, cum_s=ret_s, dd_s=ret_s, roll_sh=ret_s)

    bret_s = pd.to_numeric(spy["Close"], errors="coerce").pct_change().dropna() if spy is not None and not spy.empty and "Close" in spy.columns else pd.Series(dtype=float)

    # Normalize timezone for exact daily alignment.
    if isinstance(ret_s.index, pd.DatetimeIndex):
        ret_s.index = ret_s.index.tz_localize(None) if ret_s.index.tz is not None else ret_s.index
    if isinstance(bret_s.index, pd.DatetimeIndex):
        bret_s.index = bret_s.index.tz_localize(None) if bret_s.index.tz is not None else bret_s.index

    aligned = pd.concat([ret_s.rename("stock"), bret_s.rename("spy")], axis=1).dropna()
    if len(aligned) >= 2:
        r = aligned["stock"].to_numpy(dtype=float)
        b = aligned["spy"].to_numpy(dtype=float)
    else:
        r = ret_s.to_numpy(dtype=float)
        b = np.zeros_like(r)

    rf = float(RISK_FREE_ANNUAL_RATE) / 252
    std_r = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
    std_b = float(np.std(b, ddof=1)) if len(b) > 1 else 0.0
    beta = float(np.cov(r, b, ddof=1)[0, 1] / np.var(b, ddof=1)) if len(r) > 2 and np.var(b, ddof=1) else 0.0
    mu_r = float(np.mean(r)) * 252 if len(r) else 0.0
    mu_b = float(np.mean(b)) * 252 if len(b) else 0.0
    # Use realized trailing return for the "1yr Return" metric, not annualized mean daily return.
    close_px = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    if len(close_px) >= 253 and close_px.iloc[-253] != 0:
        ret1y_realized = (close_px.iloc[-1] / close_px.iloc[-253] - 1) * 100
    elif len(close_px) >= 2 and close_px.iloc[0] != 0:
        ret1y_realized = (close_px.iloc[-1] / close_px.iloc[0] - 1) * 100
    else:
        ret1y_realized = 0.0
    alpha = mu_r - (rf * 252 + beta * (mu_b - rf * 252))
    vol = std_r * np.sqrt(252) * 100
    sharpe = float(np.mean(r - rf) / std_r * np.sqrt(252)) if std_r else 0.0
    downside = r[r < rf]
    down_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 0.0
    sortino = float((np.mean(r) - rf) / down_std * np.sqrt(252)) if down_std else 0.0
    cum = np.cumprod(1 + r)
    running_max = np.maximum.accumulate(cum) if len(cum) else np.array([1.0])
    dd_a = (cum - running_max) / running_max if len(cum) else np.array([0.0])
    max_dd = float(np.min(dd_a)) * 100 if len(dd_a) else 0.0
    var95 = float(np.percentile(r, 5)) * 100 if len(r) else 0.0
    cutoff = np.percentile(r, 5) if len(r) else 0.0
    cvar95 = float(np.mean(r[r <= cutoff])) * 100 if len(r[r <= cutoff]) else 0.0
    calmar = (mu_r * 100) / abs(max_dd) if max_dd else 0.0
    win = float((r > 0).mean() * 100) if len(r) else 0.0
    corr = float(np.corrcoef(r, b)[0, 1]) if len(r) > 2 and std_r and std_b else 0.0
    r2 = corr ** 2
    active = r - b if len(r) == len(b) else r
    te = float(np.std(active, ddof=1)) * np.sqrt(252) * 100 if len(active) > 1 else 0.0
    ir = (mu_r - mu_b) / (te / 100) if te else 0.0
    cum_s = (1 + ret_s).cumprod()
    rmx_s = cum_s.expanding().max()
    dd_s = (cum_s - rmx_s) / rmx_s * 100
    roll_sh = (ret_s.rolling(60, min_periods=30).mean() / ret_s.rolling(60, min_periods=30).std()) * np.sqrt(252)
    return dict(
        beta=round(beta, 3), alpha=round(alpha * 100, 3), vol=round(vol, 2),
        ret1y=round(ret1y_realized, 2), sharpe=round(sharpe, 3), sortino=round(sortino, 3),
        calmar=round(calmar, 3), max_dd=round(max_dd, 2), var95=round(var95, 2),
        cvar95=round(cvar95, 2), win=round(win, 1), r2=round(r2, 3),
        te=round(te, 2), ir=round(ir, 3),
        ret_s=ret_s, cum_s=cum_s, dd_s=dd_s, roll_sh=roll_sh,
    )


# ══════════════════════════════════════════════════════════════════
#  DCF
# ══════════════════════════════════════════════════════════════════
def dcf_value(fcf, g, tg, wacc, yrs=10):
    if fcf<=0 or wacc <= tg: return 0.0
    pv=0.0
    for yr in range(1,yrs+1):
        fcf*=(1+g/100); pv+=fcf/(1+wacc/100)**yr
    tv=fcf*(1+tg/100)/(wacc/100-tg/100)
    return pv+tv/(1+wacc/100)**yrs


# ══════════════════════════════════════════════════════════════════
#  BUILT-IN AI-STYLE THESIS ENGINE — no external API key required
# ══════════════════════════════════════════════════════════════════
def safe_float(v, default=0.0):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(round(v))))

AI_RISK_MODELS = {
    "Risk Lover / Growth Momentum": "risk_loving",
    "Risk Neutral / Balanced": "risk_neutral",
    "Safe / Quality Defensive": "safe",
}
AI_RISK_MODEL_NAMES = {v: k for k, v in AI_RISK_MODELS.items()}

def get_ai_risk_model():
    return st.session_state.get("ai_risk_model", "risk_loving")

def set_ai_risk_model(value):
    if value in AI_RISK_MODEL_NAMES:
        st.session_state["ai_risk_model"] = value
    elif value in AI_RISK_MODELS:
        st.session_state["ai_risk_model"] = AI_RISK_MODELS[value]
    else:
        st.session_state["ai_risk_model"] = "risk_loving"

def _sync_ai_model_from_widget(widget_key):
    """Keep every AI-model selector tied to one shared session-state value."""
    chosen = st.session_state.get(widget_key, "Risk Lover / Growth Momentum")
    set_ai_risk_model(chosen)


def render_ai_model_selector(label="AI scoring model", key="ai_model_selector"):
    """Render a smooth shared model selector.

    Streamlit still reruns after a widget click, but this selector no longer clears
    cached market/price data. Switching models only recomputes the lightweight
    score/thesis layer, so the AI Thesis page feels much smoother.
    """
    labels = list(AI_RISK_MODELS.keys())
    current = get_ai_risk_model()
    current_label = AI_RISK_MODEL_NAMES.get(current, "Risk Lover / Growth Momentum")

    # Keep every visible selector synchronized with the same shared model.
    st.session_state[key] = current_label

    try:
        chosen = st.segmented_control(
            label or "AI scoring model",
            labels,
            key=key,
            label_visibility="collapsed" if not label else "visible",
            on_change=_sync_ai_model_from_widget,
            args=(key,),
        )
    except Exception:
        chosen = st.radio(
            label or "AI scoring model",
            labels,
            key=key,
            horizontal=True,
            label_visibility="collapsed" if not label else "visible",
            on_change=_sync_ai_model_from_widget,
            args=(key,),
        )

    set_ai_risk_model(chosen)
    return get_ai_risk_model()

def ai_model_description(model=None):
    model = model or get_ai_risk_model()
    if model == "safe":
        return "Safe model: quality, valuation, and downside protection have the highest weight; growth still matters, but risky momentum is penalized harder."
    if model == "risk_neutral":
        return "Risk-neutral model: balanced weight across growth, momentum, quality, valuation, and safety."
    return "Risk-lover model: growth and momentum dominate; quality and valuation are secondary filters; safety mainly blocks extreme downside risk."

def score_from_metrics(info, risk, hist_ta=None, model=None):
    """Growth/momentum-first scoring model for a higher-risk investor.

    Priority order:
    1) Growth and momentum: strongest drivers of the total score.
    2) Quality and valuation: still required so weak/speculative names do not pass easily.
    3) Safety/downside risk: lower weight, but extreme drawdown/volatility can still block a Buy.

    This is not financial advice; it is a rules-based dashboard model.
    """
    model = model or get_ai_risk_model()
    if model not in {"risk_loving", "risk_neutral", "safe"}:
        model = "risk_loving"
    pe = safe_float(info.get("trailingPE"), 0)
    fpe = safe_float(info.get("forwardPE"), pe)
    ps = safe_float(info.get("priceToSalesTrailing12Months"), 0)
    peg = safe_float(info.get("pegRatio"), 0)
    rev_g = safe_float(info.get("revenueGrowth"), 0) * 100
    earn_g = safe_float(info.get("earningsGrowth"), 0) * 100
    margin = safe_float(info.get("profitMargins"), 0) * 100
    op_margin = safe_float(info.get("operatingMargins"), 0) * 100
    gross_margin = safe_float(info.get("grossMargins"), 0) * 100
    roe = safe_float(info.get("returnOnEquity"), 0) * 100
    roa = safe_float(info.get("returnOnAssets"), 0) * 100
    debt_eq = safe_float(info.get("debtToEquity"), 0) / 100
    current_ratio = safe_float(info.get("currentRatio"), 0)
    beta = safe_float(risk.get("beta"), 1)
    sharpe = safe_float(risk.get("sharpe"), 0)
    sortino = safe_float(risk.get("sortino"), 0)
    vol = safe_float(risk.get("vol"), 30)
    max_dd = abs(safe_float(risk.get("max_dd"), 25))
    var95 = abs(safe_float(risk.get("var95"), 2.5))
    cvar95 = abs(safe_float(risk.get("cvar95"), 4.0))
    win = safe_float(risk.get("win"), 50)

    # Valuation is more tolerant for high-growth stocks, but not ignored.
    valuation = 48
    if pe > 0:
        valuation += 15 if pe < 18 else 9 if pe < 28 else 2 if pe < 45 else -7 if pe < 70 else -16
    else:
        valuation -= 4
    if fpe > 0 and pe > 0:
        valuation += 9 if fpe < pe * 0.80 else 5 if fpe < pe else -3 if fpe > pe * 1.25 else 0
    if ps > 0:
        valuation += 9 if ps < 4 else 3 if ps < 10 else -5 if ps < 18 else -12
    if peg > 0:
        valuation += 12 if peg < 1.3 else 5 if peg < 2.2 else -6 if peg > 3.5 else 0
    if rev_g > 25 and margin > 8:
        valuation += 8
    elif rev_g > 15:
        valuation += 4

    # Quality is second-tier priority, but negative margins/debt still matter.
    quality = 42
    quality += min(max(margin, -12), 32) * 0.62
    quality += min(max(op_margin, -12), 35) * 0.28
    quality += min(max(gross_margin, 0), 75) * 0.10
    quality += min(max(roe, 0), 40) * 0.28
    quality += min(max(roa, 0), 20) * 0.32
    quality += 5 if debt_eq and debt_eq < 0.8 else 1 if debt_eq < 1.8 else -7 if debt_eq > 3.0 else 0
    quality += 3 if current_ratio >= 1.3 else -3 if current_ratio and current_ratio < 0.9 else 0
    if margin < 0 and rev_g < 10:
        quality -= 8

    # Growth is the largest score block.
    growth = 45 + min(max(rev_g, -30), 60) * 0.95
    if earn_g:
        growth += min(max(earn_g, -40), 80) * 0.18
    if rev_g > 20 and margin > 10:
        growth += 7
    if rev_g > 35:
        growth += 6
    if rev_g < 0:
        growth -= 10

    # Momentum is heavily rewarded for your higher-risk/growth style.
    momentum = 45
    if hist_ta is not None and len(hist_ta) > 30:
        last = hist_ta.iloc[-1]
        price = safe_float(last.get("Close"), 0)
        ma5 = safe_float(last.get("MA5"), 0)
        ma20 = safe_float(last.get("MA20"), 0)
        ma50 = safe_float(last.get("MA50"), 0)
        ma120 = safe_float(last.get("MA120"), 0)
        rsi = safe_float(last.get("RSI"), 50)
        ret_20 = 0
        ret_60 = 0
        try:
            closes = hist_ta["Close"].dropna()
            if len(closes) > 21:
                ret_20 = (closes.iloc[-1] / closes.iloc[-21] - 1) * 100
            if len(closes) > 61:
                ret_60 = (closes.iloc[-1] / closes.iloc[-61] - 1) * 100
        except Exception:
            pass
        momentum += 7 if ma5 and price > ma5 else -3 if ma5 else 0
        momentum += 10 if ma20 and price > ma20 else -5 if ma20 else 0
        momentum += 9 if ma50 and price > ma50 else -6 if ma50 else 0
        momentum += 6 if ma120 and price > ma120 else -4 if ma120 else 0
        momentum += min(max(ret_20, -15), 25) * 0.35
        momentum += min(max(ret_60, -25), 45) * 0.22
        momentum += 7 if 50 <= rsi <= 72 else 2 if 40 <= rsi < 50 else -7 if rsi > 82 else -5 if rsi < 35 else 0

    # Risk score still blocks extreme cases, but is intentionally lower weight.
    risk_score = 42
    risk_score += max(beta - 1.2, 0) * 7
    risk_score += max(vol - 35, 0) * 0.45
    risk_score += max(max_dd - 30, 0) * 0.45
    risk_score += max(var95 - 3.2, 0) * 2.8
    risk_score += max(cvar95 - 5.0, 0) * 1.8
    risk_score -= max(sharpe, 0) * 5
    risk_score -= max(sortino, 0) * 3
    risk_score -= max(win - 50, 0) * 0.12
    safety = 100 - risk_score

    # Build the component score dictionary BEFORE any weighted model calculation.
    # This fixes the NameError from using scores inside _weighted_score before scores existed.
    scores = {
        "valuation_score": clamp(valuation),
        "quality_score": clamp(quality),
        "growth_score": clamp(growth),
        "momentum_score": clamp(momentum),
        "risk_score": clamp(risk_score),
        "safety_score": clamp(safety),
    }

    # Model-specific weights and gates.
    # Risk-lover: growth/momentum first. Risk-neutral: balanced. Safe: quality and downside protection first.
    def _weighted_score(w):
        return clamp(
            w["growth"] * scores["growth_score"]
            + w["momentum"] * scores["momentum_score"]
            + w["quality"] * scores["quality_score"]
            + w["valuation"] * scores["valuation_score"]
            + w["safety"] * scores["safety_score"]
        )

    if model == "safe":
        weights = {"growth": 0.16, "momentum": 0.12, "quality": 0.26, "valuation": 0.20, "safety": 0.26}
        scores["overall_score"] = _weighted_score(weights)
        buy_gate = (scores["overall_score"] >= 72 and scores["quality_score"] >= 62 and scores["valuation_score"] >= 50 and scores["growth_score"] >= 45 and scores["risk_score"] <= 58 and max_dd <= 38 and vol <= 55 and var95 <= 4.2 and (sharpe >= 0.25 or sortino >= 0.35))
        strong_buy_gate = (scores["overall_score"] >= 82 and scores["quality_score"] >= 72 and scores["valuation_score"] >= 58 and scores["risk_score"] <= 48 and max_dd <= 30 and vol <= 45 and (sharpe >= 0.55 or sortino >= 0.70))
        sell_gate = (scores["overall_score"] < 42 or scores["quality_score"] < 32 or scores["risk_score"] > 82 or max_dd > 65)
    elif model == "risk_neutral":
        weights = {"growth": 0.24, "momentum": 0.20, "quality": 0.22, "valuation": 0.18, "safety": 0.16}
        scores["overall_score"] = _weighted_score(weights)
        buy_gate = (scores["overall_score"] >= 70 and scores["growth_score"] >= 52 and scores["momentum_score"] >= 50 and scores["quality_score"] >= 50 and scores["valuation_score"] >= 42 and scores["risk_score"] <= 70 and max_dd <= 50 and vol <= 75 and (sharpe >= 0.05 or sortino >= 0.15))
        strong_buy_gate = (scores["overall_score"] >= 80 and scores["growth_score"] >= 62 and scores["momentum_score"] >= 58 and scores["quality_score"] >= 60 and scores["valuation_score"] >= 48 and scores["risk_score"] <= 60 and max_dd <= 42 and (sharpe >= 0.35 or sortino >= 0.45))
        sell_gate = (scores["overall_score"] < 40 or (scores["growth_score"] < 35 and scores["momentum_score"] < 35) or (scores["quality_score"] < 30 and scores["valuation_score"] < 32) or scores["risk_score"] > 88)
    else:
        weights = {"growth": 0.32, "momentum": 0.28, "quality": 0.18, "valuation": 0.14, "safety": 0.08}
        scores["overall_score"] = _weighted_score(weights)
        buy_gate = (scores["overall_score"] >= 70 and scores["growth_score"] >= 58 and scores["momentum_score"] >= 58 and scores["quality_score"] >= 43 and scores["valuation_score"] >= 35 and scores["risk_score"] <= 82 and max_dd <= 60 and vol <= 95 and (sharpe >= -0.10 or sortino >= -0.10))
        strong_buy_gate = (scores["overall_score"] >= 80 and scores["growth_score"] >= 68 and scores["momentum_score"] >= 66 and scores["quality_score"] >= 52 and scores["valuation_score"] >= 40 and scores["risk_score"] <= 72 and max_dd <= 50 and (sharpe >= 0.20 or sortino >= 0.30))
        sell_gate = (scores["overall_score"] < 38 or (scores["growth_score"] < 35 and scores["momentum_score"] < 38) or (scores["quality_score"] < 28 and scores["valuation_score"] < 30) or (scores["risk_score"] > 92 and scores["momentum_score"] < 50))

    scores["model"] = model
    scores["model_name"] = AI_RISK_MODEL_NAMES.get(model, "Risk Lover / Growth Momentum")
    scores["safety_score"] = clamp(safety)
    if strong_buy_gate:
        rec = "Strong Buy"
    elif buy_gate:
        rec = "Buy"
    elif sell_gate:
        rec = "Sell"
    else:
        rec = "Hold"
    scores["recommendation_model"] = rec
    return scores


def built_in_ai_thesis(ticker, info, risk, hist_ta=None, model=None):
    model = model or get_ai_risk_model()
    scores = score_from_metrics(info, risk, hist_ta, model=model)
    overall = scores["overall_score"]
    rec = scores.get("recommendation_model", "Hold")
    confidence = clamp(52 + abs(overall - 50) * 0.75)
    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"), 0)

    growth_adj = (scores["growth_score"] - 55) * 0.34
    momentum_adj = (scores["momentum_score"] - 55) * 0.30
    quality_adj = (scores["quality_score"] - 50) * 0.16
    valuation_adj = (scores["valuation_score"] - 45) * 0.12
    risk_penalty = max(scores["risk_score"] - 65, 0) * 0.12
    upside = growth_adj + momentum_adj + quality_adj + valuation_adj - risk_penalty
    if rec == "Strong Buy":
        upside += 8
    elif rec == "Buy":
        upside += 4
    elif rec == "Sell":
        upside -= 10
    target = price * (1 + upside / 100) if price else 0

    sector = info.get("sector", "the market") or "the market"
    industry = info.get("industry", "its industry") or "its industry"
    rev_g = safe_float(info.get("revenueGrowth"), 0) * 100
    margin = safe_float(info.get("profitMargins"), 0) * 100
    beta = safe_float(risk.get("beta"), 1)
    sharpe = safe_float(risk.get("sharpe"), 0)
    sortino = safe_float(risk.get("sortino"), 0)
    vol = safe_float(risk.get("vol"), 0)
    max_dd = abs(safe_float(risk.get("max_dd"), 0))

    style = (
        "Aggressive Growth Leader" if scores["growth_score"] >= 72 and scores["momentum_score"] >= 68 else
        "Growth Momentum" if scores["growth_score"] >= 62 and scores["momentum_score"] >= 60 else
        "Quality Growth" if scores["quality_score"] >= 65 and scores["growth_score"] >= 58 else
        "Value / Recovery" if scores["valuation_score"] >= 65 and scores["momentum_score"] >= 52 else
        "Balanced / Watchlist"
    )
    moat = "Wide" if scores["quality_score"] >= 75 else "Moderate" if scores["quality_score"] >= 60 else "Unclear"

    bull = f"{ticker} is scored with a growth-and-momentum-first profile. Revenue growth is about {rev_g:.1f}% and net margin is about {margin:.1f}%, while the model strongly rewards stocks trading above key moving averages with improving recent performance. A Buy rating can tolerate higher volatility, but still requires minimum quality, valuation discipline, and no extreme downside-risk profile."
    bear = f"The key risks are valuation compression, failed momentum, and large drawdowns. Beta is about {beta:.2f}, annualized volatility is about {vol:.1f}%, max drawdown is about {max_dd:.1f}%, Sharpe is {sharpe:.2f}, and Sortino is {sortino:.2f}. If growth slows or the stock loses trend strength, the model will usually downgrade even if the long-term story remains attractive."
    summary = f"Built-in thesis: {ticker} is rated {rec} with an overall score of {overall}/100. {ai_model_description(model)}"

    return {
        "recommendation": rec, "confidence": confidence, "price_target": round(target, 2),
        "upside_pct": round(upside, 1), "style": style, "horizon": "6-12 months",
        "overall_score": overall, **scores, "moat": moat,
        "moat_desc": f"Moat assessment is inferred from margins, ROE/ROA, balance-sheet strength, and industry position within {sector}.",
        "bull": bull, "bear": bear, "summary": summary,
        "catalysts": ["Revenue acceleration or higher guidance", "Breakout above major moving averages", "Earnings beats with improving margin trend", "Sector rotation into high-growth momentum names"],
        "risks": ["Growth slowdown", "Momentum reversal below key moving averages", "Multiple compression", "Extreme volatility or large drawdown"],
        "esg_score": clamp(52 + scores["quality_score"] * 0.28),
        "esg_notes": "ESG is not deeply modeled here; this score is a conservative placeholder inferred from company stability and quality metrics.",
        "insider": "Neutral", "peers": [],
    }

def comparison_paragraph(t1, info1, risk1, ta1, t2, info2, risk2, ta2):
    model = get_ai_risk_model()
    s1 = score_from_metrics(info1, risk1, ta1, model=model)
    s2 = score_from_metrics(info2, risk2, ta2, model=model)
    n1 = info1.get("longName", t1)
    n2 = info2.get("longName", t2)
    p1 = safe_float(info1.get("trailingPE"), 0)
    g2 = safe_float(info2.get("revenueGrowth"), 0) * 100
    v1 = safe_float(risk1.get("vol"), 0)
    v2 = safe_float(risk2.get("vol"), 0)
    sh2 = safe_float(risk2.get("sharpe"), 0)
    winner = t1 if s1["overall_score"] >= s2["overall_score"] else t2
    return (
        f"{n1} ({t1}) has an overall score of {s1['overall_score']}/100 versus {n2} ({t2}) at {s2['overall_score']}/100, so the dashboard slightly favors {winner} on the combined indicator view. "
        f"{t1}'s advantage is its relative mix of valuation, growth, quality, and trend strength; its drawback is higher risk if volatility ({v1:.1f}%) or valuation (P/E {p1:.1f}) look stretched. "
        f"{t2}'s advantage is its own stability, valuation, or trend profile when Sharpe ({sh2:.2f}), volatility ({v2:.1f}%), and revenue growth ({g2:.1f}%) compare favorably; its weakness is lower upside if momentum or profitability lag. "
        f"For direct trading decisions, compare the normalized price chart for trend leadership and the volatility chart for risk."
    )





# ══════════════════════════════════════════════════════════════════
#  BOND / OPTION CALCULATORS
# ══════════════════════════════════════════════════════════════════
def bond_price(face, coupon_rate, ytm, years, freq=2):
    try:
        n = int(round(years * freq))
        if n <= 0 or face <= 0 or freq <= 0:
            return 0.0
        c = face * coupon_rate / freq
        r = ytm / freq
        if abs(r) < 1e-12:
            return c * n + face
        return sum(c / ((1 + r) ** t) for t in range(1, n + 1)) + face / ((1 + r) ** n)
    except Exception:
        return 0.0


def bond_duration_convexity(face, coupon_rate, ytm, years, freq=2):
    n = int(round(years * freq))
    c = face * coupon_rate / freq
    r = ytm / freq
    times = np.array([(i / freq) for i in range(1, n + 1)], dtype=float)
    cashflows = np.array([c] * n, dtype=float)
    if n > 0:
        cashflows[-1] += face
    discounts = np.array([(1 + r) ** i for i in range(1, n + 1)], dtype=float)
    pv = cashflows / discounts
    price = float(pv.sum()) if len(pv) else 0.0
    if price <= 0:
        return 0.0, 0.0, 0.0
    macaulay = float((times * pv).sum() / price)
    modified = macaulay / (1 + r)
    convexity = float(np.sum(pv * times * (times + 1 / freq)) / (price * (1 + r) ** 2))
    return macaulay, modified, convexity


def bond_cashflow_table(face, coupon_rate, ytm, years, freq=2):
    n = int(round(years * freq))
    c = face * coupon_rate / freq
    r = ytm / freq
    rows = []
    for i in range(1, n + 1):
        cf = c + (face if i == n else 0)
        pv = cf / ((1 + r) ** i) if (1 + r) else 0
        rows.append({"Period": i, "Year": round(i / freq, 2), "Cash Flow": round(cf, 2), "Present Value": round(pv, 2)})
    return pd.DataFrame(rows)


def bond_price_sensitivity_chart(face, coupon_rate, ytm, years, freq=2):
    shocks = np.arange(-2.0, 2.01, 0.25)
    prices = [bond_price(face, coupon_rate, max(ytm + s / 100, -0.99), years, freq) for s in shocks]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=shocks, y=prices, mode="lines+markers", line=dict(color=BLUE, width=2), name="Bond Price"))
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#64748b")
    fig.update_layout(**base_layout(height=310))
    fig.update_layout(
        xaxis_title="Yield Shock (percentage points)",
        yaxis_title="Estimated Price",
        yaxis=dict(tickprefix="$", showgrid=True, gridcolor=GRID_COL, side="right"),
        xaxis=dict(ticksuffix="%", showgrid=False),
        margin=dict(l=20, r=70, t=20, b=45),
    )
    return fig


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black_scholes(S, K, T, r, sigma, option_type="Call", q=0.0):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if option_type == "Call" else max(K - S, 0)
        return {"price": intrinsic, "delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0, "d1": 0, "d2": 0, "intrinsic": intrinsic, "time_value": 0}
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option_type == "Call":
        price = S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = math.exp(-q * T) * _norm_cdf(d1)
        theta = (-(S * math.exp(-q*T) * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                 - r * K * math.exp(-r*T) * _norm_cdf(d2) + q * S * math.exp(-q*T) * _norm_cdf(d1)) / 365
        rho = K * T * math.exp(-r*T) * _norm_cdf(d2) / 100
        intrinsic = max(S - K, 0)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)
        delta = -math.exp(-q * T) * _norm_cdf(-d1)
        theta = (-(S * math.exp(-q*T) * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                 + r * K * math.exp(-r*T) * _norm_cdf(-d2) - q * S * math.exp(-q*T) * _norm_cdf(-d1)) / 365
        rho = -K * T * math.exp(-r*T) * _norm_cdf(-d2) / 100
        intrinsic = max(K - S, 0)
    gamma = math.exp(-q*T) * _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * math.exp(-q*T) * _norm_pdf(d1) * math.sqrt(T) / 100
    return {"price": price, "delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho, "d1": d1, "d2": d2, "intrinsic": intrinsic, "time_value": max(price - intrinsic, 0)}


def option_payoff_chart(S, K, premium, option_type="Call"):
    lo = max(0.01, S * 0.5)
    hi = S * 1.5
    xs = np.linspace(lo, hi, 180)
    if option_type == "Call":
        payoff = np.maximum(xs - K, 0) - premium
        breakeven = K + premium
    else:
        payoff = np.maximum(K - xs, 0) - premium
        breakeven = K - premium
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=payoff, mode="lines", line=dict(color=BLUE, width=2), name="Expiration P/L"))
    fig.add_hline(y=0, line_color="#64748b", line_dash="dash", line_width=1)
    fig.add_vline(x=S, line_color=AMBER, line_dash="dot", line_width=1)
    fig.add_vline(x=breakeven, line_color=GREEN, line_dash="dash", line_width=1)
    fig.update_layout(**base_layout(height=310))
    fig.update_layout(
        xaxis_title="Underlying Price at Expiration",
        yaxis_title="Profit / Loss per Share",
        yaxis=dict(tickprefix="$", showgrid=True, gridcolor=GRID_COL, side="right"),
        xaxis=dict(tickprefix="$", showgrid=False),
        margin=dict(l=20, r=70, t=20, b=45),
    )
    return fig

def clean_text(x):
    if x is None:
        return ""
    try:
        x = re.sub(r"<[^>]+>", " ", str(x))
        x = html.unescape(x)
        return re.sub(r"\s+", " ", x).strip()
    except Exception:
        return ""


def _news_timestamp(value):
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(pd.to_datetime(value, utc=True).timestamp())
    except Exception:
        return 0


def _extract_yf_news_item(item, ticker):
    content = item.get("content", item) if isinstance(item, dict) else {}
    title = clean_text((content.get("title") if isinstance(content, dict) else "") or (item.get("title") if isinstance(item, dict) else ""))
    summary = clean_text((content.get("summary") if isinstance(content, dict) else "") or (content.get("description") if isinstance(content, dict) else "") or (item.get("summary", "") if isinstance(item, dict) else ""))
    provider = content.get("provider") if isinstance(content, dict) else None
    publisher = provider.get("displayName", "") if isinstance(provider, dict) else ""
    publisher = clean_text(publisher or (content.get("publisher") if isinstance(content, dict) else "") or (item.get("publisher", "FMP") if isinstance(item, dict) else "FMP"))
    link = ""
    if isinstance(content, dict) and isinstance(content.get("clickThroughUrl"), dict):
        link = content.get("clickThroughUrl", {}).get("url", "")
    if not link and isinstance(content, dict) and isinstance(content.get("canonicalUrl"), dict):
        link = content.get("canonicalUrl", {}).get("url", "")
    link = link or (item.get("link", "") if isinstance(item, dict) else "")
    ts_val = None
    if isinstance(content, dict):
        ts_val = content.get("pubDate") or content.get("displayTime")
    if not ts_val and isinstance(item, dict):
        ts_val = item.get("providerPublishTime")
    ts = _news_timestamp(ts_val)
    return {"ticker": ticker, "title": title, "summary": summary, "publisher": publisher or "FMP", "link": link, "ts": ts, "source_rank": 1}


def sentiment_and_impact(title, summary, ticker=""):
    """Score news by likely stock-price relevance.

    Importance is intentionally event-driven: financial reports, earnings,
    guidance, regulation/policy, rates/Fed, litigation, M&A, analyst actions,
    capital returns, credit/debt, and major macro shocks are weighted much more
    heavily than generic market commentary.
    """
    text = f"{title} {summary}".lower()

    # Price-direction words. These drive sentiment/influence, not just importance.
    pos_words = {
        "beat": 12, "beats": 12, "beat estimates": 14, "tops estimates": 12,
        "raises guidance": 16, "raises outlook": 14, "raised guidance": 14,
        "upgrade": 11, "upgraded": 11, "buy rating": 9, "outperform": 9,
        "price target raised": 11, "higher target": 9, "strong demand": 9,
        "record revenue": 8, "record profit": 8, "margin expands": 8,
        "profit growth": 7, "revenue growth": 7, "free cash flow": 6,
        "buyback": 7, "dividend increase": 7, "approval": 8,
        "contract": 7, "partnership": 5, "launch": 4, "surge": 7, "rally": 5,
    }
    neg_words = {
        "miss": -13, "misses": -13, "missed estimates": -15,
        "cuts guidance": -17, "guidance cut": -17, "lowers outlook": -15,
        "downgrade": -11, "downgraded": -11, "sell rating": -10, "underperform": -10,
        "price target cut": -11, "probe": -10, "investigation": -11, "sec investigation": -14,
        "lawsuit": -10, "class action": -9, "antitrust": -10, "regulatory scrutiny": -9,
        "warning": -8, "profit warning": -13, "slowdown": -8, "weak demand": -9,
        "margin pressure": -8, "loss widens": -9, "debt concern": -8,
        "layoff": -5, "tariff": -6, "sanction": -8, "recall": -8,
        "slump": -7, "drops": -5, "falls": -5, "bearish": -7,
    }

    score = 0
    hits = []
    for w, v in pos_words.items():
        if w in text:
            score += v
            hits.append(w)
    for w, v in neg_words.items():
        if w in text:
            score += v
            hits.append(w)

    # Event-category importance. These are the items traders usually care about most.
    critical_categories = {
        "Earnings / Financial Report": [
            "earnings", "quarterly results", "q1 results", "q2 results", "q3 results", "q4 results",
            "financial results", "annual report", "10-k", "10-q", "eps", "profit", "net income",
            "revenue", "sales", "margin", "free cash flow", "cash flow", "ebitda", "operating income",
        ],
        "Guidance / Outlook": [
            "guidance", "outlook", "forecast", "full-year", "fy", "raises outlook", "lowers outlook",
            "cuts guidance", "raises guidance", "profit warning", "preliminary results",
        ],
        "Policy / Regulation": [
            "fed", "federal reserve", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "ppi",
            "policy", "regulation", "regulatory", "antitrust", "tariff", "sanction", "export control",
            "government", "white house", "congress", "sec", "doj", "ftc", "fda", "approval",
        ],
        "Analyst / Rating": [
            "analyst", "upgrade", "downgrade", "rating", "price target", "initiates coverage",
            "buy rating", "sell rating", "outperform", "underperform", "overweight", "neutral rating",
        ],
        "M&A / Strategic Deal": [
            "acquisition", "acquires", "merger", "takeover", "buyout", "deal", "joint venture",
            "partnership", "strategic investment", "stake", "spin off", "spinoff",
        ],
        "Legal / Investigation": [
            "lawsuit", "sued", "class action", "settlement", "probe", "investigation", "fraud",
            "subpoena", "sec investigation", "doj", "ftc", "antitrust",
        ],
        "Capital Return / Balance Sheet": [
            "dividend", "buyback", "repurchase", "debt", "bond", "credit rating", "downgrade debt",
            "cash", "liquidity", "bankruptcy", "offering", "share sale", "secondary offering",
        ],
        "Product / Demand Shock": [
            "launch", "order", "contract", "backlog", "shipment", "recall", "supply chain",
            "demand", "shortage", "ai", "cloud", "chip", "semiconductor",
        ],
    }

    category_scores = []
    for category, terms in critical_categories.items():
        matches = [term for term in terms if term in text]
        if matches:
            category_scores.append((category, min(32, 14 + 4 * len(matches))))

    category = category_scores[0][0] if category_scores else "General Market News"
    event_score = sum(v for _, v in category_scores)

    # Extra boosts for phrases that are highly material even if sentiment is neutral.
    high_material_phrases = [
        "earnings call", "earnings report", "reports earnings", "quarterly earnings",
        "beats earnings", "misses earnings", "raises guidance", "cuts guidance",
        "revenue beat", "revenue miss", "sec filing", "10-k", "10-q",
        "federal reserve", "rate decision", "cpi report", "export controls",
        "antitrust lawsuit", "class action", "merger agreement", "acquisition offer",
    ]
    material_boost = sum(10 for phrase in high_material_phrases if phrase in text)

    # Source and ticker boosts help keep direct company news above broad market filler.
    source_boost = 0
    publisher_blob = text
    if "wall street journal" in publisher_blob or "wsj" in publisher_blob or "yahoo finance" in publisher_blob:
        source_boost += 4
    ticker_boost = 12 if ticker and ticker.lower() in text else 0

    importance = 18 + event_score + material_boost + min(len(hits) * 5, 20) + ticker_boost + source_boost
    importance = max(0, min(100, importance))

    if score > 5:
        sent = "Positive"
    elif score < -5:
        sent = "Negative"
    else:
        sent = "Neutral"

    # Influence combines direction and materiality. Important neutral news still gets a nonzero watch value.
    if score != 0:
        influence = score * 3.2 + (importance - 50) * (1 if score > 0 else -1) * 0.45
    else:
        influence = 0 if importance < 65 else 8
    influence = max(-100, min(100, influence))
    return sent, int(round(influence)), int(round(importance)), category


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_items(ticker, keyword="", refresh_token=0):
    del refresh_token
    items = []
    try:
        yf_news = _fmp_ticker(ticker).news or []
        for raw in yf_news[:35]:
            n = _extract_yf_news_item(raw, ticker)
            if n["title"]:
                items.append(n)
    except Exception:
        pass
    headers = {"User-Agent": "Mozilla/5.0 StockAnalyzer/1.0"}
    queries = [f"{ticker} stock OR shares finance", f"{ticker} earnings stock"]
    if keyword:
        queries.insert(0, f"{ticker} {keyword} stock")
    for q in queries[:3]:
        try:
            url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-US&gl=US&ceid=US:en"
            r = requests.get(url, headers=headers, timeout=6)
            if r.ok:
                root = ET.fromstring(r.content)
                for it in root.findall(".//item")[:20]:
                    title = clean_text(it.findtext("title"))
                    summary = clean_text(it.findtext("description"))
                    link = clean_text(it.findtext("link"))
                    ts = _news_timestamp(it.findtext("pubDate"))
                    publisher = "Google News"
                    if " - " in title:
                        possible_title, possible_pub = title.rsplit(" - ", 1)
                        title, publisher = possible_title.strip(), possible_pub.strip()
                    items.append({"ticker": ticker, "title": title, "summary": summary, "publisher": publisher, "link": link, "ts": ts, "source_rank": 2})
        except Exception:
            pass
    try:
        for url in ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"]:
            r = requests.get(url, headers=headers, timeout=6)
            if r.ok:
                root = ET.fromstring(r.content)
                for it in root.findall(".//item")[:30]:
                    title = clean_text(it.findtext("title"))
                    summary = clean_text(it.findtext("description"))
                    blob = f"{title} {summary}".lower()
                    if ticker.lower() in blob or (keyword and keyword.lower() in blob):
                        items.append({"ticker": ticker, "title": title, "summary": summary, "publisher": "WSJ", "link": clean_text(it.findtext("link")), "ts": _news_timestamp(it.findtext("pubDate")), "source_rank": 1})
    except Exception:
        pass
    kw = clean_text(keyword or "").strip().lower()
    dedup = {}
    for n in items:
        title = n.get("title", "")
        summary = n.get("summary", "")
        if not title:
            continue
        if kw and kw not in f"{title} {summary} {n.get('publisher','')}".lower():
            continue
        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()[:90]
        sent, influence, importance, category = sentiment_and_impact(title, summary, ticker)
        n.update({"sentiment": sent, "influence": influence, "importance": importance, "category": category})
        old = dedup.get(key)
        if old is None or (n["source_rank"], -n["ts"], -n["importance"]) < (old["source_rank"], -old["ts"], -old["importance"]):
            dedup[key] = n
    out = list(dedup.values())
    # Keep material stock-moving news in front. Earnings/guidance/policy/legal/M&A items
    # should not be buried by generic recent headlines.
    out.sort(key=lambda x: (x.get("importance", 0), abs(x.get("influence", 0)), x.get("ts", 0)), reverse=True)
    important = [x for x in out if x.get("importance", 0) >= 65]
    newest = sorted(out, key=lambda x: x.get("ts", 0), reverse=True)[:8]
    merged = []
    seen = set()
    for x in important + out[:20] + newest:
        k = re.sub(r"[^a-z0-9]+", " ", x.get("title", "").lower()).strip()[:90]
        if k and k not in seen:
            seen.add(k)
            merged.append(x)
    return merged[:24]


def render_news_item(n):
    ts = n.get("ts") or 0
    when = datetime.fromtimestamp(ts).strftime("%b %d, %Y %I:%M %p") if ts else "Recent"
    sent = n.get("sentiment", "Neutral")
    sent_display = tr(sent)
    cls = "news-positive" if sent == "Positive" else "news-negative" if sent == "Negative" else "news-neutral"
    link = n.get("link", "")
    raw_title = n.get("title", "Untitled")
    raw_summary = n.get("summary", "")
    title = html.escape(raw_title)
    summary = html.escape(raw_summary)
    publisher = html.escape(n.get("publisher", "News"))
    url_html = f'<a href="{html.escape(link)}" target="_blank" style="color:#60a5fa;text-decoration:none">{tr("Open source")} ↗</a>' if link else ""
    body = f'''
    <div class="news-card">
      <div class="news-meta">{publisher} · {when}</div>
      <div class="news-title">{title}</div>
      <span class="news-pill {cls}">{sent_display}</span>
      <span class="news-pill">{html.escape(n.get('category', 'General Market News'))}</span>
      <span class="news-pill">{tr("Influence")} {n.get('influence',0):+d}/100</span>
      <span class="news-pill">{tr("Importance")} {n.get('importance',0)}/100</span>
      <div class="news-summary">{summary if summary else tr('No short summary was provided by the source.')}</div>
      <div style="font-size:12px;margin-top:8px">{url_html}</div>
    </div>
    '''
    st.markdown(body, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  BROAD MARKET NEWS ENGINE — source-prioritized, AI-style summaries
# ══════════════════════════════════════════════════════════════════
MARKET_NEWS_CATEGORIES = [
    "All Categories", "Policy / Regulation", "Central Bank / Rates", "Geopolitics / Conflict",
    "Financial Release", "Management Change", "M&A / Strategic Deal", "Commodities / Energy",
    "Technology / AI", "Banking / Credit", "Healthcare / FDA", "Earnings / Guidance",
    "Macro Data", "Legal / Investigation", "General Market News",
]
MARKET_NEWS_COUNTRIES = ["All Countries", "United States", "Global", "China", "Europe", "Japan", "Middle East", "United Kingdom", "Canada", "Emerging Markets"]
MARKET_NEWS_INDUSTRIES = [
    "All Industries", "Energy", "Semiconductors", "Software / Cloud", "Banks", "Financials",
    "Defense", "Airlines / Travel", "Shipping", "Industrials", "Consumer / Retail",
    "Autos", "Healthcare", "Biotech", "Utilities", "Real Estate", "Materials", "Crypto",
]
MARKET_SOURCE_RANK = {
    "FMP": 1, "WSJ": 1, "Wall Street Journal": 1,
    "Reuters": 2, "Associated Press": 2, "AP": 2, "CNBC": 2, "Bloomberg": 2, "MarketWatch": 2,
    "Financial Times": 3, "Barron's": 3, "Investing.com": 4, "Google News": 5,
}


def _market_clean_publisher(title, default="News"):
    title = clean_text(title)
    if " - " in title:
        possible_title, possible_pub = title.rsplit(" - ", 1)
        return possible_title.strip(), possible_pub.strip() or default
    return title, default


def _market_ai_headline(title):
    # Concise local AI-style headline without external API dependency.
    t = clean_text(title)
    if " - " in t:
        t = t.rsplit(" - ", 1)[0].strip()
    replacements = [
        (r"\bStock Market Today:\s*", ""), (r"\bStocks (rise|fall|open|close|mixed) as\b", "Market moves as"),
        (r"\bDow Jones Futures:\s*", "Futures:"), (r"\bLive Updates:?\s*", ""),
        (r"\bWhat to Watch\b", "Market watch"),
    ]
    for pat, repl in replacements:
        t = re.sub(pat, repl, t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -|•")
    words = t.split()
    if len(words) > 15:
        t = " ".join(words[:15]).rstrip(",.;:") + "…"
    return t or "Market update"


def _market_detect_country(text):
    blob = text.lower()
    rules = [
        ("Middle East", ["hormuz", "iran", "israel", "middle east", "gulf", "red sea", "opec"]),
        ("China", ["china", "beijing", "hong kong", "shanghai", "pboc", "yuan", "taiwan"]),
        ("Europe", ["europe", "eurozone", "ecb", "germany", "france", "italy", "brussels", "eu "]),
        ("Japan", ["japan", "boj", "tokyo", "yen"]),
        ("United Kingdom", ["u.k.", "uk ", "britain", "london", "boe"]),
        ("Canada", ["canada", "bank of canada", "toronto"]),
        ("Emerging Markets", ["emerging market", "india", "brazil", "mexico", "argentina", "south africa"]),
        ("United States", ["u.s.", "us ", "america", "fed", "federal reserve", "white house", "congress", "sec", "nasdaq", "s&p", "dow"]),
    ]
    for country, kws in rules:
        if any(k in blob for k in kws):
            return country
    return "Global"


def _market_category(text):
    blob = text.lower()
    category_terms = [
        ("Geopolitics / Conflict", ["hormuz", "war", "conflict", "strike", "sanction", "missile", "red sea", "iran", "israel", "russia", "ukraine"]),
        ("Central Bank / Rates", ["federal reserve", "fed ", "rate cut", "rate hike", "interest rate", "treasury yield", "ecb", "boj", "inflation"]),
        ("Policy / Regulation", ["tariff", "policy", "regulation", "regulatory", "export control", "white house", "congress", "sec", "doj", "ftc", "fda", "tax"]),
        ("Financial Release", ["cpi", "ppi", "payroll", "jobs report", "gdp", "retail sales", "ism", "pmi", "financial results", "quarterly results"]),
        ("Management Change", ["ceo", "cfo", "resigns", "steps down", "appointed", "management change", "board"]),
        ("Earnings / Guidance", ["earnings", "guidance", "outlook", "profit warning", "eps", "revenue", "margin"]),
        ("M&A / Strategic Deal", ["merger", "acquisition", "takeover", "buyout", "deal", "stake", "spin off", "spinoff"]),
        ("Commodities / Energy", ["oil", "brent", "wti", "natural gas", "gold", "copper", "commodity", "opec", "hormuz"]),
        ("Technology / AI", ["ai", "artificial intelligence", "chip", "semiconductor", "data center", "cloud", "software"]),
        ("Banking / Credit", ["bank", "credit", "loan", "default", "delinquency", "commercial real estate", "capital requirement"]),
        ("Healthcare / FDA", ["fda", "drug", "clinical trial", "biotech", "medicare", "healthcare"]),
        ("Legal / Investigation", ["lawsuit", "investigation", "probe", "settlement", "antitrust", "fraud"]),
        ("Macro Data", ["inflation", "gdp", "jobs", "payroll", "consumer confidence", "manufacturing", "services"]),
    ]
    for cat, kws in category_terms:
        if any(k in blob for k in kws):
            return cat
    return "General Market News"


def _market_impact_analysis(title, summary):
    text = f"{title} {summary}".lower()
    good, bad, watch, companies = [], [], [], []
    def add_good(item):
        if item not in good: good.append(item)
    def add_bad(item):
        if item not in bad: bad.append(item)
    def add_watch(item):
        if item not in watch: watch.append(item)

    if any(k in text for k in ["hormuz", "iran", "middle east", "red sea", "opec", "oil shock"]):
        add_good("Energy producers, oil services, defense")
        add_bad("Airlines, travel, shipping, consumer discretionary")
        add_watch("Inflation-sensitive growth stocks, broad indexes")
        companies += ["XOM", "CVX", "COP", "SLB", "RTX", "LMT", "DAL", "UAL", "AAL"]
    if any(k in text for k in ["rate cut", "lower rates", "dovish", "yields fall"]):
        add_good("Software/cloud, semiconductors, real estate, small caps")
        add_bad("Banks with net-interest-margin pressure")
        add_watch("Long-duration growth valuation multiples")
        companies += ["NVDA", "MSFT", "CRM", "PLD", "JPM", "BAC"]
    if any(k in text for k in ["rate hike", "higher rates", "hawkish", "yields rise", "hot inflation"]):
        add_good("Banks, cash-rich defensive firms")
        add_bad("High-multiple growth, real estate, utilities")
        add_watch("Dollar, Treasury yields, financing costs")
        companies += ["JPM", "BAC", "NVDA", "TSLA", "PLD", "NEE"]
    if any(k in text for k in ["tariff", "export control", "sanction", "trade restriction"]):
        add_good("Domestic substitutes, selected defense/security")
        add_bad("Semiconductors, global hardware supply chains, China ADRs, retailers")
        add_watch("Margin pressure and retaliation risk")
        companies += ["NVDA", "AMD", "AAPL", "TSM", "BABA", "PDD", "WMT"]
    if any(k in text for k in ["ai", "artificial intelligence", "data center", "chip", "semiconductor"]):
        add_good("Semiconductors, cloud infrastructure, power equipment")
        add_bad("Legacy software without AI monetization")
        add_watch("Capex sustainability and valuation risk")
        companies += ["NVDA", "AMD", "AVGO", "MSFT", "GOOGL", "AMZN", "ORCL"]
    if any(k in text for k in ["fda", "clinical trial", "drug approval", "medicare"]):
        add_good("Biotech/healthcare winners named in headline")
        add_bad("Competitors with weaker pipelines or pricing pressure")
        add_watch("Binary trial/FDA risk")
        companies += ["LLY", "NVO", "MRK", "PFE", "JNJ"]
    if any(k in text for k in ["bank", "credit", "default", "delinquency", "commercial real estate"]):
        add_good("Large diversified banks if credit stress is contained")
        add_bad("Regional banks, highly levered real estate")
        add_watch("Credit spreads and deposit flows")
        companies += ["JPM", "BAC", "KRE", "SCHW", "PLD"]
    if any(k in text for k in ["earnings", "guidance", "revenue", "margin", "profit"]):
        add_good("Companies beating guidance with margin expansion")
        add_bad("Companies cutting outlook or showing demand weakness")
        add_watch("Sector read-through from earnings commentary")
    if any(k in text for k in ["ceo", "cfo", "resigns", "steps down", "appointed"]):
        add_good("Turnaround stories if leadership improves execution")
        add_bad("Companies with unexpected executive exits")
        add_watch("Management credibility and strategy reset")
    if any(k in text for k in ["merger", "acquisition", "takeover", "buyout"]):
        add_good("Target company, investment banks, strategic consolidators")
        add_bad("Acquirer if price/leverage is excessive")
        add_watch("Regulatory approval risk")
    if not good: add_good("Possible winners depend on the named sector/company")
    if not bad: add_bad("Possible losers depend on valuation, exposure, and expectations")
    if not watch: add_watch("Watch price reaction, volume, yields, FX, and sector breadth")
    return {"good_for": good[:4], "bad_for": bad[:4], "watch": watch[:4], "companies": sorted(set([c for c in companies if c]))[:14]}


def _market_score_and_sentiment(title, summary, publisher=""):
    text = f"{title} {summary}".lower()
    importance = 24
    high = ["hormuz", "federal reserve", "rate decision", "cpi", "jobs report", "tariff", "export control", "war", "oil", "earnings", "guidance", "merger", "acquisition", "ceo", "fda", "bank", "credit"]
    med = ["inflation", "yields", "revenue", "profit", "margin", "ai", "chips", "semiconductor", "lawsuit", "probe", "policy", "regulation", "global", "china", "europe"]
    importance += sum(9 for k in high if k in text)
    importance += sum(4 for k in med if k in text)
    pub_rank = MARKET_SOURCE_RANK.get(publisher, 4)
    importance += max(0, 8 - pub_rank * 2)
    importance = clamp(importance, 0, 100)
    pos_terms = ["beat", "beats", "surge", "rally", "approval", "deal", "raises", "growth", "record", "cut rates", "dovish"]
    neg_terms = ["miss", "slump", "falls", "drops", "war", "conflict", "cuts guidance", "tariff", "sanction", "probe", "lawsuit", "hot inflation", "hawkish"]
    pos = sum(1 for k in pos_terms if k in text)
    neg = sum(1 for k in neg_terms if k in text)
    if pos > neg: sentiment = "Positive"
    elif neg > pos: sentiment = "Negative"
    else: sentiment = "Mixed / Watch"
    return importance, sentiment


def _market_ai_summary(title, summary, category, impact):
    base = clean_text(summary) or clean_text(title)
    if len(base.split()) > 34:
        base = " ".join(base.split()[:34]).rstrip(",.;:") + "…"
    good = "; ".join(impact.get("good_for", [])[:2])
    bad = "; ".join(impact.get("bad_for", [])[:2])
    return f"{base} Category: {category}. Likely positive for {good}; possible pressure on {bad}."


def _market_parse_rss_items(xml_bytes, publisher_default="News", source_rank=5, limit=40):
    rows = []
    try:
        root = ET.fromstring(xml_bytes)
        for it in root.findall(".//item")[:limit]:
            title_raw = clean_text(it.findtext("title"))
            title, publisher = _market_clean_publisher(title_raw, publisher_default)
            rows.append({"title": title, "summary": clean_text(it.findtext("description")), "link": clean_text(it.findtext("link")), "publisher": publisher or publisher_default, "ts": _news_timestamp(it.findtext("pubDate")), "source_rank": source_rank})
    except Exception:
        pass
    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market_news(keyword="", ticker_query="", refresh_token=0):
    del refresh_token
    keyword = clean_text(keyword or "").strip()
    ticker_query = clean_text(ticker_query or "").strip().upper()
    ticker_company = ""
    if ticker_query:
        try:
            tinfo = _fmp_ticker(ticker_query).get_info()
            ticker_company = clean_text(tinfo.get("shortName") or tinfo.get("longName") or "")
        except Exception:
            ticker_company = ""
    headers = {"User-Agent": "Mozilla/5.0 StockAnalyzerPro/2.0"}
    items = []
    market_symbols = ["^GSPC", "^IXIC", "^DJI", "CL=F", "GC=F", "BTC-USD", "XLK", "XLF", "XLE", "SMH"]
    if ticker_query and ticker_query not in market_symbols:
        market_symbols.insert(0, ticker_query)
    for symbol in market_symbols:
        try:
            for raw in (_fmp_ticker(symbol).news or [])[:12]:
                n = _extract_yf_news_item(raw, symbol)
                if n.get("title"):
                    n["publisher"] = n.get("publisher") or "FMP"
                    n["source_rank"] = 1
                    items.append(n)
        except Exception:
            pass
    for url, pub in [("https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "WSJ"), ("https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "WSJ"), ("https://feeds.a.dj.com/rss/RSSWorldNews.xml", "WSJ")]:
        try:
            r = requests.get(url, headers=headers, timeout=7)
            if r.ok:
                items.extend(_market_parse_rss_items(r.content, pub, source_rank=1, limit=45))
        except Exception:
            pass
    queries = [
        "latest stock market news policy rates earnings global market",
        "market news Federal Reserve CPI tariffs earnings guidance",
        "global market news China Europe Japan Middle East oil",
        "Hormuz conflict oil market impact airlines energy shipping",
        "management change CEO CFO stock market latest",
        "financial release earnings guidance major companies latest",
    ]
    if ticker_query:
        ticker_terms = f"{ticker_query} {ticker_company}".strip()
        queries.insert(0, ticker_terms + " stock company market news earnings guidance")
    if keyword.strip():
        queries.insert(0, keyword.strip() + " market news stocks")
    for q in queries[:8]:
        try:
            url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-US&gl=US&ceid=US:en"
            r = requests.get(url, headers=headers, timeout=7)
            if r.ok:
                rows = _market_parse_rss_items(r.content, "Google News", source_rank=4, limit=24)
                for row in rows:
                    pub = row.get("publisher", "")
                    if pub in MARKET_SOURCE_RANK:
                        row["source_rank"] = MARKET_SOURCE_RANK.get(pub, 4)
                    items.append(row)
        except Exception:
            pass
    kw = keyword.strip().lower()
    tq = ticker_query.lower()
    tc = ticker_company.lower()
    dedup = {}
    for n in items:
        title = clean_text(n.get("title", "")); summary = clean_text(n.get("summary", ""))
        if not title: continue
        blob = f"{title} {summary} {n.get('publisher','')}".lower()
        category = _market_category(blob); country = _market_detect_country(blob); impact = _market_impact_analysis(title, summary)
        if kw and kw not in blob:
            continue
        if tq:
            impact_companies = " ".join(impact.get("companies", []))
            ticker_blob = f"{blob} {n.get('ticker','')} {ticker_company} {impact_companies}".lower()
            ticker_match = str(n.get("ticker", "")).upper() == ticker_query
            if ticker_query in {str(c).upper() for c in impact.get("companies", [])}:
                ticker_match = True
            if len(tq) > 3:
                ticker_pat = r"(?<![a-z0-9])" + re.escape(tq) + r"(?![a-z0-9])"
                ticker_match = ticker_match or bool(re.search(ticker_pat, ticker_blob))
            if tc and tc in ticker_blob:
                ticker_match = True
            if not ticker_match:
                continue
        importance, sentiment = _market_score_and_sentiment(title, summary, n.get("publisher", ""))
        importance = clamp(importance + min(14, 2 * len(impact.get("companies", []))))
        n.update({"ai_title": _market_ai_headline(title), "category": category, "country": country, "impact": impact, "importance": importance, "sentiment": sentiment, "ai_summary": _market_ai_summary(title, summary, category, impact), "industry_tags": sorted(set([x.split(",")[0].strip() for x in impact.get("good_for", []) + impact.get("bad_for", [])]))[:8]})
        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()[:95]
        old = dedup.get(key)
        new_tuple = (n.get("source_rank", 5), -n.get("importance", 0), -n.get("ts", 0))
        old_tuple = (old.get("source_rank", 5), -old.get("importance", 0), -old.get("ts", 0)) if old else None
        if old is None or new_tuple < old_tuple:
            dedup[key] = n
    out = list(dedup.values())
    out.sort(key=lambda x: (x.get("importance", 0), x.get("ts", 0)), reverse=True)
    important = [x for x in out if x.get("importance", 0) >= 70]
    recent = sorted(out, key=lambda x: x.get("ts", 0), reverse=True)[:18]
    merged, seen = [], set()
    for x in important + out[:35] + recent:
        k = re.sub(r"[^a-z0-9]+", " ", x.get("title", "").lower()).strip()[:95]
        if k and k not in seen:
            seen.add(k); merged.append(x)
    return merged[:48]


def render_market_news_item(n):
    ts = n.get("ts") or 0
    when = datetime.fromtimestamp(ts).strftime("%b %d, %Y %I:%M %p") if ts else "Recent"
    sentiment = n.get("sentiment", "Mixed / Watch")
    cls = "news-positive" if sentiment == "Positive" else "news-negative" if sentiment == "Negative" else "news-neutral"
    title_raw = n.get("ai_title") or n.get("title", "Market update")
    title = html.escape(title_raw)
    summary_raw = n.get("ai_summary", "")
    summary = html.escape(summary_raw)
    publisher = html.escape(n.get("publisher", "News")); category = html.escape(tr(n.get("category", "General Market News"))); country = html.escape(tr(n.get("country", "Global")))
    score = int(n.get("importance", 0)); impact = n.get("impact", {}) or {}
    good = html.escape("; ".join(impact.get("good_for", [])[:4])); bad = html.escape("; ".join(impact.get("bad_for", [])[:4])); watch = html.escape("; ".join(impact.get("watch", [])[:4]))
    companies = ", ".join(impact.get("companies", [])[:14]) or "Context-dependent"
    link = n.get("link", "")
    url_html = f'<a class="market-source-link" href="{html.escape(link)}" target="_blank">{tr("Open source")} ↗</a>' if link else ""
    st.markdown(f'''
    <div class="news-card">
      <div class="market-card-top">
        <div style="min-width:0;flex:1">
          <div class="news-meta">{publisher} · {when} · {country}</div>
          <div class="news-title">{title}</div>
        </div>
        <div class="market-score-ring" style="--score:{score}">{score}</div>
      </div>
      <span class="news-pill {cls}">{html.escape(tr(sentiment))}</span>
      <span class="news-pill">{category}</span>
      <span class="news-pill">{tr("Importance")} {score}/100</span>
      <span class="news-pill">{tr("Affected")}: {html.escape(companies)}</span>
      <div class="news-summary">{summary}</div>
      <div class="market-impact-grid">
        <div class="market-impact-box"><div class="market-impact-label">{tr("Good for")}</div><div class="market-impact-good">{good}</div></div>
        <div class="market-impact-box"><div class="market-impact-label">{tr("Bad for")}</div><div class="market-impact-bad">{bad}</div></div>
        <div class="market-impact-box"><div class="market-impact-label">{tr("Watch")}</div><div class="market-impact-watch">{watch}</div></div>
      </div>
      {url_html}
    </div>
    ''', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  CHART BUILDERS  — clean Webull style, legends as HTML below
# ══════════════════════════════════════════════════════════════════

def price_chart(df, ticker, days, active_mas, show_bb, show_vol):
    """Main OHLCV candlestick chart with optional MA, BB, volume+vol panel."""
    if df is None or df.empty:
        return go.Figure()
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(set(df.columns)):
        return go.Figure()
    dp = df.tail(days).copy()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in dp.columns:
            dp[col] = 0 if col == "Volume" else np.nan
        dp[col] = pd.to_numeric(dp[col], errors="coerce")
    dp = dp.dropna(subset=["Open", "High", "Low", "Close"])
    if dp.empty:
        return go.Figure()
    up = dp["Close"] >= dp["Open"]

    rows  = 2 if show_vol else 1
    row_h = [0.70, 0.30] if show_vol else [1.0]
    specs = [[{}],[{}]] if show_vol else [[{}]]

    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.02, row_heights=row_h, specs=specs)

    # ── Candlesticks
    fig.add_trace(go.Candlestick(
        x=dp.index, open=dp["Open"], high=dp["High"],
        low=dp["Low"], close=dp["Close"],
        increasing=dict(line=dict(color=GREEN, width=1),
                        fillcolor="rgba(16,185,129,0.4)"),
        decreasing=dict(line=dict(color=RED, width=1),
                        fillcolor="rgba(239,68,68,0.4)"),
        name="Price", whiskerwidth=0.5,
    ), row=1, col=1)

    # ── Bollinger Bands
    if show_bb and "BB_U" in dp.columns:
        fig.add_trace(go.Scatter(x=dp.index, y=dp["BB_U"],
            line=dict(color="rgba(139,92,246,0.6)", width=1, dash="dot"),
            name="BB Upper", hovertemplate="%{y:.2f}"), row=1, col=1)
        fig.add_trace(go.Scatter(x=dp.index, y=dp["BB_L"],
            line=dict(color="rgba(139,92,246,0.6)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(139,92,246,0.04)",
            name="BB Lower", hovertemplate="%{y:.2f}"), row=1, col=1)
        fig.add_trace(go.Scatter(x=dp.index, y=dp["BB_M"],
            line=dict(color="rgba(139,92,246,0.45)", width=1),
            name="BB Mid", hovertemplate="%{y:.2f}"), row=1, col=1)

    # ── Moving averages
    for ma in active_mas:
        if ma in dp.columns:
            fig.add_trace(go.Scatter(
                x=dp.index, y=dp[ma].round(2),
                line=dict(color=MA_COLORS[ma], width=1.5),
                name=ma, hovertemplate=f"{ma}: %{{y:.2f}}",
            ), row=1, col=1)

    # ── Volume + rolling volatility
    if show_vol:
        bar_cols = ["rgba(16,185,129,0.5)" if u else "rgba(239,68,68,0.5)" for u in up]
        fig.add_trace(go.Bar(x=dp.index, y=dp["Volume"],
            marker_color=bar_cols, name="Volume",
            hovertemplate="Vol: %{y:,.0f}"), row=2, col=1)
        if "VOL_MA" in dp.columns:
            fig.add_trace(go.Scatter(x=dp.index, y=dp["VOL_MA"],
                line=dict(color=AMBER, width=1.2),
                name="Volume MA20", hovertemplate="Vol MA: %{y:,.0f}"), row=2, col=1)
        if "RVOL20" in dp.columns:
            # secondary y for vol%
            fig.add_trace(go.Scatter(x=dp.index, y=dp["RVOL20"].round(1),
                line=dict(color=PURPLE, width=1.3, dash="dash"),
                name="Ann.Vol 20d", yaxis="y3",
                hovertemplate="Vol%%: %{y:.1f}%%"), row=2, col=1)

    lout = base_layout(height=580 if show_vol else 460)
    lout["yaxis"].update(tickprefix="$", title=None)
    lout["xaxis"].update(rangeslider_visible=False)
    lout["margin"] = dict(l=20, r=70, t=16, b=36)

    if show_vol:
        lout["yaxis2"] = dict(
            showgrid=True, gridcolor=GRID_COL, zeroline=False,
            tickfont=dict(color=TICK_COL, size=9), side="right",
            tickformat=",.0s",
        )
        lout["yaxis3"] = dict(
            overlaying="y2", side="left", showgrid=False,
            tickfont=dict(color=PURPLE, size=9),
            ticksuffix="%", zeroline=False,
        )
        lout["xaxis2"] = dict(showgrid=False, showspikes=True,
                               spikecolor="#334155", spikethickness=1)

    fig.update_layout(**lout)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COL, zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def _indicator_fig(height=200):
    """Base figure for indicator sub-charts."""
    lout = base_layout(height=height)
    lout["margin"] = dict(l=20, r=70, t=30, b=36)
    fig = go.Figure()
    fig.update_layout(**lout)
    return fig


def add_hline_stable(fig, y, color, dash="solid", width=1):
    """Version-safe horizontal line for Plotly figures."""
    fig.add_shape(
        type="line", xref="paper", x0=0, x1=1, yref="y", y0=y, y1=y,
        line=dict(color=color, width=width, dash=dash),
    )


def rsi_chart(df, days):
    dp  = df.tail(days)
    fig = _indicator_fig(200)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.05)", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(16,185,129,0.05)", line_width=0)
    add_hline_stable(fig, 70, "rgba(239,68,68,0.4)", "dash", 1)
    add_hline_stable(fig, 50, "#2e3448", "dot", 1)
    add_hline_stable(fig, 30, "rgba(16,185,129,0.4)", "dash", 1)
    fig.add_trace(go.Scatter(x=dp.index, y=dp["RSI"].round(2),
        line=dict(color=BLUE, width=1.8), name="RSI",
        fill="tozeroy", fillcolor="rgba(59,130,246,0.07)",
        hovertemplate="RSI: %{y:.1f}"))
    if "RSI_MA" in dp.columns:
        fig.add_trace(go.Scatter(x=dp.index, y=dp["RSI_MA"].round(2),
            line=dict(color=AMBER, width=1.2, dash="dash"),
            name="RSI MA9", hovertemplate="MA9: %{y:.1f}"))
    fig.update_layout(yaxis=dict(range=[0,100], showgrid=True, gridcolor=GRID_COL,
                                  zeroline=False, tickfont=dict(color=TICK_COL, size=10),
                                  side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def macd_chart(df, days):
    dp  = df.tail(days)
    hcl = ["rgba(16,185,129,0.75)" if v>=0 else "rgba(239,68,68,0.75)"
           for v in dp["MACD_H"].fillna(0)]
    fig = _indicator_fig(200)
    add_hline_stable(fig, 0, "#2e3448", "solid", 1)
    fig.add_trace(go.Bar(x=dp.index, y=dp["MACD_H"].round(3),
        marker_color=hcl, name="Histogram",
        hovertemplate="Hist: %{y:.3f}"))
    fig.add_trace(go.Scatter(x=dp.index, y=dp["MACD"].round(3),
        line=dict(color=BLUE, width=1.8), name="MACD",
        hovertemplate="MACD: %{y:.3f}"))
    fig.add_trace(go.Scatter(x=dp.index, y=dp["MACD_SIG"].round(3),
        line=dict(color=RED, width=1.5), name="Signal",
        hovertemplate="Signal: %{y:.3f}"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def stoch_chart(df, days):
    dp  = df.tail(days)
    fig = _indicator_fig(200)
    fig.add_hrect(y0=80, y1=100, fillcolor="rgba(239,68,68,0.05)", line_width=0)
    fig.add_hrect(y0=0,  y1=20,  fillcolor="rgba(16,185,129,0.05)", line_width=0)
    add_hline_stable(fig, 80, "rgba(239,68,68,0.4)", "dash", 1)
    add_hline_stable(fig, 20, "rgba(16,185,129,0.4)", "dash", 1)
    fig.add_trace(go.Scatter(x=dp.index, y=dp["STOCH_K"].round(2),
        line=dict(color=BLUE, width=1.8), name="%K",
        hovertemplate="%%K: %{y:.1f}"))
    fig.add_trace(go.Scatter(x=dp.index, y=dp["STOCH_D"].round(2),
        line=dict(color=RED, width=1.5, dash="dash"), name="%D",
        hovertemplate="%%D: %{y:.1f}"))
    fig.update_layout(yaxis=dict(range=[0,100], showgrid=True, gridcolor=GRID_COL,
                                  zeroline=False, tickfont=dict(color=TICK_COL, size=10),
                                  side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def vol_chart(df, days):
    dp  = df.tail(days)
    fig = _indicator_fig(200)
    if "RVOL60" in dp.columns:
        fig.add_trace(go.Scatter(x=dp.index, y=dp["RVOL60"].round(1),
            line=dict(color=TEAL, width=1.2, dash="dash"), name="60-Day Vol",
            hovertemplate="Vol 60d: %{y:.1f}%%"))
    if "RVOL20" in dp.columns:
        fig.add_trace(go.Scatter(x=dp.index, y=dp["RVOL20"].round(1),
            fill="tozeroy", fillcolor="rgba(139,92,246,0.1)",
            line=dict(color=PURPLE, width=1.8), name="20-Day Vol",
            hovertemplate="Vol 20d: %{y:.1f}%%"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10),
                                  ticksuffix="%", side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def drawdown_chart(dd):
    fig = _indicator_fig(220)
    fig.add_trace(go.Scatter(x=dd.index, y=dd.values.round(2),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.12)",
        line=dict(color=RED, width=1.5), name="Drawdown",
        hovertemplate="DD: %{y:.1f}%%"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10),
                                  ticksuffix="%", side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def returns_hist(ret):
    r = pd.to_numeric(pd.Series(ret), errors="coerce").dropna() * 100
    fig = _indicator_fig(220)
    if r.empty:
        return fig
    r = r.round(3)
    mn  = float(r.mean())
    var = float(np.percentile(r, 5))
    fig.add_trace(go.Histogram(x=r.tolist(), nbinsx=80,
        marker=dict(color=BLUE, opacity=0.55), name="Returns",
        hovertemplate="Return: %{x:.2f}%%<br>Count: %{y}"))
    if np.isfinite(mn):
        fig.add_vline(x=mn,  line_dash="dash", line_color=GREEN, line_width=1.5,
                      annotation=dict(text=f"Mean {mn:.2f}%", font_color=GREEN,
                                      font_size=10, y=1.0, yref="paper"))
    if np.isfinite(var):
        fig.add_vline(x=var, line_dash="dash", line_color=RED, line_width=1.5,
                      annotation=dict(text=f"VaR {var:.2f}%", font_color=RED,
                                      font_size=10, y=0.85, yref="paper"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10),
                                  ticksuffix="%"))
    return fig

def rolling_sharpe_chart(rs):
    fig = _indicator_fig(220)

    # Avoid Plotly add_hline here; some Plotly builds crash while converting
    # axis-spanning hlines to layout shapes. Explicit shapes are more stable.
    fig.add_shape(
        type="line", xref="paper", x0=0, x1=1, yref="y", y0=1, y1=1,
        line=dict(color="rgba(16,185,129,0.5)", width=1, dash="dash"),
    )
    fig.add_annotation(
        xref="paper", x=1.0, yref="y", y=1, text="Sharpe=1",
        showarrow=False, xanchor="right", yanchor="bottom",
        font=dict(color=GREEN, size=10),
    )
    fig.add_shape(
        type="line", xref="paper", x0=0, x1=1, yref="y", y0=0, y1=0,
        line=dict(color="rgba(239,68,68,0.4)", width=1, dash="dash"),
    )

    rs = rs.dropna()
    fig.add_trace(go.Scatter(x=rs.index, y=rs.values.round(2),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.07)",
        line=dict(color=BLUE, width=1.6), name="Sharpe",
        hovertemplate="Sharpe: %{y:.2f}"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def perf_chart(main_hist, main_ticker, peers):
    lout = base_layout(height=340)
    lout["margin"] = dict(l=20, r=70, t=16, b=36)
    fig  = go.Figure(layout=go.Layout(**lout))
    nm   = (main_hist["Close"]/main_hist["Close"].iloc[0]*100).round(2)
    fig.add_trace(go.Scatter(x=nm.index, y=nm.values, name=main_ticker,
        line=dict(color=BLUE, width=2.5),
        hovertemplate=f"{main_ticker}: %{{y:.1f}}"))
    palette = [GREEN, RED, AMBER, PURPLE, TEAL, "#fb923c", "#f472b6"]
    for i, (sym, d) in enumerate(peers.items()):
        ph = d["hist"]
        if len(ph) > 1:
            n = (ph["Close"]/ph["Close"].iloc[0]*100).round(2)
            fig.add_trace(go.Scatter(x=n.index, y=n.values, name=sym,
                line=dict(color=palette[i%len(palette)], width=1.5),
                hovertemplate=f"{sym}: %{{y:.1f}}"))
    add_hline_stable(fig, 100, "#2e3448", "dot", 1)
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig


def multiples_chart(sv, secv, spv, labels):
    lout = base_layout(height=280)
    lout["margin"] = dict(l=20, r=70, t=16, b=36)
    lout["barmode"] = "group"
    fig  = go.Figure(layout=go.Layout(**lout))
    fig.add_trace(go.Bar(name="Stock",   x=labels, y=sv,
        marker_color=BLUE,      hovertemplate="%{x}: %{y:.1f}"))
    fig.add_trace(go.Bar(name="Sector",  x=labels, y=secv,
        marker_color=AMBER,     hovertemplate="%{x}: %{y:.1f}"))
    fig.add_trace(go.Bar(name="S&P 500", x=labels, y=spv,
        marker_color="#475569", hovertemplate="%{x}: %{y:.1f}"))
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False,
                                  tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=11)))
    return fig




def compare_price_chart(h1, t1, h2, t2):
    fig = go.Figure()
    a = h1["Close"].dropna()
    b = h2["Close"].dropna()
    if len(a) > 0:
        na = (a / a.iloc[0] * 100).round(2)
        fig.add_trace(go.Scatter(x=na.index, y=na.values, name=t1, line=dict(color=BLUE, width=2.2), hovertemplate=f"{t1}: %{{y:.2f}}"))
    if len(b) > 0:
        nb = (b / b.iloc[0] * 100).round(2)
        fig.add_trace(go.Scatter(x=nb.index, y=nb.values, name=t2, line=dict(color=AMBER, width=2.2), hovertemplate=f"{t2}: %{{y:.2f}}"))
    add_hline_stable(fig, 100, "#2e3448", "dot", 1)
    lout = base_layout(height=360, title="Normalized stock price performance, start = 100")
    lout["showlegend"] = True
    lout["margin"] = dict(l=20, r=70, t=42, b=36)
    fig.update_layout(**lout)
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False, tickfont=dict(color=TICK_COL, size=10), side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig

def compare_vol_chart(ta1, t1, ta2, t2):
    fig = go.Figure()
    if "RVOL20" in ta1.columns:
        s1 = ta1["RVOL20"].dropna().round(2)
        fig.add_trace(go.Scatter(x=s1.index, y=s1.values, name=f"{t1} 20d Vol", line=dict(color=BLUE, width=2), hovertemplate=f"{t1}: %{{y:.1f}}%%"))
    if "RVOL20" in ta2.columns:
        s2 = ta2["RVOL20"].dropna().round(2)
        fig.add_trace(go.Scatter(x=s2.index, y=s2.values, name=f"{t2} 20d Vol", line=dict(color=AMBER, width=2), hovertemplate=f"{t2}: %{{y:.1f}}%%"))
    lout = base_layout(height=320, title="Annualized 20-day realized volatility")
    lout["showlegend"] = True
    lout["margin"] = dict(l=20, r=70, t=42, b=36)
    fig.update_layout(**lout)
    fig.update_layout(yaxis=dict(showgrid=True, gridcolor=GRID_COL, zeroline=False, tickfont=dict(color=TICK_COL, size=10), ticksuffix="%", side="right"),
                      xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COL, size=10)))
    return fig

def comparison_table(t1, i1, r1, ta1, t2, i2, r2, ta2):
    def row(metric, v1, v2):
        return {"Metric": metric, t1: v1, t2: v2}
    def pct(v): return fpct(v) if v is not None else "—"
    def money(v): return fmtn(v, "$")
    def last_val(ta, col):
        try: return ta[col].dropna().iloc[-1]
        except Exception: return None
    rows = [
        row("Company", i1.get("longName", t1), i2.get("longName", t2)),
        row("Sector", i1.get("sector", "—"), i2.get("sector", "—")),
        row("Industry", i1.get("industry", "—"), i2.get("industry", "—")),
        row("Market Cap", money(i1.get("marketCap")), money(i2.get("marketCap"))),
        row("Current Price", money(i1.get("currentPrice") or i1.get("regularMarketPrice")), money(i2.get("currentPrice") or i2.get("regularMarketPrice"))),
        row("P/E TTM", f"{safe_float(i1.get('trailingPE')):.2f}" if i1.get("trailingPE") else "—", f"{safe_float(i2.get('trailingPE')):.2f}" if i2.get("trailingPE") else "—"),
        row("Forward P/E", f"{safe_float(i1.get('forwardPE')):.2f}" if i1.get("forwardPE") else "—", f"{safe_float(i2.get('forwardPE')):.2f}" if i2.get("forwardPE") else "—"),
        row("P/S", f"{safe_float(i1.get('priceToSalesTrailing12Months')):.2f}" if i1.get("priceToSalesTrailing12Months") else "—", f"{safe_float(i2.get('priceToSalesTrailing12Months')):.2f}" if i2.get("priceToSalesTrailing12Months") else "—"),
        row("Revenue Growth", pct(i1.get("revenueGrowth")), pct(i2.get("revenueGrowth"))),
        row("Net Margin", pct(i1.get("profitMargins")), pct(i2.get("profitMargins"))),
        row("ROE", pct(i1.get("returnOnEquity")), pct(i2.get("returnOnEquity"))),
        row("Debt/Equity", f"{safe_float(i1.get('debtToEquity'))/100:.2f}" if i1.get("debtToEquity") else "—", f"{safe_float(i2.get('debtToEquity'))/100:.2f}" if i2.get("debtToEquity") else "—"),
        row("Beta", f"{safe_float(r1.get('beta')):.2f}", f"{safe_float(r2.get('beta')):.2f}"),
        row("Annual Volatility", f"{safe_float(r1.get('vol')):.1f}%", f"{safe_float(r2.get('vol')):.1f}%"),
        row("Sharpe", f"{safe_float(r1.get('sharpe')):.2f}", f"{safe_float(r2.get('sharpe')):.2f}"),
        row("Max Drawdown", f"{safe_float(r1.get('max_dd')):.1f}%", f"{safe_float(r2.get('max_dd')):.1f}%"),
        row("RSI", f"{safe_float(last_val(ta1,'RSI')):.1f}", f"{safe_float(last_val(ta2,'RSI')):.1f}"),
        row("20d Volatility", f"{safe_float(last_val(ta1,'RVOL20')):.1f}%", f"{safe_float(last_val(ta2,'RVOL20')):.1f}%"),
        row("Overall Score", f"{score_from_metrics(i1, r1, ta1)['overall_score']}/100", f"{score_from_metrics(i2, r2, ta2)['overall_score']}/100"),
    ]
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════
#  INVESTOR VIEW — FAMOUS INVESTOR STYLE SIMULATOR
# ══════════════════════════════════════════════════════════════════
INVESTOR_PROFILES = {
    "Warren Buffett": {
        "style": "Quality value compounder", "risk": "Moderate", "horizon": "5-10 years",
        "philosophy": "Durable moats, predictable cash flows, high return on capital, honest balance sheets, and a fair price rather than a cheap-looking low-quality stock.",
        "likes": ["quality", "value", "stability", "cash flow", "moat"],
        "avoids": ["unprofitable speculation", "excessive leverage", "hard-to-understand cyclicals"],
        "weights": {"quality": .34, "value": .25, "growth": .14, "momentum": .06, "stability": .21},
        "sector_bias": {"Consumer Defensive": 8, "Financial Services": 6, "Technology": 4, "Healthcare": 3, "Energy": 1},
        "universe": ["BRK-B","AAPL","KO","AXP","BAC","COST","V","MA","MCO","MSFT","GOOGL","JNJ","PG","PEP","WMT","HD","UNH","XOM","CVX"],
        "cash_base": 10, "concentration": "High-conviction, concentrated"
    },
    "Charlie Munger": {
        "style": "Extreme quality + mental models", "risk": "Moderate", "horizon": "Very long term",
        "philosophy": "Few outstanding businesses held patiently; quality and management matter more than frequent trading or statistical cheapness.",
        "likes": ["moat", "quality", "pricing power", "management", "simplicity"],
        "avoids": ["turnarounds", "commodity leverage", "over-diversification"],
        "weights": {"quality": .42, "value": .18, "growth": .16, "momentum": .04, "stability": .20},
        "sector_bias": {"Consumer Defensive": 7, "Technology": 6, "Financial Services": 4, "Healthcare": 3},
        "universe": ["COST","BRK-B","AAPL","MSFT","GOOGL","V","MA","MCO","SPY","JNJ","PG","KO"],
        "cash_base": 12, "concentration": "Very concentrated"
    },
    "Benjamin Graham": {
        "style": "Deep value and margin of safety", "risk": "Low-Moderate", "horizon": "2-5 years",
        "philosophy": "Prefer statistically cheap, financially sound securities with a margin of safety and less dependence on optimistic growth forecasts.",
        "likes": ["low valuation", "balance sheet", "dividends", "mean reversion"],
        "avoids": ["high P/E hype", "negative earnings", "narrative-only growth"],
        "weights": {"quality": .20, "value": .43, "growth": .06, "momentum": .04, "stability": .27},
        "sector_bias": {"Financial Services": 5, "Healthcare": 4, "Consumer Defensive": 4, "Energy": 3, "Utilities": 3},
        "universe": ["BRK-B","JPM","BAC","C","XOM","CVX","JNJ","PFE","WMT","KO","PG","T","VZ","INTC","IBM","SPY","SHY"],
        "cash_base": 18, "concentration": "Diversified value basket"
    },
    "Peter Lynch": {
        "style": "Growth at a reasonable price", "risk": "Moderate-High", "horizon": "1-5 years",
        "philosophy": "Find understandable businesses with earnings growth that the market has not fully appreciated; avoid overpaying for story stocks.",
        "likes": ["earnings growth", "reasonable PEG", "consumer insight", "category leaders"],
        "avoids": ["diworsification", "too much debt", "no earnings path"],
        "weights": {"quality": .20, "value": .22, "growth": .29, "momentum": .14, "stability": .15},
        "sector_bias": {"Consumer Cyclical": 6, "Technology": 5, "Healthcare": 4, "Consumer Defensive": 3, "Financial Services": 2},
        "universe": ["COST","HD","WMT","MCD","NKE","SBUX","AMZN","GOOGL","META","MSFT","AAPL","LLY","NVO","V","MA","SHOP","MELI","PDD"],
        "cash_base": 8, "concentration": "Diversified growth/value ideas"
    },
    "Ray Dalio": {
        "style": "Macro all-weather allocation", "risk": "Balanced", "horizon": "Cycle-aware",
        "philosophy": "Balance assets across growth/inflation regimes, diversify globally, and avoid relying on one economic outcome.",
        "likes": ["diversification", "global exposure", "inflation hedges", "bonds", "commodities"],
        "avoids": ["single-factor concentration", "unhedged macro bets"],
        "weights": {"quality": .16, "value": .15, "growth": .12, "momentum": .12, "stability": .45},
        "sector_bias": {"Consumer Defensive": 4, "Healthcare": 4, "Energy": 4, "Basic Materials": 3, "Utilities": 3},
        "universe": ["SPY","VTI","QQQ","EEM","GLD","IAU","TLT","IEF","SHY","TIP","DBC","USO","XLE","XLV","XLP","XLF","NVDA","MSFT"],
        "cash_base": 10, "concentration": "Balanced multi-asset"
    },
    "Cathie Wood": {
        "style": "Disruptive innovation growth", "risk": "Very High", "horizon": "3-7 years",
        "philosophy": "Favor companies with exponential technology adoption, high revenue growth, and large optionality even with valuation volatility.",
        "likes": ["innovation", "AI", "platform growth", "genomics", "automation", "software"],
        "avoids": ["low-growth value traps", "legacy businesses", "overly defensive assets"],
        "weights": {"quality": .12, "value": .05, "growth": .41, "momentum": .30, "stability": .12},
        "sector_bias": {"Technology": 12, "Healthcare": 7, "Consumer Cyclical": 4, "Communication Services": 4},
        "universe": ["TSLA","NVDA","PLTR","COIN","SHOP","ROKU","CRSP","TDOC","PATH","DKNG","SQ","HOOD","META","AMD","CRWD","SNOW","NET","TSM","ARKK"],
        "cash_base": 4, "concentration": "High-growth thematic"
    },
    "Stanley Druckenmiller": {
        "style": "Macro momentum and concentrated winners", "risk": "High", "horizon": "Weeks to years",
        "philosophy": "Press big macro/earnings trends, emphasize liquidity and relative strength, and cut quickly when the thesis breaks.",
        "likes": ["momentum", "macro trend", "AI leaders", "liquidity", "asymmetric payoff"],
        "avoids": ["stale laggards", "crowded downside without catalyst", "illiquidity"],
        "weights": {"quality": .18, "value": .08, "growth": .27, "momentum": .34, "stability": .13},
        "sector_bias": {"Technology": 10, "Semiconductors": 10, "Energy": 4, "Financial Services": 3},
        "universe": ["NVDA","MSFT","META","AMZN","AVGO","AMD","TSM","ASML","GOOGL","XLE","XOM","GLD","TLT","QQQ","SPY","PLTR","CRWD"],
        "cash_base": 8, "concentration": "Concentrated macro winners"
    },
    "George Soros": {
        "style": "Reflexive macro trader", "risk": "High", "horizon": "Tactical",
        "philosophy": "Markets can overshoot; use macro reflexivity, trend shifts, and liquidity conditions to position before consensus catches up.",
        "likes": ["macro inflection", "currency/rate sensitivity", "momentum", "hedges"],
        "avoids": ["static buy-and-hold assumptions", "fragile consensus trades"],
        "weights": {"quality": .14, "value": .12, "growth": .20, "momentum": .34, "stability": .20},
        "sector_bias": {"Technology": 5, "Financial Services": 4, "Energy": 4, "Basic Materials": 4},
        "universe": ["SPY","QQQ","GLD","TLT","USO","XLE","XLF","NVDA","MSFT","META","JPM","BABA","TSM","EEM","FXI","UUP"],
        "cash_base": 12, "concentration": "Tactical macro basket"
    },
    "Joel Greenblatt": {
        "style": "Magic formula quality value", "risk": "Moderate", "horizon": "1-3 years",
        "philosophy": "Buy good companies at good prices using disciplined ranking of quality and value rather than narratives.",
        "likes": ["earnings yield", "return on capital", "free cash flow", "valuation discipline"],
        "avoids": ["expensive low-return businesses", "story-driven speculation"],
        "weights": {"quality": .36, "value": .36, "growth": .10, "momentum": .06, "stability": .12},
        "sector_bias": {"Technology": 3, "Healthcare": 3, "Consumer Defensive": 3, "Industrials": 3},
        "universe": ["MSFT","GOOGL","META","AAPL","V","MA","COST","UNH","LLY","JNJ","ADBE","ORCL","TXN","QCOM","AMGN","GILD","SPY"],
        "cash_base": 8, "concentration": "Ranked quality-value basket"
    },
    "Howard Marks": {
        "style": "Cycle-aware risk control", "risk": "Low-Moderate", "horizon": "Cycle-aware",
        "philosophy": "Avoid permanent loss, respect credit cycles, become aggressive only when risk compensation is unusually attractive.",
        "likes": ["margin of safety", "credit discipline", "defensive cash flow", "contrarian value"],
        "avoids": ["euphoric pricing", "excess leverage", "late-cycle risk"],
        "weights": {"quality": .25, "value": .27, "growth": .06, "momentum": .04, "stability": .38},
        "sector_bias": {"Consumer Defensive": 5, "Healthcare": 5, "Utilities": 4, "Financial Services": 3, "Energy": 2},
        "universe": ["SHY","IEF","TLT","TIP","BRK-B","JNJ","PG","KO","WMT","XOM","CVX","JPM","VZ","XLV","XLP","SPY"],
        "cash_base": 22, "concentration": "Defensive and cycle-aware"
    },
    "Bill Ackman": {
        "style": "Concentrated quality activist", "risk": "Moderate-High", "horizon": "Multi-year",
        "philosophy": "Own a small set of simple, dominant businesses where strategic, management, or capital-allocation changes can unlock value.",
        "likes": ["simple businesses", "pricing power", "activist catalyst", "dominant brands"],
        "avoids": ["complex financial engineering", "weak governance", "low-quality cyclicals"],
        "weights": {"quality": .32, "value": .20, "growth": .18, "momentum": .10, "stability": .20},
        "sector_bias": {"Consumer Cyclical": 5, "Consumer Defensive": 5, "Communication Services": 4, "Technology": 3},
        "universe": ["CMG","QSR","HLT","GOOGL","CP","LOW","HD","MCD","SBUX","COST","MSFT","BRK-B","SPY","V","MA"],
        "cash_base": 8, "concentration": "Very concentrated quality/catalyst"
    },
    "John Templeton": {
        "style": "Global contrarian value", "risk": "Moderate", "horizon": "3-7 years",
        "philosophy": "Search globally for pessimism-priced assets with long-term recovery potential and avoid home-country bias.",
        "likes": ["global diversification", "contrarian value", "emerging markets", "low expectations"],
        "avoids": ["overcrowded consensus", "one-country concentration"],
        "weights": {"quality": .18, "value": .34, "growth": .12, "momentum": .08, "stability": .28},
        "sector_bias": {"Financial Services": 4, "Energy": 4, "Basic Materials": 4, "Technology": 3, "Consumer Defensive": 3},
        "universe": ["EEM","FXI","BABA","PDD","TSM","ASML","NVO","SAP","SHEL","BP","RIO","BHP","HSBC","TM","SONY","MELI","VALE","SPY"],
        "cash_base": 12, "concentration": "Global contrarian basket"
    },
}

OPEN_SOURCE_MODEL_BLEND = {
    "agent_debate": {"description": "Multi-agent investment debate pattern: bull, bear, risk, and macro lenses vote before allocation.", "weight": .35},
    "value_checklist": {"description": "Legendary-investor checklist pattern: quality, valuation, risk, and behavior filters.", "weight": .30},
    "quant_factor": {"description": "Portfolio factor model: value, quality, growth, momentum, and stability normalized into one score.", "weight": .35},
}

INVESTOR_DEFAULT_UNIVERSE = sorted(set(sum([v["universe"] for v in INVESTOR_PROFILES.values()], [])))


def _safe_pct_return(close, days):
    try:
        c = pd.Series(close).dropna()
        if len(c) <= days:
            return 0.0
        return float(c.iloc[-1] / c.iloc[-days-1] - 1) * 100
    except Exception:
        return 0.0


def _max_drawdown_pct(close):
    try:
        c = pd.Series(close).dropna().astype(float)
        if len(c) < 3:
            return 0.0
        cum = c / c.iloc[0]
        dd = cum / cum.cummax() - 1
        return float(dd.min() * 100)
    except Exception:
        return 0.0


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market_regime_for_investor(refresh_token=0):
    symbols = ["SPY", "QQQ", "IWM", "TLT", "GLD", "USO", "^VIX"]
    rows = {}

    def _fetch_sym(sym):
        try:
            h = _fmp_ticker(sym).history(period="1y", auto_adjust=True)
            if h is None or h.empty or "Close" not in h:
                return sym, None
            close = h["Close"].dropna()
            ma50  = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else float(close.iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else ma50
            return sym, {
                "last":      float(close.iloc[-1]),
                "ret_1m":    _safe_pct_return(close, 21),
                "ret_3m":    _safe_pct_return(close, 63),
                "above_50":  float(close.iloc[-1] > ma50),
                "above_200": float(close.iloc[-1] > ma200),
            }
        except Exception:
            return sym, None

    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        for sym, result in ex.map(_fetch_sym, symbols):
            if result is not None:
                rows[sym] = result
    spy = rows.get("SPY", {}); qqq = rows.get("QQQ", {}); iwm = rows.get("IWM", {})
    vix = rows.get("^VIX", {}).get("last", 20)
    risk_on = 50
    risk_on += 12 if spy.get("above_50") else -10
    risk_on += 10 if spy.get("above_200") else -12
    risk_on += 8 if qqq.get("above_50") else -6
    risk_on += 6 if iwm.get("above_50") else -5
    risk_on += min(max(spy.get("ret_3m", 0), -12), 18) * 0.9
    risk_on += min(max(qqq.get("ret_3m", 0), -15), 24) * 0.6
    risk_on -= max(vix - 18, 0) * 1.2
    risk_on += max(16 - vix, 0) * 0.6
    risk_on = clamp(risk_on)
    if risk_on >= 68:
        label = "Risk-on / growth-friendly"
    elif risk_on <= 38:
        label = "Risk-off / defensive"
    else:
        label = "Mixed / selective"
    return {"risk_on": risk_on, "label": label, "assets": rows, "vix": round(float(vix), 1)}



@st.cache_data(ttl=1800, show_spinner=False)
def fetch_investor_universe_data(tickers_tuple, refresh_token=0):
    _CASH = {"CASH", "CASH / T-BILLS"}
    ETF_SET = {"SPY","QQQ","GLD","TLT","IEF","SHY","TIP","USO","DBC","EEM","FXI","XLE","XLF","XLV","XLP","ARKK","UUP"}

    def _fetch_one(t):
        if str(t).upper() in _CASH:
            return None
        try:
            tk   = _fmp_ticker(t)
            info = tk.info or {}
            hist = tk.history(period="1y", auto_adjust=True)
            if hist is None or hist.empty or "Close" not in hist:
                return None
            hist_ta = calc_ta(hist)
            close   = hist["Close"].dropna()
            last_ta = hist_ta.iloc[-1] if len(hist_ta) else pd.Series(dtype=float)
            ret     = close.pct_change().dropna()
            vol     = float(ret.std() * np.sqrt(252) * 100) if len(ret) > 2 else 0.0
            tu = str(t).upper()
            return {
                "Ticker":           tu,
                "Company / Asset":  info.get("shortName") or info.get("longName") or tu,
                "Sector":           info.get("sector") or ("ETF / Macro" if info.get("quoteType") == "ETF" or tu in ETF_SET else "Unknown"),
                "Industry":         info.get("industry") or "—",
                "Country":          info.get("country") or "Global/ETF",
                "Market Cap":       safe_float(info.get("marketCap"), 0),
                "Price":            float(close.iloc[-1]),
                "P/E":              safe_float(info.get("trailingPE"), 0),
                "Forward P/E":      safe_float(info.get("forwardPE"), 0),
                "P/S":              safe_float(info.get("priceToSalesTrailing12Months"), 0),
                "PEG":              safe_float(info.get("pegRatio"), 0),
                "Revenue Growth":   safe_float(info.get("revenueGrowth"), 0) * 100,
                "Earnings Growth":  safe_float(info.get("earningsGrowth"), 0) * 100,
                "Net Margin":       safe_float(info.get("profitMargins"), 0) * 100,
                "ROE":              safe_float(info.get("returnOnEquity"), 0) * 100,
                "Debt/Equity":      safe_float(info.get("debtToEquity"), 0) / 100,
                "Dividend Yield":   safe_float(info.get("dividendYield"), 0) * 100,
                "Beta":             safe_float(info.get("beta"), 1),
                "1M Return":        _safe_pct_return(close, 21),
                "3M Return":        _safe_pct_return(close, 63),
                "6M Return":        _safe_pct_return(close, 126),
                "1Y Return":        _safe_pct_return(close, 252),
                "Volatility":       vol,
                "Max Drawdown":     _max_drawdown_pct(close),
                "RSI":              safe_float(last_ta.get("RSI"), 50),
                "Above MA50":       bool(safe_float(last_ta.get("MA50"), 0) and float(close.iloc[-1]) > safe_float(last_ta.get("MA50"), 0)),
                "Above MA200":      bool(safe_float(last_ta.get("MA200"), 0) and float(close.iloc[-1]) > safe_float(last_ta.get("MA200"), 0)),
            }
        except Exception:
            return None

    equity_tickers = [t for t in tickers_tuple if str(t).upper() not in _CASH]
    with ThreadPoolExecutor(max_workers=min(len(equity_tickers), 8)) as ex:
        results = list(ex.map(_fetch_one, equity_tickers))
    return pd.DataFrame([r for r in results if r is not None])

# ══════════════════════════════════════════════════════════════════
#  INVESTOR VIEW — ENHANCED SCORING & BACKTEST ENGINE v2
# ══════════════════════════════════════════════════════════════════

# ── Factor scoring: value ────────────────────────────────────────
def _score_value(row):
    """Multi-metric value score: P/E, Forward P/E, P/S, PEG, P/B, EV/EBITDA, dividend."""
    pe      = row.get("P/E", 0)
    fpe     = row.get("Forward P/E", 0)
    ps      = row.get("P/S", 0)
    peg     = row.get("PEG", 0)
    pb      = row.get("P/B", 0)
    ev_eb   = row.get("EV/EBITDA", 0)
    div     = row.get("Dividend Yield", 0)

    score = 50

    # P/E — tiered with negative earnings penalty
    if   pe > 0 and pe < 10:   score += 20
    elif pe > 0 and pe < 15:   score += 14
    elif pe > 0 and pe < 22:   score += 8
    elif pe > 0 and pe < 35:   score += 1
    elif pe > 0 and pe < 55:   score -= 8
    elif pe > 0:               score -= 16
    elif pe < 0:               score -= 10   # negative earnings
    else:                      score -= 4    # missing

    # Forward P/E direction (earnings trend proxy)
    if fpe > 0 and pe > 0:
        ratio = fpe / pe
        if   ratio < 0.80:  score += 12   # strong earnings acceleration
        elif ratio < 0.92:  score += 7
        elif ratio < 1.05:  score += 2
        elif ratio < 1.20:  score -= 4
        else:               score -= 9

    # P/S ratio
    if   ps > 0 and ps < 1.0:   score += 14
    elif ps > 0 and ps < 2.5:   score += 8
    elif ps > 0 and ps < 5.0:   score += 3
    elif ps > 0 and ps < 10:    score -= 4
    elif ps > 0 and ps < 20:    score -= 10
    elif ps > 0:                score -= 16

    # PEG ratio (value + growth combined)
    if   peg > 0 and peg < 0.8:  score += 16
    elif peg > 0 and peg < 1.2:  score += 10
    elif peg > 0 and peg < 2.0:  score += 3
    elif peg > 0 and peg < 3.5:  score -= 6
    elif peg > 0:                score -= 13

    # Price-to-Book
    if   pb > 0 and pb < 1.0:   score += 9
    elif pb > 0 and pb < 2.0:   score += 5
    elif pb > 0 and pb < 4.0:   score += 1
    elif pb > 0 and pb < 8.0:   score -= 4
    elif pb > 0:                score -= 8

    # EV/EBITDA (enterprise-level valuation)
    if   ev_eb > 0 and ev_eb < 6:    score += 12
    elif ev_eb > 0 and ev_eb < 10:   score += 7
    elif ev_eb > 0 and ev_eb < 16:   score += 2
    elif ev_eb > 0 and ev_eb < 25:   score -= 5
    elif ev_eb > 0 and ev_eb < 40:   score -= 10
    elif ev_eb > 0:                  score -= 16

    # Dividend yield bonus (income + financial discipline signal)
    if div > 0:
        score += min(div * 1.2, 7)

    return clamp(score)


# ── Factor scoring: quality ──────────────────────────────────────
def _score_quality(row):
    """Quality score: margins, ROE, leverage, earnings quality, liquidity."""
    margin      = row.get("Net Margin", 0)
    roe         = row.get("ROE", 0)
    debt        = row.get("Debt/Equity", 0)
    rev_growth  = row.get("Revenue Growth", 0)
    earn_growth = row.get("Earnings Growth", 0)

    score = 50

    # Net margin: strong positive slope, heavy penalty for negative
    if   margin > 25:   score += 22
    elif margin > 15:   score += 14
    elif margin > 8:    score += 7
    elif margin > 3:    score += 2
    elif margin > 0:    score -= 2
    elif margin > -8:   score -= 12
    else:               score -= 20

    # ROE: 20%+ is exceptional (Buffett threshold)
    if   roe > 25:   score += 16
    elif roe > 15:   score += 10
    elif roe > 8:    score += 4
    elif roe > 0:    score += 0
    elif roe > -10:  score -= 8
    else:            score -= 16

    # Debt/Equity: fortress balance sheet vs overleveraged
    if   debt < 0.20:  score += 14
    elif debt < 0.50:  score += 9
    elif debt < 1.0:   score += 3
    elif debt < 2.0:   score -= 5
    elif debt < 4.0:   score -= 13
    else:              score -= 20

    # Earnings quality: earnings growing faster than revenue can be artificially inflated
    if rev_growth > 0 and earn_growth > 0:
        ratio = earn_growth / max(rev_growth, 0.5)
        if   ratio > 0 and ratio < 2.0:  score += 6   # healthy margin expansion
        elif ratio >= 2.0 and ratio < 4: score += 2   # ok but watch
        elif ratio >= 4.0:               score -= 5   # potential earnings quality concern

    # Revenue growth consistency (quality companies have durable growth)
    if   rev_growth > 20:  score += 9
    elif rev_growth > 10:  score += 5
    elif rev_growth > 5:   score += 2
    elif rev_growth < -8:  score -= 10
    elif rev_growth < 0:   score -= 4

    return clamp(score)


# ── Factor scoring: growth ───────────────────────────────────────
def _score_growth(row):
    """Growth score: revenue & earnings acceleration, margin expansion."""
    rev  = row.get("Revenue Growth", 0)
    earn = row.get("Earnings Growth", 0)
    net_margin = row.get("Net Margin", 0)
    roe  = row.get("ROE", 0)

    score = 45

    # Revenue growth — most reliable growth metric
    if   rev > 35:  score += 28
    elif rev > 20:  score += 20
    elif rev > 12:  score += 13
    elif rev > 6:   score += 7
    elif rev > 0:   score += 2
    elif rev > -8:  score -= 8
    else:           score -= 18

    # Earnings growth — add-on but clip for cash flow quality
    if   earn > 40:  score += 14
    elif earn > 20:  score += 9
    elif earn > 10:  score += 4
    elif earn > 0:   score += 1
    elif earn < -15: score -= 10
    elif earn < 0:   score -= 4

    # High-quality growth: strong revenue + positive margins (not just burn)
    if rev > 20 and net_margin > 8:   score += 9
    if rev > 10 and roe > 15:          score += 5

    # Profitless growth penalty (growth-at-any-cost risk)
    if rev > 20 and net_margin < -5:  score -= 8

    return clamp(score)


# ── Factor scoring: momentum ─────────────────────────────────────
def _score_momentum(row):
    """Momentum: skip-month risk-adjusted momentum, MA filters, RSI regime."""
    ret_1m  = row.get("1M Return", 0)
    ret_3m  = row.get("3M Return", 0)
    ret_6m  = row.get("6M Return", 0)
    ret_12m = row.get("1Y Return", 0)
    above50 = row.get("Above MA50", False)
    above200= row.get("Above MA200", False)
    rsi     = row.get("RSI", 50)
    vol     = max(row.get("Volatility", 30), 5)

    score = 45

    # Skip-month momentum (remove 1M reversal; academic standard since Jegadeesh-Titman)
    skip_mom = ret_12m - ret_1m if ret_12m != 0 else ret_6m
    score += min(max(skip_mom, -35), 45) * 0.25

    # 3M momentum — strongest predictor in cross-section
    score += min(max(ret_3m, -20), 35) * 0.72

    # 6M momentum — medium-term continuation
    score += min(max(ret_6m, -30), 55) * 0.32

    # Risk-adjusted 3M momentum (Sharpe-like: return per unit of vol)
    risk_adj = ret_3m / vol * 30
    score += min(max(risk_adj, -10), 14) * 0.45

    # Moving average filters (trend regime)
    score += 8 if above50  else -7
    score += 9 if above200 else -8

    # RSI regime filter (avoid extreme overbought, penalize oversold)
    if   45 <= rsi <= 68:  score += 6   # healthy momentum range
    elif rsi > 80:         score -= 12  # overbought reversal risk
    elif rsi > 72:         score -= 4
    elif rsi < 28:         score -= 14  # extreme oversold
    elif rsi < 38:         score -= 6

    return clamp(score)


# ── Factor scoring: stability ────────────────────────────────────
def _score_stability(row):
    """Stability: beta, volatility, drawdown depth, dividend yield."""
    beta  = row.get("Beta", 1.0)
    vol   = row.get("Volatility", 30)
    dd    = abs(row.get("Max Drawdown", 25))
    div   = row.get("Dividend Yield", 0)
    debt  = row.get("Debt/Equity", 1.0)

    score = 70

    # Beta: penalty for market amplification, bonus for low-beta
    if   beta < 0.4:  score += 10
    elif beta < 0.7:  score += 6
    elif beta < 0.9:  score += 2
    elif beta < 1.1:  score += 0
    elif beta < 1.4:  score -= 8
    elif beta < 1.8:  score -= 16
    else:             score -= 24

    # Volatility: penalise excess vol above 25%
    score -= max(vol - 22, 0) * 0.80

    # Max drawdown depth
    if   dd < 15:   score += 8
    elif dd < 25:   score += 3
    elif dd < 35:   score -= 5
    elif dd < 50:   score -= 12
    else:           score -= 20

    # Dividend yield: proxy for financial stability & cash flow discipline
    score += min(div * 2.0, 8)

    # Overleveraged companies are fragile in downturns
    if debt > 3.0: score -= 10
    if debt > 5.0: score -= 10  # stacking

    return clamp(score)


# ── Factor aggregation ───────────────────────────────────────────
def investor_factor_scores(row):
    return {
        "quality":   _score_quality(row),
        "value":     _score_value(row),
        "growth":    _score_growth(row),
        "momentum":  _score_momentum(row),
        "stability": _score_stability(row),
    }


# ── Per-row investor score with macro overlay ────────────────────
def investor_score_row(row, profile, regime, stance="Balanced", news_shock=0):
    factors = investor_factor_scores(row)
    w = profile["weights"]
    base = sum(factors[k] * w.get(k, 0) for k in factors)
    sector = row.get("Sector", "Unknown")
    sector_bonus = profile.get("sector_bias", {}).get(sector, 0)
    risk_on = regime.get("risk_on", 50)

    # Macro overlay: growth/momentum styles benefit from risk-on regimes
    growth_exposure    = w.get("growth", 0) + w.get("momentum", 0)
    defensive_exposure = w.get("stability", 0) + w.get("value", 0) * 0.45
    macro_adj = (risk_on - 50) * (growth_exposure - defensive_exposure) * 0.44

    # Stance amplifier
    if   stance == "Aggressive": macro_adj += 5 + (risk_on - 50) * 0.06
    elif stance == "Defensive":  macro_adj -= 4 + max(50 - risk_on, 0) * 0.04

    # VIX/vol regime penalty for high-beta picks in risk-off
    vix_level = regime.get("vix", 20)
    if vix_level > 28:
        high_beta_penalty = max(row.get("Beta", 1.0) - 1.0, 0) * (vix_level - 28) * 0.35
        macro_adj -= high_beta_penalty

    score = base + sector_bonus + macro_adj + news_shock
    return clamp(score), factors, macro_adj + sector_bonus + news_shock


# ── News shock layer ─────────────────────────────────────────────
def investor_news_shock_for_row(row, news_items):
    if not news_items:
        return 0
    text = (row.get("Ticker", "") + " " + row.get("Company / Asset", "") + " " +
            row.get("Sector", "") + " " + row.get("Industry", "")).lower()
    score = 0
    for n in news_items[:18]:
        nt = " ".join([
            str(n.get("title", "")), str(n.get("summary", "")),
            " ".join(n.get("industry_tags", [])),
            " ".join(n.get("impact", {}).get("good_for", [])),
            " ".join(n.get("impact", {}).get("bad_for", [])),
            " ".join(n.get("impact", {}).get("companies", [])),
        ]).lower()
        importance = safe_float(n.get("importance"), 50)
        if (row.get("Ticker", "").lower() in nt or
                row.get("Sector", "").lower() in nt or
                any(x in nt for x in text.split()[:3] if len(x) > 4)):
            direction = 0
            if row.get("Sector", "").lower() in " ".join(n.get("impact", {}).get("good_for", [])).lower():
                direction += 1
            if row.get("Ticker", "").lower() in " ".join(n.get("impact", {}).get("companies", [])).lower():
                direction += 0.7
            if row.get("Sector", "").lower() in " ".join(n.get("impact", {}).get("bad_for", [])).lower():
                direction -= 1
            # Thematic macro shocks
            if any(k in nt for k in ["rate hike", "fed", "inflation", "cpi"]):
                if row.get("Sector") in {"Utilities", "Real Estate"}:   direction -= 0.5
                if row.get("Sector") == "Financial Services":            direction += 0.4
            if any(k in nt for k in ["hormuz", "oil", "middle east", "conflict", "shipping"]):
                if row.get("Sector") == "Energy":                        direction += 1.1
                if row.get("Sector") in {"Consumer Cyclical", "Industrials"}: direction -= 0.5
            if any(k in nt for k in ["ai", "chip", "semiconductor", "nvidia", "data center"]):
                if row.get("Sector") == "Technology":                    direction += 0.7
            score += direction * min(8, importance / 12)
    return max(-10, min(10, score))


# ── Portfolio simulator ──────────────────────────────────────────
def simulate_investor_portfolio(investor_name, stance="Balanced", max_holdings=10,
                                 model_blend=65, use_news=True, refresh_token=0):
    profile = INVESTOR_PROFILES[investor_name]
    tickers = tuple(sorted(set(profile["universe"])))
    regime  = fetch_market_regime_for_investor(refresh_token)
    df      = fetch_investor_universe_data(tickers, refresh_token)

    news_items = []
    if use_news and "fetch_market_news" in globals():
        try:
            news_items = fetch_market_news("", "", refresh_token)[:25]
        except Exception:
            news_items = []

    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), regime, profile, []

    rows = []
    for _, row in df.iterrows():
        rowd = row.to_dict()
        shock = investor_news_shock_for_row(rowd, news_items) if use_news else 0
        style_score, factors, adj = investor_score_row(rowd, profile, regime, stance=stance, news_shock=shock)

        # Generic multi-factor model (open-source ensemble component)
        generic = (0.22 * factors["quality"] + 0.18 * factors["value"] +
                   0.24 * factors["growth"]  + 0.20 * factors["momentum"] +
                   0.16 * factors["stability"])

        final = style_score * (model_blend / 100) + generic * (1 - model_blend / 100)

        # Build transparent reason string
        top_factor = max(factors, key=factors.get)
        reason_bits = [f"{top_factor.title()} {factors[top_factor]:.0f}/100"]
        if adj > 4:   reason_bits.append("macro/style tailwind")
        if adj < -4:  reason_bits.append("macro/style headwind")
        if shock > 2: reason_bits.append("news tailwind")
        if shock < -2:reason_bits.append("news risk")

        # Compute individual risk contribution proxy (vol * beta)
        vol  = rowd.get("Volatility", 25)
        beta = rowd.get("Beta", 1.0)
        risk_score = min(vol * max(beta, 0.3) / 30, 2.0)   # normalised 0-2

        rowd.update({
            "Investor Score": round(final, 1),
            "Style Match":    round(style_score, 1),
            "Quality":        factors["quality"],
            "Value":          factors["value"],
            "Growth":         factors["growth"],
            "Momentum":       factors["momentum"],
            "Stability":      factors["stability"],
            "News Shock":     round(shock, 1),
            "Risk Index":     round(risk_score, 2),
            "Reason":         "; ".join(reason_bits),
        })
        rows.append(rowd)

    scored = (
        pd.DataFrame(rows)
        .sort_values(["Investor Score", "Market Cap"], ascending=[False, False])
        .head(max_holdings)
        .copy()
    )

    # ── Cash target: regime + stance + profile-base ──────────────
    risk_on = regime.get("risk_on", 50)
    cash = float(profile.get("cash_base", 8))
    cash += max(45 - risk_on, 0) * 0.38       # risk-off → more cash
    cash -= max(risk_on - 65, 0) * 0.18       # risk-on  → less cash
    if stance == "Aggressive": cash -= 6
    elif stance == "Defensive": cash += 10
    # VIX spike: emergency cash buffer
    vix = regime.get("vix", 20)
    if vix > 30: cash += (vix - 30) * 0.5
    cash = max(0.0, min(40.0, cash))

    # ── Weight allocation: score-driven with position limits ─────
    raw = np.maximum(scored["Investor Score"].astype(float).to_numpy() - 45, 1.0)
    power = 1.55 if "concentrated" in profile.get("concentration", "").lower() else 1.18
    raw = raw ** power

    equity_budget = 100.0 - cash
    weights_raw = raw / raw.sum() * equity_budget if raw.sum() else np.zeros(len(raw))

    # Position limits: cap any single holding
    max_pos = 35.0 if "concentrated" in profile.get("concentration", "").lower() else 25.0
    min_pos = 1.5
    weights_clipped = np.clip(weights_raw, min_pos, max_pos)
    # Renormalise after clipping
    if weights_clipped.sum() > 0:
        weights_clipped = weights_clipped / weights_clipped.sum() * equity_budget
    weights_clipped = np.round(weights_clipped, 2)

    scored["Weight"] = weights_clipped

    if cash >= 1.0:
        cash_row = {
            "Ticker": "CASH", "Company / Asset": "Cash / T-Bills (3M)",
            "Sector": "Cash / Defense", "Industry": "Liquidity", "Country": "US",
            "Price": 1.0, "Investor Score": 50, "Style Match": 50,
            "Quality": 50, "Value": 50, "Growth": 0, "Momentum": 0,
            "Stability": 92, "News Shock": 0, "Risk Index": 0.05,
            "Reason": f"dry powder & risk control ({stance} stance, risk-on={risk_on:.0f}/100)",
            "Weight": round(cash, 2),
        }
        scored = pd.concat([scored, pd.DataFrame([cash_row])], ignore_index=True)

    sector = (scored
              .groupby("Sector", as_index=False)["Weight"]
              .sum()
              .sort_values("Weight", ascending=False))
    return scored, sector, regime, profile, news_items


# ══════════════════════════════════════════════════════════════════
#  ALLOCATION CHARTS
# ══════════════════════════════════════════════════════════════════

def investor_allocation_fig(port):
    """Donut chart with hover details for portfolio allocation."""
    fig = go.Figure()
    if port is None or port.empty:
        return fig

    # Assign colors: CASH always grey
    palette = ["#00E5FF","#FFB000","#22C55E","#FF4D6D","#A78BFA","#F97316",
               "#3B82F6","#E879F9","#14B8A6","#A3E635","#F43F5E","#38BDF8",
               "#FBBF24","#6EE7B7"]
    colors = []
    for _, r in port.iterrows():
        colors.append("#64748B" if str(r.get("Ticker","")) == "CASH"
                      else palette[len(colors) % len(palette)])

    labels = port["Ticker"].astype(str).tolist()
    names  = port["Company / Asset"].astype(str).tolist() if "Company / Asset" in port.columns else labels
    scores = port["Investor Score"].tolist() if "Investor Score" in port.columns else [50]*len(labels)
    weights = port["Weight"].tolist()

    hover = [
        f"<b>{lbl}</b><br>{nm}<br>Weight: {w:.1f}%<br>Score: {s:.0f}/100"
        for lbl, nm, w, s in zip(labels, names, weights, scores)
    ]

    fig.add_trace(go.Pie(
        labels=labels,
        values=weights,
        hole=0.50,
        textinfo="label+percent",
        textfont=dict(size=11, color="#F8FAFC"),
        marker=dict(colors=colors, line=dict(color="#0d0f14", width=1.6)),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
        pull=[0.04 if str(port.iloc[i].get("Ticker","")) != "CASH" and
              float(port.iloc[i].get("Weight",0)) == port[port["Ticker"]!="CASH"]["Weight"].max()
              else 0 for i in range(len(port))],
        sort=False,
    ))
    # Centre annotation
    total_eq = float(port[port["Ticker"] != "CASH"]["Weight"].sum())
    fig.add_annotation(
        text=f"<b>{total_eq:.0f}%</b><br><span style='font-size:9px'>Equity</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#F8FAFC"),
        xanchor="center", yanchor="middle",
    )
    fig.update_layout(**base_layout(height=390))
    fig.update_layout(margin=dict(l=10, r=10, t=24, b=10), showlegend=False)
    return fig


def investor_sector_fig(sector):
    """Premium horizontal sector bar with gradient colours."""
    fig = go.Figure()
    if sector is None or sector.empty:
        return fig
    data = sector.copy()
    data["Weight"] = pd.to_numeric(data["Weight"], errors="coerce").fillna(0)
    data = data[data["Weight"] > 0].sort_values("Weight", ascending=True)  # ascending for horizontal
    if data.empty:
        return fig

    palette = ["#00E5FF","#FFB000","#FF4D6D","#7C3AED","#22C55E","#F97316",
               "#3B82F6","#E879F9","#14B8A6","#A3E635","#F43F5E","#94A3B8"]
    colors = [palette[i % len(palette)] for i in range(len(data))]

    fig.add_trace(go.Bar(
        y=data["Sector"].astype(str),
        x=data["Weight"],
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="rgba(255,255,255,0.28)", width=0.8),
            opacity=0.92,
        ),
        text=[f"{x:.1f}%" for x in data["Weight"]],
        textposition="outside",
        textfont=dict(color="#F8FAFC", size=11, family="SF Mono, Fira Code, monospace"),
        hovertemplate="<b>%{y}</b><br>Weight: %{x:.1f}%<extra></extra>",
        cliponaxis=False,
    ))

    xmax = max(float(data["Weight"].max()) * 1.28, 12)
    fig.update_layout(**base_layout(height=390))
    fig.update_layout(
        plot_bgcolor="#08111F", paper_bgcolor="#08111F",
        bargap=0.30, margin=dict(l=10, r=70, t=32, b=14),
        showlegend=False,
        title=dict(text="Sector Allocation", font=dict(size=12, color="#E2E8F0"), x=0.01, y=0.99),
        xaxis=dict(
            ticksuffix="%", range=[0, xmax], showgrid=True,
            gridcolor="rgba(148,163,184,0.12)", zeroline=True,
            zerolinecolor="rgba(248,250,252,0.28)", tickfont=dict(color="#94A3B8", size=10),
        ),
        yaxis=dict(
            showgrid=False, tickfont=dict(color="#CBD5E1", size=10),
            automargin=True,
        ),
        hoverlabel=dict(bgcolor="#111827", bordercolor="#38BDF8",
                        font=dict(color="#F8FAFC", size=12, family="monospace")),
    )
    return fig


def investor_factor_radar_fig(port, profile):
    """Radar / spider chart of weighted-average factor exposures vs style weights."""
    if port is None or port.empty:
        return go.Figure()

    cats = ["Quality","Value","Growth","Momentum","Stability"]
    # Weighted average of each factor across equity holdings
    port_eq = port[port["Ticker"] != "CASH"].copy()
    wsum = port_eq["Weight"].astype(float).sum()

    port_vals = []
    for c in cats:
        if c in port_eq.columns and wsum > 0:
            v = float((port_eq[c].astype(float) * port_eq["Weight"].astype(float)).sum() / wsum)
        else:
            v = 50.0
        port_vals.append(v)

    # Investor style target (profile weights → scaled to 0-100)
    w = profile.get("weights", {})
    max_w = max(w.values()) if w else 1
    style_vals = [w.get(c.lower(), 0) / max_w * 100 for c in cats]

    fig = go.Figure()
    cats_closed = cats + [cats[0]]
    port_closed  = port_vals + [port_vals[0]]
    style_closed = style_vals + [style_vals[0]]

    fig.add_trace(go.Scatterpolar(
        r=port_closed, theta=cats_closed, fill="toself", name="Portfolio Factors",
        fillcolor="rgba(59,130,246,0.18)", line=dict(color="#3B82F6", width=2.5),
    ))
    fig.add_trace(go.Scatterpolar(
        r=style_closed, theta=cats_closed, fill="toself", name="Investor Style Target",
        fillcolor="rgba(245,158,11,0.12)", line=dict(color="#F59E0B", width=2.0, dash="dot"),
    ))
    fig.update_layout(**base_layout(height=390))
    fig.update_layout(
        polar=dict(
            bgcolor="#08111F",
            radialaxis=dict(visible=True, range=[0,100], tickfont=dict(size=9, color="#64748B"),
                            gridcolor="rgba(148,163,184,0.15)", linecolor="rgba(148,163,184,0.20)"),
            angularaxis=dict(tickfont=dict(size=11, color="#CBD5E1"),
                             linecolor="rgba(148,163,184,0.25)"),
        ),
        showlegend=True,
        legend=dict(
            orientation="h", y=-0.10, x=0.5, xanchor="center", yanchor="top",
            font=dict(size=11, color="#CBD5E1"),
            bgcolor="rgba(8,17,31,0.85)",
            bordercolor="rgba(59,130,246,0.30)",
            borderwidth=1,
            itemsizing="constant",
            tracegroupgap=0,
        ),
        margin=dict(l=40, r=40, t=36, b=90),
    )
    return fig


# ══════════════════════════════════════════════════════════════════
#  AI PORTFOLIO EXPLANATION
# ══════════════════════════════════════════════════════════════════

def _investor_weighted_avg(port, col):
    try:
        d = port[(port["Ticker"] != "CASH") & port[col].notna()].copy()
        if d.empty: return 0.0
        w = d["Weight"].astype(float)
        return float((d[col].astype(float) * w).sum() / w.sum()) if w.sum() > 0 else float(d[col].astype(float).mean())
    except Exception:
        return 0.0


def investor_ai_portfolio_explanation(name, profile, regime, port, stance="Balanced", model_blend=70, use_news=True, news_used=None):
    news_used = news_used or []
    if port is None or port.empty:
        return "Portfolio explanation unavailable", "The model could not fetch enough data to explain this simulated allocation."

    eq = port[port["Ticker"] != "CASH"]
    top_names  = ", ".join(eq.head(3)["Ticker"].astype(str).tolist()) if not eq.empty else "—"
    top_sector = port.groupby("Sector")["Weight"].sum().idxmax() if not port.empty else "—"
    sector_weight = float(port.groupby("Sector")["Weight"].sum().max()) if not port.empty else 0
    cash_weight   = float(port[port["Ticker"]=="CASH"]["Weight"].sum()) if "Ticker" in port.columns else 0
    risk_on = regime.get("risk_on", 50)

    avg_quality   = _investor_weighted_avg(port, "Quality")
    avg_value     = _investor_weighted_avg(port, "Value")
    avg_growth    = _investor_weighted_avg(port, "Growth")
    avg_momentum  = _investor_weighted_avg(port, "Momentum")
    avg_stability = _investor_weighted_avg(port, "Stability")
    avg_score     = _investor_weighted_avg(port, "Investor Score")

    _factor_avgs = {"quality": avg_quality, "value": avg_value,
                    "growth": avg_growth, "momentum": avg_momentum,
                    "stability": avg_stability}
    leading = max(_factor_avgs, key=_factor_avgs.get)

    news_sentence = ""
    if use_news and news_used:
        top = news_used[0].get("ai_headline", news_used[0].get("title",""))
        news_sentence = f" Active news shock layer detected theme: '{top[:80]}...' influencing sector tilts."

    headline = f"{name}-style {leading} tilt: {top_names} lead the simulated portfolio"
    paragraph = (
        f"The simulated {name} portfolio allocates mainly to {top_names}, with the largest sector tilt in "
        f"{top_sector} ({sector_weight:.1f}% of total allocation) and {cash_weight:.1f}% in cash/defense. "
        f"The model selected this mix because the {name} framework emphasises "
        f"{profile.get('concentration','diversified allocation')}. "
        f"Current market regime: {regime.get('label','—')} (risk-on score {risk_on:.0f}/100), "
        f"model blend {model_blend}% investor style vs {100-model_blend}% generic multi-factor. "
        f"Weighted portfolio factor scores: quality {avg_quality:.0f}/100, value {avg_value:.0f}/100, "
        f"growth {avg_growth:.0f}/100, momentum {avg_momentum:.0f}/100, stability {avg_stability:.0f}/100 "
        f"→ composite investor score {avg_score:.1f}/100.{news_sentence} "
        f"This is an AI-style educational simulation of the investor's documented framework, "
        f"not a claim about real holdings or private opinion."
    )
    return headline, paragraph


def render_investor_ai_explanation(name, profile, regime, port, stance="Balanced", model_blend=70, use_news=True, news_used=None):
    headline, paragraph = investor_ai_portfolio_explanation(name, profile, regime, port, stance, model_blend, use_news, news_used)
    st.markdown(f"""
    <div class="investor-ai-box">
      <div class="investor-ai-kicker">{html.escape(tr('AI portfolio explanation'))}</div>
      <div class="investor-ai-headline">{html.escape(headline)}</div>
      <div class="investor-ai-body">{html.escape(paragraph)}</div>
    </div>""", unsafe_allow_html=True)


def render_investor_card(name, profile, regime, port):
    top_txt = ", ".join(port[port["Ticker"]!="CASH"].head(3)["Ticker"].astype(str).tolist()) if port is not None and not port.empty else "—"
    st.markdown(f"""
    <div class="investor-card">
      <div class="investor-title">{html.escape(name)} · {html.escape(profile.get('style',''))}</div>
      <div class="investor-subtitle">{html.escape(profile.get('philosophy',''))}</div>
      <div class="investor-pill-row">
        <span class="investor-pill">Horizon: {html.escape(profile.get('horizon','—'))}</span>
        <span class="investor-pill">Risk: {html.escape(profile.get('risk','—'))}</span>
        <span class="investor-pill">Regime: {html.escape(regime.get('label','—'))}</span>
        <span class="investor-pill">Top ideas: {html.escape(top_txt)}</span>
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  BACKTEST ENGINE — ENHANCED
# ══════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_investor_backtest_prices(tickers_tuple, period="1y", refresh_token=0):
    """Fetch adjusted historical prices for Investor View backtests."""
    frames = []
    custom_years = None
    period_str = str(period).lower().strip()
    m = re.fullmatch(r"(\d+)y", period_str)
    if m and int(m.group(1)) not in {1, 2, 5, 10}:
        custom_years = int(m.group(1))
        yf_period = "max"
    else:
        yf_period = period

    cutoff = None
    if custom_years:
        cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(years=custom_years)

    for raw_ticker in tickers_tuple:
        t = str(raw_ticker).upper().strip()
        if not t or t in {"CASH", "CASH / T-BILLS", "CASH / T-BILLS (3M)"}:
            continue
        try:
            h = _fmp_ticker(t).history(period=yf_period, auto_adjust=True)
            if h is None or h.empty or "Close" not in h.columns:
                continue
            close = pd.to_numeric(h["Close"], errors="coerce").dropna().rename(t)
            if isinstance(close.index, pd.DatetimeIndex):
                close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
            if cutoff is not None:
                close = close[close.index >= cutoff]
            if close.empty:
                continue
            frames.append(close)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    prices = pd.concat(frames, axis=1).sort_index().ffill().dropna(how="all")
    return prices


def _portfolio_cash_daily_return(annual_cash_rate=0.045):
    try:
        return (1 + float(annual_cash_rate)) ** (1/252) - 1
    except Exception:
        return 0.0


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_spy_benchmark(period="1y", refresh_token=0):
    """Fetch SPY as benchmark for the backtest. Always shown."""
    try:
        period_str = str(period).lower().strip()
        m = re.fullmatch(r"(\d+)y", period_str)
        if m and int(m.group(1)) not in {1,2,5,10}:
            yf_p = "max"
            cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(years=int(m.group(1)))
        else:
            yf_p = period
            cutoff = None
        h = _fmp_ticker("SPY").history(period=yf_p, auto_adjust=True)
        if h is None or h.empty or "Close" not in h.columns:
            return pd.Series(dtype=float)
        close = pd.to_numeric(h["Close"], errors="coerce").dropna()
        if isinstance(close.index, pd.DatetimeIndex):
            close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
        if cutoff is not None:
            close = close[close.index >= cutoff]
        return close.rename("SPY")
    except Exception:
        return pd.Series(dtype=float)


def investor_backtest_from_portfolio(port, period="1y", refresh_token=0, rebalance="Monthly"):
    """
    Enhanced backtest engine:
    - Monthly rebalancing actually rebalances on month-end dates
    - Buy-and-hold lets weights drift naturally
    - Computes comprehensive risk metrics vs SPY benchmark
    """
    empty = {"metrics": {}, "curve": pd.Series(dtype=float),
             "drawdown": pd.Series(dtype=float),
             "daily_returns": pd.Series(dtype=float),
             "monthly_returns": pd.Series(dtype=float),
             "weights": pd.Series(dtype=float),
             "contribution": pd.DataFrame()}

    if port is None or port.empty or "Ticker" not in port or "Weight" not in port:
        return empty

    clean_port = port.copy()
    clean_port["Ticker"] = clean_port["Ticker"].astype(str).str.upper().str.strip()
    clean_port["Weight"] = pd.to_numeric(clean_port["Weight"], errors="coerce").fillna(0.0)
    weights = clean_port.set_index("Ticker")["Weight"] / 100.0
    cash_tickers = {"CASH","CASH / T-BILLS","CASH / T-BILLS (3M)"}
    cash_w = float(weights[weights.index.isin(cash_tickers)].sum())
    equity_weights = weights[~weights.index.isin(cash_tickers)]
    equity_weights = equity_weights[equity_weights > 0]

    prices = fetch_investor_backtest_prices(tuple(equity_weights.index), period, refresh_token)
    if prices.empty:
        return {**empty, "weights": weights}

    available = [t for t in equity_weights.index if t in prices.columns]
    if not available:
        return {**empty, "weights": weights}

    eq_w = equity_weights.loc[available].astype(float)
    missing_equity_w = float(equity_weights.sum() - eq_w.sum())
    cash_w = max(0.0, cash_w + missing_equity_w)

    returns = prices[available].pct_change().dropna(how="all").fillna(0.0)
    if returns.empty:
        return {**empty, "weights": weights}

    eq_w = eq_w / max(eq_w.sum(), 1e-12) * max(0.0, 1.0 - cash_w)
    cash_daily = _portfolio_cash_daily_return()

    # ── Simulate portfolio curve ─────────────────────────────────
    if rebalance == "Buy & Hold":
        norm_prices = prices[available].loc[returns.index] / prices[available].loc[returns.index].iloc[0]
        equity_curve = (norm_prices * eq_w).sum(axis=1)
        cash_curve   = cash_w * ((1 + cash_daily) ** np.arange(len(equity_curve)))
        curve = (equity_curve + cash_curve).rename("Portfolio")
        daily = curve.pct_change().dropna()

        # Per-holding contribution (buy & hold drift)
        holding_vals = norm_prices * eq_w
        contribution_return = (holding_vals.iloc[-1] - holding_vals.iloc[0]) / 1.0 * 100
    else:
        # Monthly rebalancing: reset weights to target on month-end dates
        month_ends = pd.date_range(returns.index[0], returns.index[-1], freq="BME")
        rebal_dates = set(d.normalize() for d in month_ends)

        port_value = pd.Series(index=returns.index, dtype=float)
        # Track each holding's dollar value so weights drift naturally between rebalancing dates.
        holding_values = eq_w.copy().astype(float)   # equity; sums to (1 - cash_w)
        cash_value = float(cash_w)                   # cash portion

        for i, date in enumerate(returns.index):
            day_ret = returns.loc[date]
            # Drift: update each holding by its own daily return
            holding_values = holding_values * (1.0 + day_ret.reindex(holding_values.index).fillna(0.0))
            cash_value *= (1.0 + cash_daily)
            total_val = float(holding_values.sum()) + cash_value
            port_value.iloc[i] = total_val
            # Rebalance at month-end: reset each holding to its target weight
            if i > 0 and date.normalize() in rebal_dates:
                holding_values = eq_w.copy().astype(float) * total_val
                cash_value = float(cash_w) * total_val

        curve = port_value.rename("Portfolio")

        # Per-holding contribution (weighted return over full period)
        holding_total = prices[available].iloc[-1] / prices[available].iloc[0] - 1
        contribution_return = holding_total * eq_w * 100

    curve = curve.dropna()
    daily = curve.pct_change().fillna(0.0)

    # ── Fetch SPY for relative metrics ──────────────────────────
    spy = _fetch_spy_benchmark(period, refresh_token)
    spy_daily = pd.Series(dtype=float)
    spy_curve  = pd.Series(dtype=float)
    if not spy.empty:
        spy_aligned = spy.reindex(curve.index, method="ffill").dropna()
        spy_curve = spy_aligned / spy_aligned.iloc[0]
        spy_daily = spy_curve.pct_change().fillna(0.0)

    # ── Core metrics ─────────────────────────────────────────────
    running_max = curve.cummax()
    drawdown    = (curve / running_max - 1) * 100

    total_return = (float(curve.iloc[-1]) - 1.0) * 100
    years        = max(len(daily) / 252, 1/252)
    ann_return   = ((float(curve.iloc[-1])) ** (1/years) - 1) * 100 if curve.iloc[-1] > 0 else 0.0
    ann_vol      = float(daily.std(ddof=1) * np.sqrt(252) * 100) if len(daily) > 1 else 0.0

    rf_daily = 0.045 / 252
    sharpe   = float((daily.mean() - rf_daily) / daily.std(ddof=1) * np.sqrt(252)) if len(daily)>1 and daily.std(ddof=1) else 0.0
    downside = daily[daily < rf_daily]
    sortino  = float((daily.mean()-rf_daily)/downside.std(ddof=1)*np.sqrt(252)) if len(downside)>1 and downside.std(ddof=1) else 0.0

    max_dd = float(drawdown.min()) if not drawdown.empty else 0.0
    calmar = float(ann_return / abs(max_dd)) if max_dd else 0.0

    var95  = float(np.percentile(daily, 5) * 100) if len(daily) else 0.0
    cutoff_pct = np.percentile(daily, 5) if len(daily) else 0.0
    cvar95 = float(daily[daily <= cutoff_pct].mean() * 100) if len(daily[daily<=cutoff_pct]) else 0.0

    win_rate  = float((daily > 0).mean() * 100) if len(daily) else 0.0
    best_day  = float(daily.max() * 100) if len(daily) else 0.0
    worst_day = float(daily.min() * 100) if len(daily) else 0.0

    # ── Drawdown duration ────────────────────────────────────────
    in_dd = (drawdown < -0.5)
    dd_dur = 0
    cur_dur = 0
    for v in in_dd:
        if v: cur_dur += 1; dd_dur = max(dd_dur, cur_dur)
        else: cur_dur = 0

    # ── Monthly returns ──────────────────────────────────────────
    monthly = (curve.resample("ME").last().pct_change().dropna() * 100)

    # ── Positive/negative month ratio (Omega-like) ───────────────
    pos_months  = (monthly > 0).sum()
    neg_months  = (monthly <= 0).sum()
    win_months  = float(pos_months / max(pos_months + neg_months, 1) * 100)

    # ── Benchmark-relative metrics ───────────────────────────────
    alpha = beta_vs_spy = r_squared = treynor = info_ratio = te = 0.0
    spy_ann_return = 0.0
    if not spy_daily.empty and len(spy_daily) > 10:
        port_aligned = daily.reindex(spy_daily.index).dropna()
        spy_aligned2 = spy_daily.reindex(port_aligned.index).dropna()
        port_aligned = port_aligned.reindex(spy_aligned2.index)
        if len(port_aligned) > 10:
            cov_matrix   = np.cov(port_aligned, spy_aligned2)
            var_spy      = float(np.var(spy_aligned2, ddof=1))
            beta_vs_spy  = float(cov_matrix[0,1] / var_spy) if var_spy > 0 else 1.0
            alpha_daily  = port_aligned.mean() - (rf_daily + beta_vs_spy*(spy_aligned2.mean()-rf_daily))
            alpha         = float(alpha_daily * 252 * 100)
            corr         = float(np.corrcoef(port_aligned, spy_aligned2)[0,1])
            r_squared    = float(corr ** 2)
            treynor      = float((ann_return/100 - 0.045) / beta_vs_spy * 100) if beta_vs_spy else 0.0
            active_ret   = port_aligned - spy_aligned2
            te           = float(active_ret.std(ddof=1) * np.sqrt(252) * 100) if len(active_ret)>1 else 0.0
            info_ratio   = float(active_ret.mean() / active_ret.std(ddof=1) * np.sqrt(252)) if te > 0 else 0.0

            spy_yrs = max(len(spy_aligned2)/252, 1/252)
            spy_total = float(spy_curve.iloc[-1]) if not spy_curve.empty else 1.0
            spy_ann_return = float((spy_total**(1/spy_yrs)-1)*100)

    # ── Omega Ratio ──────────────────────────────────────────────
    threshold = rf_daily
    gains = daily[daily > threshold] - threshold
    losses = threshold - daily[daily <= threshold]
    omega = float(gains.sum() / losses.sum()) if losses.sum() > 0 else 10.0

    # ── Ulcer Index ──────────────────────────────────────────────
    ulcer = float(np.sqrt((drawdown**2).mean())) if not drawdown.empty else 0.0

    # ── Contribution table ────────────────────────────────────────
    contrib_df = pd.DataFrame()
    if isinstance(contribution_return, pd.Series) and not contribution_return.empty:
        contrib_df = contribution_return.reset_index()
        contrib_df.columns = ["Ticker","Contribution (%)"]
        contrib_df["Contribution (%)"] = contrib_df["Contribution (%)"].round(2)
        contrib_df = contrib_df.sort_values("Contribution (%)", ascending=False)

    metrics = {
        "Total Return":      round(total_return, 2),
        "Annual Return":     round(ann_return, 2),
        "SPY Annual Return": round(spy_ann_return, 2),
        "Annual Volatility": round(ann_vol, 2),
        "Sharpe":            round(sharpe, 3),
        "Sortino":           round(sortino, 3),
        "Calmar":            round(calmar, 3),
        "Omega Ratio":       round(omega, 3),
        "Max Drawdown":      round(max_dd, 2),
        "Max DD Duration":   int(dd_dur),
        "Ulcer Index":       round(ulcer, 2),
        "VaR 95%":           round(var95, 2),
        "CVaR 95%":          round(cvar95, 2),
        "Win Rate (Days)":   round(win_rate, 1),
        "Win Rate (Months)": round(win_months, 1),
        "Best Day":          round(best_day, 2),
        "Worst Day":         round(worst_day, 2),
        "Beta vs SPY":       round(beta_vs_spy, 3),
        "Alpha (Ann %)":     round(alpha, 2),
        "R² vs SPY":         round(r_squared, 3),
        "Treynor (%)":       round(treynor, 2),
        "Tracking Error %":  round(te, 2),
        "Info Ratio":        round(info_ratio, 3),
        "Cash Weight":       round(cash_w * 100, 2),
        "Days":              int(len(daily)),
    }
    return {
        "metrics":        metrics,
        "curve":          curve,
        "drawdown":       drawdown,
        "daily_returns":  daily,
        "monthly_returns":monthly,
        "spy_curve":      spy_curve,
        "spy_daily":      spy_daily,
        "weights":        weights,
        "contribution":   contrib_df,
    }


# ══════════════════════════════════════════════════════════════════
#  BACKTEST CHARTS
# ══════════════════════════════════════════════════════════════════

def investor_backtest_comparison_fig(results, title="Investor Decision Backtest"):
    """Return-curve chart always including SPY benchmark."""
    fig = go.Figure()
    palette = ["#00E5FF","#FFB000","#22C55E","#FF4D6D","#A78BFA","#F97316"]

    # Add investor curves
    for i, (label, res) in enumerate(results.items()):
        curve = res.get("curve", pd.Series(dtype=float))
        if curve is None or curve.empty:
            continue
        y = (curve / curve.iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(
            x=y.index, y=y.values, mode="lines", name=label,
            line=dict(color=palette[i % len(palette)], width=3.2),
            hovertemplate=f"<b>{label}</b><br>%{{x|%Y-%m-%d}}<br>Return: %{{y:.2f}}%<extra></extra>",
        ))

    # Always add SPY benchmark
    first_res = next(iter(results.values()), {})
    spy_curve = first_res.get("spy_curve", pd.Series(dtype=float))
    if spy_curve is not None and not spy_curve.empty:
        spy_pct = (spy_curve / spy_curve.iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(
            x=spy_pct.index, y=spy_pct.values, mode="lines", name="SPY (Benchmark)",
            line=dict(color="#94A3B8", width=1.8, dash="dot"),
            hovertemplate="<b>SPY Benchmark</b><br>%{x|%Y-%m-%d}<br>Return: %{y:.2f}%<extra></extra>",
        ))

    # Zero line
    fig.add_hline(y=0, line=dict(color="rgba(248,250,252,0.20)", width=1.0, dash="dash"))

    fig.update_layout(**base_layout(height=390, title=title))
    fig.update_layout(
        plot_bgcolor="#08111F", paper_bgcolor="#08111F", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(8,17,31,0.72)", bordercolor="rgba(148,163,184,0.22)",
                    borderwidth=1, font=dict(size=11, color="#E2E8F0")),
        yaxis=dict(title="Total Return", ticksuffix="%", showgrid=True,
                   gridcolor="rgba(148,163,184,0.14)", side="right",
                   zeroline=True, zerolinecolor="rgba(248,250,252,0.25)"),
        xaxis=dict(showgrid=False, linecolor="rgba(148,163,184,0.30)"),
        margin=dict(l=22, r=72, t=50, b=42),
        hoverlabel=dict(bgcolor="#111827", bordercolor="#38BDF8",
                        font=dict(color="#F8FAFC", size=12, family="monospace")),
    )
    return fig


def investor_drawdown_comparison_fig(results):
    """Underwater drawdown chart with SPY overlay."""
    fig = go.Figure()
    palette = ["#00E5FF","#FFB000","#22C55E","#FF4D6D","#A78BFA","#F97316"]

    for i, (label, res) in enumerate(results.items()):
        dd = res.get("drawdown", pd.Series(dtype=float))
        if dd is None or dd.empty:
            continue
        clr = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values, mode="lines", name=label,
            line=dict(color=clr, width=2.4),
            fill="tozeroy",
            fillcolor=f"rgba({int(clr[1:3],16)},{int(clr[3:5],16)},{int(clr[5:7],16)},0.12)",
            hovertemplate=f"<b>{label}</b><br>%{{x|%Y-%m-%d}}<br>Drawdown: %{{y:.2f}}%<extra></extra>",
        ))

    # SPY drawdown
    first_res = next(iter(results.values()), {})
    spy_curve = first_res.get("spy_curve", pd.Series(dtype=float))
    if spy_curve is not None and not spy_curve.empty:
        spy_run_max = spy_curve.cummax()
        spy_dd = (spy_curve / spy_run_max - 1) * 100
        fig.add_trace(go.Scatter(
            x=spy_dd.index, y=spy_dd.values, mode="lines", name="SPY (Benchmark)",
            line=dict(color="#94A3B8", width=1.6, dash="dot"),
            hovertemplate="<b>SPY</b><br>%{x|%Y-%m-%d}<br>DD: %{y:.2f}%<extra></extra>",
        ))

    fig.add_hline(y=0, line=dict(color="rgba(248,250,252,0.18)", width=1.0))
    fig.update_layout(**base_layout(height=320, title="Underwater Drawdown"))
    fig.update_layout(
        plot_bgcolor="#08111F", paper_bgcolor="#08111F", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(8,17,31,0.72)", bordercolor="rgba(148,163,184,0.22)",
                    borderwidth=1, font=dict(size=11, color="#E2E8F0")),
        yaxis=dict(title="Drawdown", ticksuffix="%", showgrid=True,
                   gridcolor="rgba(148,163,184,0.14)", side="right",
                   zeroline=True, zerolinecolor="rgba(248,250,252,0.22)"),
        xaxis=dict(showgrid=False, linecolor="rgba(148,163,184,0.30)"),
        margin=dict(l=22, r=72, t=50, b=42),
        hoverlabel=dict(bgcolor="#111827", bordercolor="#38BDF8",
                        font=dict(color="#F8FAFC", size=12, family="monospace")),
    )
    return fig


def investor_rolling_metrics_fig(results):
    """Rolling 63-day (3M) Sharpe ratio and annualised volatility."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=["Rolling 3-Month Sharpe Ratio",
                                        "Rolling 3-Month Annualised Volatility (%)"])
    palette = ["#00E5FF","#FFB000","#22C55E","#FF4D6D"]
    rf_daily = 0.045 / 252
    WINDOW = 63

    for i, (label, res) in enumerate(results.items()):
        daily = res.get("daily_returns", pd.Series(dtype=float))
        if daily is None or daily.empty or len(daily) < WINDOW:
            continue
        clr = palette[i % len(palette)]

        roll_mean = daily.rolling(WINDOW).mean()
        roll_std  = daily.rolling(WINDOW).std(ddof=1)
        roll_sharpe = ((roll_mean - rf_daily) / roll_std * np.sqrt(252)).dropna()
        roll_vol    = (roll_std * np.sqrt(252) * 100).dropna()

        fig.add_trace(go.Scatter(x=roll_sharpe.index, y=roll_sharpe.values,
                                 mode="lines", name=label, line=dict(color=clr, width=2.0),
                                 hovertemplate=f"<b>{label}</b><br>%{{x|%Y-%m-%d}}<br>Sharpe: %{{y:.2f}}<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=roll_vol.index, y=roll_vol.values,
                                 mode="lines", name=label, showlegend=False,
                                 line=dict(color=clr, width=2.0, dash="solid"),
                                 hovertemplate=f"<b>{label}</b><br>%{{x|%Y-%m-%d}}<br>Vol: %{{y:.1f}}%<extra></extra>"),
                      row=2, col=1)

    # SPY rolling
    first_res = next(iter(results.values()), {})
    spy_daily = first_res.get("spy_daily", pd.Series(dtype=float))
    if spy_daily is not None and not spy_daily.empty and len(spy_daily) >= WINDOW:
        s_mean = spy_daily.rolling(WINDOW).mean()
        s_std  = spy_daily.rolling(WINDOW).std(ddof=1)
        s_shr  = ((s_mean - rf_daily) / s_std * np.sqrt(252)).dropna()
        s_vol  = (s_std * np.sqrt(252) * 100).dropna()
        fig.add_trace(go.Scatter(x=s_shr.index, y=s_shr.values, mode="lines",
                                 name="SPY", line=dict(color="#94A3B8", width=1.5, dash="dot"),
                                 hovertemplate="<b>SPY</b><br>%{x|%Y-%m-%d}<br>Sharpe: %{y:.2f}<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=s_vol.index, y=s_vol.values, mode="lines",
                                 name="SPY", showlegend=False, line=dict(color="#94A3B8", width=1.5, dash="dot"),
                                 hovertemplate="<b>SPY</b><br>%{x|%Y-%m-%d}<br>Vol: %{y:.1f}%<extra></extra>"),
                      row=2, col=1)

    fig.add_hline(y=0, row=1, col=1, line=dict(color="rgba(248,250,252,0.20)", width=1.0, dash="dash"))

    _shared = dict(showgrid=True, gridcolor="rgba(148,163,184,0.12)", zeroline=False,
                   tickfont=dict(color="#94A3B8", size=9))
    fig.update_layout(height=360, plot_bgcolor="#08111F", paper_bgcolor="#08111F",
                      showlegend=True,
                      legend=dict(orientation="h", y=1.04, x=0, xanchor="left",
                                  bgcolor="rgba(8,17,31,0.72)", font=dict(size=10, color="#E2E8F0")),
                      margin=dict(l=22, r=60, t=52, b=36),
                      font=dict(color="#94A3B8", size=10),
                      hoverlabel=dict(bgcolor="#111827", font=dict(color="#F8FAFC", size=11)))
    fig.update_yaxes(**_shared)
    fig.update_xaxes(showgrid=False, linecolor="rgba(148,163,184,0.28)")
    fig.update_yaxes(ticksuffix="", row=1, col=1, side="right")
    fig.update_yaxes(ticksuffix="%", row=2, col=1, side="right")
    for ann in fig.layout.annotations:
        ann.font.color = "#94A3B8"
        ann.font.size  = 11
    return fig


def investor_monthly_heatmap_fig(res, label="Portfolio"):
    """Calendar heatmap of monthly returns."""
    monthly = res.get("monthly_returns", pd.Series(dtype=float))
    if monthly is None or monthly.empty:
        return go.Figure()

    df = monthly.to_frame("ret")
    df.index = pd.to_datetime(df.index)
    df["year"]  = df.index.year
    df["month"] = df.index.month

    years  = sorted(df["year"].unique())
    months = list(range(1,13))
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    z_matrix = []
    text_matrix = []
    for yr in years:
        row_z = []
        row_t = []
        for mo in months:
            sub = df[(df["year"]==yr) & (df["month"]==mo)]
            if sub.empty:
                row_z.append(None); row_t.append("")
            else:
                v = float(sub["ret"].iloc[0])
                row_z.append(v)
                row_t.append(f"{v:+.1f}%")
        z_matrix.append(row_z)
        text_matrix.append(row_t)

    fig = go.Figure(go.Heatmap(
        z=z_matrix,
        x=month_labels,
        y=[str(y) for y in years],
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=10, color="#F8FAFC"),
        colorscale=[
            [0.0,   "#7F1D1D"],
            [0.25,  "#EF4444"],
            [0.48,  "#1E293B"],
            [0.52,  "#1E293B"],
            [0.75,  "#10B981"],
            [1.0,   "#064E3B"],
        ],
        zmid=0,
        zmin=-8, zmax=8,
        showscale=True,
        colorbar=dict(title=dict(text="%", font=dict(color="#64748B", size=10)),
                      ticksuffix="%", tickfont=dict(color="#94A3B8", size=9), len=0.7,
                      bgcolor="rgba(8,17,31,0.6)", bordercolor="#252A38"),
        hovertemplate="<b>%{y} %{x}</b><br>Monthly return: %{text}<extra></extra>",
    ))
    fig.update_layout(
        height=max(200, len(years)*46+80),
        plot_bgcolor="#08111F", paper_bgcolor="#08111F",
        margin=dict(l=55, r=70, t=36, b=28),
        title=dict(text=f"Monthly Returns — {label}", font=dict(color="#E2E8F0", size=12), x=0.01),
        xaxis=dict(side="top", tickfont=dict(color="#CBD5E1", size=10), showgrid=False),
        yaxis=dict(tickfont=dict(color="#CBD5E1", size=10), showgrid=False, autorange="reversed"),
        font=dict(color="#94A3B8"),
    )
    return fig


def investor_return_dist_fig(results):
    """Daily return distribution histogram with normal overlay."""
    from plotly.subplots import make_subplots as _msp
    fig = go.Figure()
    palette = ["#00E5FF","#FFB000","#22C55E","#FF4D6D","#A78BFA"]

    for i, (label, res) in enumerate(results.items()):
        daily = res.get("daily_returns", pd.Series(dtype=float))
        if daily is None or daily.empty:
            continue
        clr = palette[i % len(palette)]
        d_pct = daily * 100
        fig.add_trace(go.Histogram(
            x=d_pct, name=label, nbinsx=60, opacity=0.65,
            marker=dict(color=clr, line=dict(color="#0d0f14", width=0.5)),
            hovertemplate=f"<b>{label}</b><br>Range: %{{x:.2f}}%<br>Count: %{{y}}<extra></extra>",
        ))

    # SPY distribution overlay
    first_res = next(iter(results.values()), {})
    spy_daily = first_res.get("spy_daily", pd.Series(dtype=float))
    if spy_daily is not None and not spy_daily.empty:
        fig.add_trace(go.Histogram(
            x=spy_daily*100, name="SPY", nbinsx=60, opacity=0.38,
            marker=dict(color="#94A3B8", line=dict(color="#0d0f14", width=0.4)),
        ))

    fig.update_layout(**base_layout(height=300, title="Daily Return Distribution"))
    fig.update_layout(
        plot_bgcolor="#08111F", paper_bgcolor="#08111F",
        barmode="overlay",
        legend=dict(orientation="h", y=1.04, x=0, xanchor="left",
                    font=dict(size=10, color="#E2E8F0"), bgcolor="rgba(8,17,31,0.72)"),
        xaxis=dict(title="Daily Return (%)", ticksuffix="%",
                   showgrid=True, gridcolor="rgba(148,163,184,0.10)"),
        yaxis=dict(title="Count", side="right",
                   showgrid=True, gridcolor="rgba(148,163,184,0.10)"),
        margin=dict(l=22, r=65, t=46, b=40),
        hoverlabel=dict(bgcolor="#111827", font=dict(color="#F8FAFC", size=11)),
    )
    return fig


def investor_contribution_fig(contrib_df):
    """Bar chart of per-holding return contribution."""
    if contrib_df is None or contrib_df.empty:
        return go.Figure()
    df = contrib_df.sort_values("Contribution (%)", ascending=True)
    colors = [GREEN if v >= 0 else RED for v in df["Contribution (%)"]]
    fig = go.Figure(go.Bar(
        y=df["Ticker"].astype(str),
        x=df["Contribution (%)"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="#0d0f14", width=0.6)),
        text=[f"{v:+.1f}%" for v in df["Contribution (%)"]],
        textposition="outside",
        textfont=dict(color="#F8FAFC", size=10),
        hovertemplate="<b>%{y}</b><br>Contribution: %{x:.2f}%<extra></extra>",
        cliponaxis=False,
    ))
    fig.add_vline(x=0, line=dict(color="rgba(248,250,252,0.20)", width=1.0))
    fig.update_layout(**base_layout(height=max(220, len(df)*32+60),
                                    title="Estimated Holding Contribution (%)"))
    fig.update_layout(
        plot_bgcolor="#08111F", paper_bgcolor="#08111F",
        showlegend=False,
        xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="rgba(148,163,184,0.10)"),
        yaxis=dict(showgrid=False, tickfont=dict(color="#CBD5E1", size=10), automargin=True),
        margin=dict(l=10, r=80, t=44, b=24),
        hoverlabel=dict(bgcolor="#111827", font=dict(color="#F8FAFC", size=11)),
    )
    return fig


# ── Metrics comparison table ──────────────────────────────────────
def investor_backtest_metrics_table(results):
    METRIC_KEYS = [
        "Total Return", "Annual Return", "SPY Annual Return",
        "Annual Volatility", "Sharpe", "Sortino", "Calmar",
        "Omega Ratio", "Max Drawdown", "Max DD Duration",
        "Ulcer Index", "VaR 95%", "CVaR 95%",
        "Win Rate (Days)", "Win Rate (Months)",
        "Best Day", "Worst Day",
        "Beta vs SPY", "Alpha (Ann %)", "R² vs SPY",
        "Treynor (%)", "Tracking Error %", "Info Ratio",
        "Cash Weight", "Days",
    ]
    rows = []
    for label, res in results.items():
        m = res.get("metrics", {}) or {}
        if not m: continue
        row = {"Investor Model": label}
        for k in METRIC_KEYS:
            row[k] = m.get(k, None)
        rows.append(row)
    return pd.DataFrame(rows)


# ── Backtest panel renderer ───────────────────────────────────────
def render_investor_backtest_panel(primary_name, primary_port, stance, max_holdings, model_blend, use_news, refresh_token):
    st.markdown(f"<div class='section-head'>{tr('Investor decision backtest & comparison')}</div>", unsafe_allow_html=True)

    b1, b2, b3, b4 = st.columns([1.0, 1.05, 1.1, 1.25])
    lookback_label = b1.selectbox(tr("Backtest window"),
                                  ["1M","3M","6M","1Y","2Y","5Y","10Y","20Y","25Y"],
                                  index=3, key="investor_bt_window")
    period_map = {"1M":"1mo","3M":"3mo","6M":"6mo","1Y":"1y","2Y":"2y",
                  "5Y":"5y","10Y":"10y","20Y":"20y","25Y":"25y"}
    rebalance    = b2.selectbox(tr("Backtest method"), ["Monthly","Buy & Hold"],
                                index=0, key="investor_bt_method", format_func=tr)
    compare_enabled = b3.checkbox(tr("Compare two investor decisions"), value=False,
                                   key="investor_compare_enabled")
    compare_name = primary_name
    if compare_enabled:
        choices     = [x for x in INVESTOR_PROFILES.keys() if x != primary_name]
        default_idx = choices.index("Ray Dalio") if "Ray Dalio" in choices else 0
        compare_name = b4.selectbox(tr("Compare with"), choices,
                                    index=default_idx, key="investor_compare_name")
    else:
        b4.caption(tr("Enable comparison to test another investor model."))

    with st.spinner("Backtesting simulated investor decisions…"):
        primary_bt = investor_backtest_from_portfolio(primary_port, period_map.get(lookback_label,"1y"), refresh_token, rebalance)
        results = {primary_name: primary_bt}
        compare_port = None
        if compare_enabled and compare_name:
            compare_port, _, _, _, _ = simulate_investor_portfolio(compare_name, stance, max_holdings, model_blend, use_news, refresh_token)
            compare_bt = investor_backtest_from_portfolio(compare_port, period_map.get(lookback_label,"1y"), refresh_token, rebalance)
            results[compare_name] = compare_bt

    metrics_df = investor_backtest_metrics_table(results)
    if metrics_df.empty:
        st.info("Backtest data could not be built from FMP. Try a longer window or another investor profile.")
        return

    # ── Quick-glance KPI row ─────────────────────────────────────
    p_m = primary_bt.get("metrics", {})
    spy_ann = p_m.get("SPY Annual Return", 0)
    ann_r   = p_m.get("Annual Return", 0)
    excess  = ann_r - spy_ann

    kpi_cols = st.columns(8)
    kpi_cols[0].metric("Total Return",       f"{p_m.get('Total Return',0):+.2f}%")
    kpi_cols[1].metric("Annual Return",       f"{ann_r:+.2f}%",
                        delta=f"vs SPY {excess:+.2f}%", delta_color="normal")
    kpi_cols[2].metric("Sharpe",              f"{p_m.get('Sharpe',0):.2f}")
    kpi_cols[3].metric("Sortino",             f"{p_m.get('Sortino',0):.2f}")
    kpi_cols[4].metric("Max Drawdown",        f"{p_m.get('Max Drawdown',0):.2f}%")
    kpi_cols[5].metric("Alpha (Ann %)",       f"{p_m.get('Alpha (Ann %)',0):+.2f}%")
    kpi_cols[6].metric("Omega Ratio",         f"{p_m.get('Omega Ratio',0):.2f}")
    kpi_cols[7].metric("Ulcer Index",         f"{p_m.get('Ulcer Index',0):.2f}")

    # ── Return curve + drawdown ──────────────────────────────────
    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_backtest_comparison_fig(results, f"{lookback_label} Simulated Return vs SPY"),
                        use_container_width=True,
                        key=f"bt_ret_{primary_name}_{compare_name}_{lookback_label}_{rebalance}")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_drawdown_comparison_fig(results),
                        use_container_width=True,
                        key=f"bt_dd_{primary_name}_{compare_name}_{lookback_label}_{rebalance}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Rolling metrics ──────────────────────────────────────────
    if any(len(r.get("daily_returns", pd.Series(dtype=float))) >= 63 for r in results.values()):
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_rolling_metrics_fig(results), use_container_width=True,
                        key=f"bt_roll_{primary_name}_{compare_name}_{lookback_label}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Monthly heatmap + return distribution ────────────────────
    hm_col, dist_col = st.columns([1.1, 0.9])
    with hm_col:
        monthly_data = primary_bt.get("monthly_returns", pd.Series(dtype=float))
        if monthly_data is not None and not monthly_data.empty:
            st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
            st.plotly_chart(investor_monthly_heatmap_fig(primary_bt, primary_name),
                            use_container_width=True,
                            key=f"bt_heatmap_{primary_name}_{lookback_label}")
            st.markdown('</div>', unsafe_allow_html=True)
    with dist_col:
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_return_dist_fig(results), use_container_width=True,
                        key=f"bt_dist_{primary_name}_{compare_name}_{lookback_label}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Holding contribution ─────────────────────────────────────
    contrib = primary_bt.get("contribution", pd.DataFrame())
    if contrib is not None and not contrib.empty:
        st.markdown(f"<div class='section-head'>Estimated Holding Return Contribution — {primary_name}</div>", unsafe_allow_html=True)
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_contribution_fig(contrib), use_container_width=True,
                        key=f"bt_contrib_{primary_name}_{lookback_label}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Full metrics comparison table ────────────────────────────
    shead("Detailed Performance Metrics")

    # Format metrics table nicely
    fmt_map = {
        "Total Return": "{:+.2f}%","Annual Return": "{:+.2f}%","SPY Annual Return": "{:+.2f}%",
        "Annual Volatility": "{:.2f}%","Sharpe": "{:.3f}","Sortino": "{:.3f}","Calmar": "{:.3f}",
        "Omega Ratio": "{:.3f}","Max Drawdown": "{:.2f}%","Max DD Duration": "{:.0f} days",
        "Ulcer Index": "{:.2f}","VaR 95%": "{:.2f}%","CVaR 95%": "{:.2f}%",
        "Win Rate (Days)": "{:.1f}%","Win Rate (Months)": "{:.1f}%",
        "Best Day": "{:+.2f}%","Worst Day": "{:+.2f}%",
        "Beta vs SPY": "{:.3f}","Alpha (Ann %)": "{:+.2f}%","R² vs SPY": "{:.3f}",
        "Treynor (%)": "{:+.2f}%","Tracking Error %": "{:.2f}%","Info Ratio": "{:.3f}",
        "Cash Weight": "{:.1f}%","Days": "{:.0f}",
    }
    display_df = metrics_df.copy()
    for col in display_df.columns:
        if col == "Investor Model": continue
        fmt = fmt_map.get(col, "{:.2f}")
        def _fmt(v, f=fmt):
            try: return f.format(float(v))
            except: return "—"
        display_df[col] = display_df[col].apply(_fmt)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Holdings comparison ───────────────────────────────────────
    if compare_enabled and compare_port is not None and not compare_port.empty:
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown(f"<div class='section-head'>{html.escape(primary_name)} {tr('simulated holdings')}</div>", unsafe_allow_html=True)
            show = primary_port[[c for c in ["Ticker","Weight","Sector","Investor Score","Risk Index"] if c in primary_port.columns]].head(12).copy()
            if "Weight" in show: show["Weight"] = show["Weight"].map(lambda x: f"{float(x):.2f}%")
            st.dataframe(show, use_container_width=True, hide_index=True)
        with c_right:
            st.markdown(f"<div class='section-head'>{html.escape(compare_name)} {tr('simulated holdings')}</div>", unsafe_allow_html=True)
            show2 = compare_port[[c for c in ["Ticker","Weight","Sector","Investor Score","Risk Index"] if c in compare_port.columns]].head(12).copy()
            if "Weight" in show2: show2["Weight"] = show2["Weight"].map(lambda x: f"{float(x):.2f}%")
            st.dataframe(show2, use_container_width=True, hide_index=True)

    page_comment("Backtest methodology", [
        "<b>Benchmark:</b> SPY (S&P 500 ETF) is always shown as the reference. Excess return = portfolio minus SPY annualised return.",
        "<b>Monthly rebalancing:</b> positions are reset to target weights at each month-end, simulating realistic institutional portfolio management.",
        "<b>Metrics:</b> Sharpe/Sortino use 4.5% risk-free rate. Omega = ratio of gains above threshold to losses below. Ulcer Index measures pain of drawdowns.",
        "<b>Contribution:</b> estimated holding-level return based on price change × initial weight. Does not account for intra-period trading.",
        "<b>Limitation:</b> this is a model backtest, not evidence that the real investor owned these assets. Past performance does not guarantee future results.",
    ])


# ══════════════════════════════════════════════════════════════════
#  INVESTOR VIEW — MAIN RENDER
# ══════════════════════════════════════════════════════════════════

def render_investor_view():
    shead("Famous Investor Simulator")
    st.caption("Educational simulation of famous-investor styles. Does not represent any real investor's current holdings, advice, or private opinion.")

    if "investor_refresh_token" not in st.session_state:
        st.session_state.investor_refresh_token = 0

    c1, c2, c3, c4, c5 = st.columns([1.45, 1.1, 0.80, 0.95, 0.75])
    investor_name = c1.selectbox(tr("Investor profile"), list(INVESTOR_PROFILES.keys()), index=0, key="investor_profile")
    stance        = c2.selectbox(tr("Market stance"), ["Balanced","Defensive","Aggressive"],
                                  index=0, key="investor_stance", format_func=tr)
    max_holdings  = c3.selectbox(tr("Max holdings"), [5,8,10,12,15], index=2, key="investor_holdings")
    model_blend   = c4.slider(tr("Model blend"), min_value=0, max_value=100, value=70, step=5,
                               help="100% = pure selected-investor style. 0% = generic multi-factor quant model.",
                               key="investor_model_blend")
    if c5.button("⟳ " + tr("Update"), key="investor_update", use_container_width=True):
        st.session_state.investor_refresh_token = int(time.time())
        fetch_market_regime_for_investor.clear()
        fetch_investor_universe_data.clear()
        _fetch_spy_benchmark.clear()

    use_news = st.checkbox(tr("Use latest market-news shock layer"), value=True, key="investor_use_news")

    with st.spinner("Building investor-style portfolio from live prices, market regime, factor scores, and news shock layer…"):
        port, sector, regime, profile, news_used = simulate_investor_portfolio(
            investor_name, stance, max_holdings, model_blend, use_news,
            st.session_state.investor_refresh_token
        )

    render_investor_card(investor_name, profile, regime, port)

    if port.empty:
        st.info("Investor model could not fetch enough data from FMP. Try Update or choose a different profile.")
        return

    if not port.empty:
        render_investor_ai_explanation(investor_name, profile, regime, port, stance, model_blend, use_news, news_used)

    # ── Portfolio-level KPI grid ──────────────────────────────────
    equity      = 100 - float(port.loc[port["Ticker"].eq("CASH"), "Weight"].sum()) if "Ticker" in port else 100
    cash        = 100 - equity
    top_sector  = sector.iloc[0]["Sector"] if not sector.empty else "—"
    concentration = float(port[port["Ticker"]!="CASH"].head(3)["Weight"].sum()) if not port.empty else 0
    n_equity    = int((port["Ticker"] != "CASH").sum()) if "Ticker" in port.columns else 0
    avg_score   = _investor_weighted_avg(port, "Investor Score")
    avg_risk_idx= _investor_weighted_avg(port, "Risk Index") if "Risk Index" in port.columns else 0

    risk_on = regime.get("risk_on", 50)
    vix_est = regime.get("vix", 20)

    st.markdown(f"""
    <div class="investor-grid" style="grid-template-columns:repeat(8,minmax(0,1fr))">
      <div class="investor-mini"><div class="investor-mini-label">Risk-on Score</div><div class="investor-mini-value" style="color:{'#10b981' if risk_on>62 else '#f59e0b' if risk_on>42 else '#ef4444'}">{risk_on:.0f}/100</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Equity Exposure</div><div class="investor-mini-value">{equity:.1f}%</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Cash / Defense</div><div class="investor-mini-value">{cash:.1f}%</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Top 3 Concentration</div><div class="investor-mini-value">{concentration:.1f}%</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Equity Holdings</div><div class="investor-mini-value">{n_equity}</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Avg Investor Score</div><div class="investor-mini-value" style="color:#3b82f6">{avg_score:.1f}/100</div></div>
      <div class="investor-mini"><div class="investor-mini-label">Top Sector</div><div class="investor-mini-value" style="font-size:13px">{html.escape(top_sector[:14])}</div></div>
      <div class="investor-mini"><div class="investor-mini-label">VIX Estimate</div><div class="investor-mini-value" style="color:{'#10b981' if vix_est<18 else '#f59e0b' if vix_est<28 else '#ef4444'}">{vix_est:.1f}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Allocation + Sector + Factor Radar ───────────────────────
    st.markdown('<div class="investor-allocation-section">', unsafe_allow_html=True)
    al_col, sec_col, rad_col = st.columns([1.05, 0.95, 1.0])
    with al_col:
        st.markdown(f"<div class='section-head'>{tr('Portfolio allocation')}</div>", unsafe_allow_html=True)
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_allocation_fig(port), use_container_width=True, key=f"investor_alloc_{investor_name}")
        st.markdown('</div>', unsafe_allow_html=True)
    with sec_col:
        st.markdown(f"<div class='section-head'>{tr('Sector allocation')}</div>", unsafe_allow_html=True)
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_sector_fig(sector), use_container_width=True, key=f"investor_sector_{investor_name}")
        st.markdown('</div>', unsafe_allow_html=True)
    with rad_col:
        st.markdown(f"<div class='section-head'>Factor Exposure Radar</div>", unsafe_allow_html=True)
        st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
        st.plotly_chart(investor_factor_radar_fig(port, profile), use_container_width=True, key=f"investor_radar_{investor_name}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div style='margin-top:-1.2rem'></div>", unsafe_allow_html=True)

    # ── Simulated portfolio table ─────────────────────────────────
    show_cols = ["Ticker","Company / Asset","Sector","Country","Weight",
                 "Investor Score","Style Match","Quality","Value","Growth",
                 "Momentum","Stability","Risk Index","News Shock","Reason"]
    table = port[[c for c in show_cols if c in port.columns]].copy()
    if "Weight" in table:
        table["Weight"] = table["Weight"].map(lambda x: f"{float(x):.2f}%")
    for fc in ["Quality","Value","Growth","Momentum","Stability"]:
        if fc in table.columns:
            table[fc] = table[fc].map(lambda x: f"{float(x):.0f}/100")
    if "Investor Score" in table.columns:
        table["Investor Score"] = table["Investor Score"].map(lambda x: f"{float(x):.1f}/100")
    st.markdown(f"<div class='section-head'>{tr('Simulated portfolio')}</div>", unsafe_allow_html=True)
    st.dataframe(table, use_container_width=True, hide_index=True)

    # ── Backtest section ─────────────────────────────────────────
    render_investor_backtest_panel(investor_name, port, stance, max_holdings,
                                    model_blend, use_news,
                                    st.session_state.investor_refresh_token)

    # ── Investor notes ───────────────────────────────────────────
    likes  = ", ".join(profile.get("likes",  []))
    avoids = ", ".join(profile.get("avoids", []))
    market_view = (
        f"{regime.get('label')} with risk-on score {regime.get('risk_on'):.0f}/100. "
        f"The model tilts toward growth/momentum when risk appetite is strong and "
        f"toward cash, quality, value, and defensive sectors when risk appetite weakens."
    )
    if news_used:
        top_news = news_used[0].get("ai_headline", news_used[0].get("title",""))
        market_view += f" News shock layer active — top theme: {top_news}."

    st.markdown(f"""
    <div class="investor-note"><b>{tr('Current market view')}:</b> {html.escape(market_view)}</div>
    <div class="investor-note"><b>{tr('What this investor may like now')}:</b> {html.escape(likes)}.</div>
    <div class="investor-note"><b>{tr('What this investor may avoid now')}:</b> {html.escape(avoids)}.</div>
    <div class="investor-note"><b>Scoring model transparency:</b> Factor scores (Value, Quality, Growth, Momentum, Stability) are computed from live FMP fundamentals. The final Investor Score blends the investor-style factor weights ({model_blend}%) with a generic quant multi-factor model ({100-model_blend}%), then adds market-regime overlay and news shock adjustment. Position weights use a score-power law with {('concentrated' if 'concentrated' in profile.get('concentration','').lower() else 'diversified')} style — capped at {'35%' if 'concentrated' in profile.get('concentration','').lower() else '25%'} per holding.</div>
    """, unsafe_allow_html=True)

    page_comment("Model disclaimer", [
        "<b>Simulation only:</b> this does not claim to know what any investor currently thinks or owns.",
        "<b>Not financial advice:</b> use as a watchlist/thesis generator, then verify fundamentals, filings, valuation, liquidity, and risk.",
        "<b>Benchmark:</b> SPY (S&P 500) is used as the reference for Alpha, Beta, R², Tracking Error, and Information Ratio.",
        "<b>Model mechanics:</b> allocation combines investor-style factor weights, current market regime (VIX, MA signals, SPY/QQQ/IWM breadth), news shock tags, and fundamental factor scores from FMP.",
    ])

# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def fmtn(n, pre="", d=2):
    if n is None: return "—"
    try:
        n = float(n)
        if abs(n)>=1e12: return f"{pre}{n/1e12:.{d}f}T"
        if abs(n)>=1e9:  return f"{pre}{n/1e9:.{d}f}B"
        if abs(n)>=1e6:  return f"{pre}{n/1e6:.{d}f}M"
        return f"{pre}{n:,.{d}f}"
    except: return "—"

def fpct(v, d=1):
    if v is None: return "—"
    try: return f"{float(v)*100:.{d}f}%"
    except: return "—"


# Broad sector averages for context only; not live data.
SECTOR_AVERAGES = {
    "Technology": dict(pe=30,fpe=26,ps=7,pb=8,peg=2,ev_ebitda=22,ev_rev=6.5,beta=1.2,div_yield=.004,gross_margin=.58,net_margin=.18,op_margin=.22,rev_growth=.10,eps_growth=.10,roe=.24,roa=.09,debt_equity=.85,current_ratio=1.6,quick_ratio=1.2,vol=32,sharpe=.70,sortino=1.0,calmar=.55,max_dd=-30,var95=-2.6,cvar95=-3.8,win=53,r2=.55,te=18,ir=.20,rsi=50,adx=22,rvol20=32),
    "Healthcare": dict(pe=24,fpe=21,ps=4.5,pb=4,peg=1.8,ev_ebitda=15,ev_rev=4.3,beta=.85,div_yield=.015,gross_margin=.62,net_margin=.13,op_margin=.18,rev_growth=.06,eps_growth=.07,roe=.18,roa=.07,debt_equity=.75,current_ratio=1.7,quick_ratio=1.25,vol=25,sharpe=.55,sortino=.8,calmar=.45,max_dd=-25,var95=-2.1,cvar95=-3.2,win=52,r2=.40,te=16,ir=.15,rsi=50,adx=20,rvol20=25),
    "Financial Services": dict(pe=13,fpe=12,ps=2.8,pb=1.4,peg=1.2,ev_ebitda=11,ev_rev=3,beta=1.1,div_yield=.025,gross_margin=.45,net_margin=.22,op_margin=.28,rev_growth=.04,eps_growth=.05,roe=.12,roa=.012,debt_equity=1.8,current_ratio=1.1,quick_ratio=1,vol=28,sharpe=.5,sortino=.75,calmar=.4,max_dd=-28,var95=-2.3,cvar95=-3.4,win=52,r2=.60,te=15,ir=.12,rsi=50,adx=20,rvol20=28),
    "Communication Services": dict(pe=22,fpe=20,ps=4,pb=4.5,peg=1.7,ev_ebitda=13,ev_rev=4,beta=1.05,div_yield=.01,gross_margin=.52,net_margin=.14,op_margin=.20,rev_growth=.06,eps_growth=.07,roe=.18,roa=.07,debt_equity=1,current_ratio=1.3,quick_ratio=1,vol=30,sharpe=.55,sortino=.85,calmar=.45,max_dd=-30,var95=-2.4,cvar95=-3.6,win=52,r2=.55,te=17,ir=.15,rsi=50,adx=21,rvol20=30),
    "Consumer Cyclical": dict(pe=22,fpe=19,ps=2,pb=4,peg=1.5,ev_ebitda=14,ev_rev=2.5,beta=1.25,div_yield=.012,gross_margin=.38,net_margin=.07,op_margin=.10,rev_growth=.05,eps_growth=.06,roe=.18,roa=.06,debt_equity=1.2,current_ratio=1.4,quick_ratio=.9,vol=34,sharpe=.45,sortino=.70,calmar=.35,max_dd=-35,var95=-2.8,cvar95=-4.2,win=51,r2=.58,te=19,ir=.10,rsi=50,adx=21,rvol20=34),
    "Consumer Defensive": dict(pe=21,fpe=19,ps=1.6,pb=4.2,peg=2,ev_ebitda=14,ev_rev=2,beta=.6,div_yield=.025,gross_margin=.34,net_margin=.07,op_margin=.10,rev_growth=.03,eps_growth=.04,roe=.20,roa=.07,debt_equity=1.1,current_ratio=1.2,quick_ratio=.8,vol=20,sharpe=.50,sortino=.75,calmar=.40,max_dd=-20,var95=-1.6,cvar95=-2.5,win=52,r2=.35,te=13,ir=.10,rsi=50,adx=19,rvol20=20),
    "Industrials": dict(pe=20,fpe=18,ps=1.8,pb=3.5,peg=1.6,ev_ebitda=13,ev_rev=2,beta=1.05,div_yield=.018,gross_margin=.32,net_margin=.08,op_margin=.11,rev_growth=.04,eps_growth=.05,roe=.16,roa=.06,debt_equity=.95,current_ratio=1.5,quick_ratio=1,vol=27,sharpe=.50,sortino=.78,calmar=.40,max_dd=-27,var95=-2.2,cvar95=-3.3,win=52,r2=.55,te=15,ir=.12,rsi=50,adx=20,rvol20=27),
    "Energy": dict(pe=12,fpe=11,ps=1.2,pb=2,peg=1,ev_ebitda=6,ev_rev=1.4,beta=1.35,div_yield=.035,gross_margin=.35,net_margin=.10,op_margin=.14,rev_growth=.03,eps_growth=.03,roe=.18,roa=.07,debt_equity=.6,current_ratio=1.2,quick_ratio=.9,vol=36,sharpe=.40,sortino=.65,calmar=.35,max_dd=-38,var95=-3,cvar95=-4.6,win=51,r2=.45,te=22,ir=.08,rsi=50,adx=22,rvol20=36),
    "Utilities": dict(pe=18,fpe=16,ps=2.3,pb=1.8,peg=2.5,ev_ebitda=11,ev_rev=3,beta=.55,div_yield=.035,gross_margin=.38,net_margin=.10,op_margin=.20,rev_growth=.03,eps_growth=.03,roe=.10,roa=.03,debt_equity=1.5,current_ratio=.9,quick_ratio=.7,vol=18,sharpe=.45,sortino=.65,calmar=.35,max_dd=-18,var95=-1.4,cvar95=-2.2,win=52,r2=.30,te=12,ir=.08,rsi=50,adx=18,rvol20=18),
    "Real Estate": dict(pe=28,fpe=23,ps=6,pb=1.7,peg=2.2,ev_ebitda=17,ev_rev=7,beta=.95,div_yield=.04,gross_margin=.55,net_margin=.12,op_margin=.24,rev_growth=.03,eps_growth=.03,roe=.08,roa=.03,debt_equity=1.4,current_ratio=1,quick_ratio=.8,vol=26,sharpe=.40,sortino=.60,calmar=.30,max_dd=-28,var95=-2.1,cvar95=-3.2,win=51,r2=.45,te=16,ir=.05,rsi=50,adx=19,rvol20=26),
    "Basic Materials": dict(pe=16,fpe=14,ps=1.5,pb=2,peg=1.3,ev_ebitda=8,ev_rev=1.8,beta=1.15,div_yield=.025,gross_margin=.30,net_margin=.08,op_margin=.12,rev_growth=.03,eps_growth=.04,roe=.12,roa=.05,debt_equity=.7,current_ratio=1.6,quick_ratio=1,vol=31,sharpe=.42,sortino=.65,calmar=.35,max_dd=-32,var95=-2.6,cvar95=-3.9,win=51,r2=.50,te=18,ir=.08,rsi=50,adx=21,rvol20=31),
}

def _avg(metric, info=None):
    sector = (info or {}).get("sector", "Technology") or "Technology"
    return SECTOR_AVERAGES.get(sector, SECTOR_AVERAGES["Technology"]).get(metric)

def _fmt_avg(metric, v):
    if v is None: return ""
    if metric in {"gross_margin","net_margin","op_margin","rev_growth","eps_growth","roe","roa","div_yield"}: return f"{v*100:.1f}%"
    if metric in {"vol","max_dd","var95","cvar95","win","te","rvol20"}: return f"{v:.1f}%"
    if metric in {"rsi","adx"}: return f"{v:.0f}"
    return f"{v:.2f}" if abs(float(v)) < 10 else f"{v:.1f}"

def with_avg(value, metric, info=None):
    if value in (None, "", "—", "None"):
        return value if value not in (None, "") else "—"
    a = _avg(metric, info)
    f = _fmt_avg(metric, a)
    return f"{value} (ave. {f})" if f else value




def is_intraday_interval(interval):
    return str(interval).lower() not in ("1d", "5d", "1wk", "1mo", "3mo")


def uses_us_regular_session_symbol(symbol):
    """True for U.S.-style equities/ETFs; false for crypto, commodities, indexes, and foreign suffixes."""
    s = str(symbol or "").upper().strip()
    if not s:
        return True
    if s.startswith("^") or "=" in s or "-" in s or "." in s:
        return False
    if s.endswith("USD") and len(s) > 4:
        return False
    return True


def regular_session_only(df):
    """Keep only regular U.S. session bars, 9:30 AM to 4:00 PM New York time."""
    if df is None or df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df
    out = df.copy()
    try:
        if out.index.tz is None:
            out.index = out.index.tz_localize("America/New_York")
        else:
            out.index = out.index.tz_convert("America/New_York")
        out = out.between_time("09:30", "16:00", inclusive="left")
    except Exception:
        return df
    return out if not out.empty else df


def _figure_datetime_info(fig):
    """Return (has_datetime_x, looks_intraday) using the figure's own x-values, not sidebar state."""
    try:
        if fig is None or not getattr(fig, "data", None):
            return False, False
        for trace in fig.data:
            x = getattr(trace, "x", None)
            if x is None:
                continue
            vals = list(x)
            if not vals:
                continue

            # Numeric bar/histogram axes can be accidentally converted by
            # pandas.to_datetime into 1970 timestamps. Only treat the x-axis
            # as datetime when the original values are actually date-like.
            sample = next((v for v in vals if v is not None and str(v) not in {"", "nan", "NaT"}), None)
            if sample is None:
                continue
            is_date_like = isinstance(sample, (pd.Timestamp, datetime, np.datetime64))
            if not is_date_like and isinstance(sample, str):
                is_date_like = bool(re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}", sample))
            if not is_date_like:
                continue

            dt = pd.to_datetime(pd.Series(vals), errors="coerce")
            if dt.notna().sum() == 0:
                continue
            valid = dt.dropna()
            if valid.empty:
                continue
            intraday = bool(((valid.dt.hour != 0) | (valid.dt.minute != 0) | (valid.dt.second != 0)).any())
            return True, intraday
    except Exception:
        pass
    return False, False


def _figure_has_weekend_x(fig):
    """Detect 7-day assets so crypto/commodity charts do not hide weekend data."""
    try:
        for trace in getattr(fig, "data", []) or []:
            x = getattr(trace, "x", None)
            if x is None:
                continue
            vals = list(x)
            if not vals:
                continue
            dt = pd.to_datetime(pd.Series(vals), errors="coerce").dropna()
            if not dt.empty and bool(dt.dt.dayofweek.isin([5, 6]).any()):
                return True
    except Exception:
        pass
    return False


def apply_market_axis(fig):
    """Apply date-axis range breaks only when the figure is exchange-session data."""
    has_dt, looks_intraday = _figure_datetime_info(fig)
    if not has_dt:
        return fig

    show_ext = bool(st.session_state.get("show_ext_hours", False))
    has_weekend_data = _figure_has_weekend_x(fig)
    weekend_break = [] if has_weekend_data else [dict(bounds=["sat", "mon"])]
    if looks_intraday and not show_ext:
        fig.update_xaxes(
            rangebreaks=weekend_break + [dict(bounds=[16, 9.5], pattern="hour")],
            tickformat="%b %d<br>%I:%M %p",
            hoverformat="%b %d, %Y %I:%M %p",
        )
    elif looks_intraday:
        fig.update_xaxes(
            rangebreaks=weekend_break,
            tickformat="%b %d<br>%I:%M %p",
            hoverformat="%b %d, %Y %I:%M %p",
        )
    elif weekend_break:
        fig.update_xaxes(rangebreaks=weekend_break)
    return fig

def shead(t):
    st.markdown(f'<div class="section-head">{tr(t)}</div>', unsafe_allow_html=True)

def page_comment(title, lines):
    body = "<br>".join(lines)
    st.markdown(
        f"<div class='comment-box'><div class='comment-title'>{html.escape(title)}</div>{body}</div>",
        unsafe_allow_html=True,
    )


def score_bar(label, score):
    pct = min(100, max(0, score))
    clr = GREEN if score>=65 else AMBER if score>=40 else RED
    st.markdown(f"""
    <div class="score-bar-wrap">
      <div class="score-bar-label">
        <span>{label}</span>
        <span style="color:{clr};font-weight:600;font-family:monospace">{score}/100</span>
      </div>
      <div class="score-bar-track">
        <div style="width:{pct:.0f}%;height:100%;background:{clr};border-radius:3px"></div>
      </div>
    </div>""", unsafe_allow_html=True)

def _series_has_numeric_data(values):
    try:
        arr = pd.to_numeric(pd.Series(list(values)), errors="coerce")
        return bool(arr.notna().any())
    except Exception:
        return False


def figure_has_displayable_data(fig):
    """Return False when Plotly has no real points to show for the selected period."""
    try:
        if fig is None or not getattr(fig, "data", None):
            return False
        for trace in fig.data:
            # Scatter/Bar/Histogram style traces
            if hasattr(trace, "y") and trace.y is not None and _series_has_numeric_data(trace.y):
                return True
            if hasattr(trace, "x") and trace.x is not None and _series_has_numeric_data(trace.x):
                # Histograms often only have x-values.
                if getattr(trace, "type", "") == "histogram":
                    return True
            # Candlestick/OHLC traces do not use y directly.
            for attr in ("close", "open", "high", "low"):
                vals = getattr(trace, attr, None)
                if vals is not None and _series_has_numeric_data(vals):
                    return True
    except Exception:
        return False
    return False


def no_chart_message(extra=""):
    msg = "No chart for the period you select."
    if extra:
        msg += " " + extra
    st.info(msg)


def pchart(fig, key):
    # Keep Plotly labels clean, remove stray Plotly/Streamlit "undefined" text,
    # and compress intraday axes so hidden non-trading hours do not appear as 00:00 gaps.
    if not figure_has_displayable_data(fig):
        no_chart_message("Try a longer period or a different interval.")
        return
    preserve_legend = bool(getattr(fig.layout, "showlegend", False))
    fig.update_layout(title=dict(text=""))
    if not preserve_legend:
        fig.update_layout(showlegend=False)
    fig.update_xaxes(title=dict(text=""))
    fig.update_yaxes(title=dict(text=""))
    fig = apply_market_axis(fig)
    st.markdown(
        """<style>
        .js-plotly-plot .gtitle,
        .js-plotly-plot .xtitle,
        .js-plotly-plot .ytitle { display:none!important; }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown('</div>', unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════
#  MARKET RANKINGS / GLOBAL INDEXES
# ══════════════════════════════════════════════════════════════════
RANKING_UNIVERSES = {
    "All Industries": ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","AMD","NFLX","ORCL","CRM","NOW","ADBE","PANW","JPM","BAC","GS","MS","V","MA","XOM","CVX","COP","SLB","LLY","UNH","JNJ","MRK","PFE","WMT","COST","HD","MCD","NKE","TSM","ASML","BABA","TCEHY","NVO","SAP","SHEL","TM","SONY","SHOP","RY","BHP","RIO","HSBC","UL","PDD","JD","BIDU","MELI"],
    "Global Large Caps": ["AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","TSM","ASML","NVO","SAP","BABA","PDD","TCEHY","TM","SONY","SHEL","BP","BHP","RIO","HSBC","UL","SHOP","RY","TD","MELI","INFY","IBN"],
    "Technology": ["AAPL","MSFT","NVDA","GOOGL","META","ORCL","ADBE","CRM","NOW","PANW","CRWD","SNOW","SHOP","INTU","IBM","QCOM","AMD","AVGO","TXN","AMAT","SAP","SONY","BABA","PDD","BIDU"],
    "Semiconductors": ["NVDA","AMD","AVGO","QCOM","INTC","MU","TSM","ASML","AMAT","LRCX","KLAC","TXN","ADI","MRVL","ON","NXPI"],
    "Software": ["MSFT","ORCL","ADBE","CRM","NOW","PANW","CRWD","SNOW","DDOG","MDB","TEAM","INTU","SHOP","PLTR","NET","ZS","SAP","INFY"],
    "Financials": ["JPM","BAC","WFC","C","GS","MS","BLK","SCHW","AXP","V","MA","PYPL","COF","USB","PNC","HSBC","RY","TD","IBN"],
    "Energy": ["XOM","CVX","COP","SLB","EOG","MPC","PSX","VLO","OXY","HAL","BKR","KMI","WMB","SHEL","BP"],
    "Healthcare": ["LLY","UNH","JNJ","MRK","ABBV","PFE","TMO","ABT","DHR","ISRG","AMGN","GILD","BMY","CVS","NVO"],
    "Consumer": ["AMZN","TSLA","WMT","COST","HD","MCD","NKE","SBUX","TGT","LOW","DIS","NFLX","PEP","KO","PG","BABA","PDD","JD","TM","MELI"],
}
GLOBAL_INDEXES = [
    {"Continent": "North America", "Country": "United States", "Index": "S&P 500", "Ticker": "^GSPC"},
    {"Continent": "North America", "Country": "United States", "Index": "Nasdaq 100", "Ticker": "^NDX"},
    {"Continent": "North America", "Country": "United States", "Index": "Dow Jones", "Ticker": "^DJI"},
    {"Continent": "North America", "Country": "United States", "Index": "Russell 2000", "Ticker": "^RUT"},
    {"Continent": "North America", "Country": "United States", "Index": "VIX Volatility", "Ticker": "^VIX"},
    {"Continent": "North America", "Country": "Canada", "Index": "TSX Composite", "Ticker": "^GSPTSE"},
    {"Continent": "Asia-Pacific", "Country": "China", "Index": "Shanghai Composite", "Ticker": "000001.SS"},
    {"Continent": "Asia-Pacific", "Country": "China", "Index": "Shenzhen Component", "Ticker": "399001.SZ"},
    {"Continent": "Asia-Pacific", "Country": "Hong Kong / China", "Index": "Hang Seng", "Ticker": "^HSI"},
    {"Continent": "Asia-Pacific", "Country": "Japan", "Index": "Nikkei 225", "Ticker": "^N225"},
    {"Continent": "Asia-Pacific", "Country": "South Korea", "Index": "KOSPI", "Ticker": "^KS11"},
    {"Continent": "Asia-Pacific", "Country": "India", "Index": "Nifty 50", "Ticker": "^NSEI"},
    {"Continent": "Asia-Pacific", "Country": "Australia", "Index": "ASX 200", "Ticker": "^AXJO"},
    {"Continent": "Europe", "Country": "United Kingdom", "Index": "FTSE 100", "Ticker": "^FTSE"},
    {"Continent": "Europe", "Country": "Germany", "Index": "DAX", "Ticker": "^GDAXI"},
    {"Continent": "Europe", "Country": "France", "Index": "CAC 40", "Ticker": "^FCHI"},
    {"Continent": "Latin America", "Country": "Brazil", "Index": "Bovespa", "Ticker": "^BVSP"},
]

COMMODITIES = [
    {"Group": "Energy", "Commodity": "WTI Crude Oil", "Ticker": "CL=F", "Unit": "USD/bbl"},
    {"Group": "Energy", "Commodity": "Brent Crude Oil", "Ticker": "BZ=F", "Unit": "USD/bbl"},
    {"Group": "Metals", "Commodity": "Gold", "Ticker": "GC=F", "Unit": "USD/oz"},
    {"Group": "Metals", "Commodity": "Silver", "Ticker": "SI=F", "Unit": "USD/oz"},
    {"Group": "Metals", "Commodity": "Copper", "Ticker": "HG=F", "Unit": "USD/lb"},
    {"Group": "Energy", "Commodity": "Natural Gas", "Ticker": "NG=F", "Unit": "USD/MMBtu"},
]
def _ranking_note(pct, vol20, vol_ratio):
    if pct > 3 and vol_ratio > 1.5: return "Strong upside momentum; verify catalyst and avoid chasing extended move."
    if pct < -3 and vol_ratio > 1.5: return "Heavy selling pressure; check news, earnings, guidance, and support levels."
    if vol20 > 55: return "High volatility; suitable for active trading but position size should be smaller."
    if abs(pct) < 0.5 and vol20 < 25: return "Stable move; better for trend confirmation than short-term momentum."
    return "Moderate move; compare with sector and volume confirmation."
@st.cache_data(ttl=900, show_spinner=False)
def ai_score_universe(tickers_tuple, period="1y", model="risk_loving"):
    """Score a universe with the built-in AI thesis model, grouped by reported industry."""
    try:
        spy_hist = _fmp_ticker("SPY").history(period=period, auto_adjust=True)
    except Exception:
        spy_hist = pd.DataFrame()

    def _one(t):
        try:
            y = _fmp_ticker(t)
            h = y.history(period=period, auto_adjust=True)
            if h is None or h.empty or len(h) < 35:
                return None
            try:
                inf = y.get_info()
            except Exception:
                inf = {}
            hta   = calc_ta(h)
            risk  = calc_risk(h, spy_hist)
            scores = score_from_metrics(inf, risk, hta, model=model)
            close  = h["Close"].dropna()
            last_price = safe_float(close.iloc[-1], 0) if len(close) else 0
            ret_3m = 0.0
            if len(close) > 63 and close.iloc[-64]:
                ret_3m = (close.iloc[-1] / close.iloc[-64] - 1) * 100
            return {
                "Ticker": t,
                "Company": str(inf.get("shortName") or inf.get("longName") or t)[:46],
                "Sector": inf.get("sector") or "Unknown",
                "Industry": inf.get("industry") or "Unknown",
                "Country": inf.get("country") or "Unknown",
                "Market Cap $B": round(safe_float(inf.get("marketCap"), 0) / 1e9, 2),
                "Last Price": round(last_price, 2),
                "AI Score": scores.get("overall_score", 0),
                "Recommendation": scores.get("recommendation_model", "Hold"),
                "Model": scores.get("model_name", AI_RISK_MODEL_NAMES.get(model, model)),
                "Growth": scores.get("growth_score", 0),
                "Momentum": scores.get("momentum_score", 0),
                "Quality": scores.get("quality_score", 0),
                "Valuation": scores.get("valuation_score", 0),
                "Risk Score": scores.get("risk_score", 0),
                "3M Return %": round(ret_3m, 2),
                "Sharpe": risk.get("sharpe", 0),
                "Max Drawdown %": risk.get("max_dd", 0),
                "Annual Vol %": risk.get("vol", 0),
                "Why It Scores This Way": (
                    f"Growth {scores.get('growth_score', 0)}/100 and momentum {scores.get('momentum_score', 0)}/100 "
                    f"are scored under the {AI_RISK_MODEL_NAMES.get(model, model)} model; quality {scores.get('quality_score', 0)}/100, "
                    f"valuation {scores.get('valuation_score', 0)}/100, and risk {scores.get('risk_score', 0)}/100 adjust the final score."
                ),
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=min(len(tickers_tuple), 8)) as ex:
        results = list(ex.map(_one, tickers_tuple))
    df = pd.DataFrame([r for r in results if r is not None])
    if not df.empty:
        df = df.sort_values(["Industry", "AI Score"], ascending=[True, False]).reset_index(drop=True)
    return df

def ai_score_universe(tickers_tuple, period="1y", model="risk_loving"):
    """Score a universe with the same built-in AI thesis model, grouped by reported industry."""
    rows = []
    try:
        spy_hist = _fmp_ticker("SPY").history(period=period, auto_adjust=True)
    except Exception:
        spy_hist = pd.DataFrame()
    for t in tickers_tuple:
        try:
            y = _fmp_ticker(t)
            h = y.history(period=period, auto_adjust=True)
            if h is None or h.empty or len(h) < 35:
                continue
            try:
                inf = y.get_info()
            except Exception:
                inf = {}
            hta = calc_ta(h)
            risk = calc_risk(h, spy_hist)
            scores = score_from_metrics(inf, risk, hta, model=model)
            close = h["Close"].dropna()
            last_price = safe_float(close.iloc[-1], 0) if len(close) else 0
            ret_3m = 0.0
            if len(close) > 63 and close.iloc[-64]:
                ret_3m = (close.iloc[-1] / close.iloc[-64] - 1) * 100
            rows.append({
                "Ticker": t,
                "Company": str(inf.get("shortName") or inf.get("longName") or t)[:46],
                "Sector": inf.get("sector") or "Unknown",
                "Industry": inf.get("industry") or "Unknown",
                "Country": inf.get("country") or "Unknown",
                "Market Cap $B": round(safe_float(inf.get("marketCap"), 0) / 1e9, 2),
                "Last Price": round(last_price, 2),
                "AI Score": scores.get("overall_score", 0),
                "Recommendation": scores.get("recommendation_model", "Hold"),
                "Model": scores.get("model_name", AI_RISK_MODEL_NAMES.get(model, model)),
                "Growth": scores.get("growth_score", 0),
                "Momentum": scores.get("momentum_score", 0),
                "Quality": scores.get("quality_score", 0),
                "Valuation": scores.get("valuation_score", 0),
                "Risk Score": scores.get("risk_score", 0),
                "3M Return %": round(ret_3m, 2),
                "Sharpe": risk.get("sharpe", 0),
                "Max Drawdown %": risk.get("max_dd", 0),
                "Annual Vol %": risk.get("vol", 0),
                "Why It Scores This Way": (
                    f"Growth {scores.get('growth_score', 0)}/100 and momentum {scores.get('momentum_score', 0)}/100 "
                    f"are scored under the {AI_RISK_MODEL_NAMES.get(model, model)} model; quality {scores.get('quality_score', 0)}/100, "
                    f"valuation {scores.get('valuation_score', 0)}/100, and risk {scores.get('risk_score', 0)}/100 adjust the final score."
                ),
            })
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["Industry", "AI Score"], ascending=[True, False]).reset_index(drop=True)
    return df
@st.cache_data(ttl=1800, show_spinner=False)
def index_snapshot(period="1mo"):
    rows = []
    curves = {}
    for order, meta in enumerate(GLOBAL_INDEXES):
        name, sym = meta["Index"], meta["Ticker"]
        try:
            h = _fmp_ticker(sym).history(period=period, auto_adjust=True)
            if h is None or h.empty or len(h) < 2:
                continue
            close = h["Close"].dropna()
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            chg = last - prev
            pct = (last / prev - 1) * 100 if prev else 0.0
            ret = close.pct_change().dropna()
            vol20 = float(ret.tail(20).std() * np.sqrt(252) * 100) if len(ret) >= 2 else 0.0
            rows.append({
                "Order": order,
                "Continent": meta["Continent"],
                "Country": meta["Country"],
                "Index": name,
                "Ticker": sym,
                "Last Price": round(last, 2),
                "Change $": round(chg, 2),
                "Change %": round(pct, 2),
                "20D Vol %": round(vol20, 2),
            })
            curves[f"{name} ({meta['Country']})"] = (close / close.iloc[0] * 100).round(2)
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Order").drop(columns=["Order"]).reset_index(drop=True)
    return df, curves

@st.cache_data(ttl=1800, show_spinner=False)
def commodity_snapshot(period="3mo"):
    rows = []
    curves = {}
    for meta in COMMODITIES:
        name, sym = meta["Commodity"], meta["Ticker"]
        try:
            h = _fmp_ticker(sym).history(period=period, auto_adjust=True)
            if h is None or h.empty or len(h) < 2:
                continue
            close = h["Close"].dropna()
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            chg = last - prev
            pct = (last / prev - 1) * 100 if prev else 0.0
            ret = close.pct_change().dropna()
            vol20 = float(ret.tail(20).std() * np.sqrt(252) * 100) if len(ret) >= 2 else 0.0
            ma20 = float(close.tail(20).mean()) if len(close) >= 20 else float(close.mean())
            ma50 = float(close.tail(50).mean()) if len(close) >= 50 else float(close.mean())
            rsi_val = 50.0
            try:
                rsi_series = ta.momentum.rsi(close, window=14)
                clean_rsi = rsi_series.dropna()
                rsi_val = float(clean_rsi.iloc[-1]) if not clean_rsi.empty else 50.0
            except Exception:
                pass
            trend = "Bullish" if last > ma20 > ma50 else "Bearish" if last < ma20 < ma50 else "Mixed"
            v = h["Volume"].dropna() if "Volume" in h else pd.Series(dtype=float)
            vol_ratio = float(v.iloc[-1] / v.tail(20).mean()) if len(v) >= 5 and v.tail(20).mean() else 0.0
            rows.append({
                "Group": meta["Group"], "Commodity": name, "Ticker": sym, "Unit": meta["Unit"],
                "Last Price": round(last, 2), "Change $": round(chg, 2), "Change %": round(pct, 2),
                "20D Vol %": round(vol20, 2), "RSI 14": round(rsi_val, 1),
                "MA20": round(ma20, 2), "MA50": round(ma50, 2), "Trend": trend,
                "Volume Ratio": round(vol_ratio, 2),
            })
            curves[name] = (close / close.iloc[0] * 100).round(2)
        except Exception:
            continue
    return pd.DataFrame(rows), curves
def ranking_bar_chart(df, metric, title="", ascending=False):
    fig = go.Figure()
    if df is not None and not df.empty and metric in df.columns:
        d = df.sort_values(metric, ascending=ascending).copy()
        xcol = "Ticker" if "Ticker" in d.columns else ("Index" if "Index" in d.columns else d.columns[0])
        # Always pass Plotly plain lists. This avoids Narwhals/DuplicateError when
        # a DataFrame has duplicate names such as both old/new Ticker columns.
        if "Company" in d.columns:
            hover = d["Company"].astype(str).tolist()
        elif "Index" in d.columns:
            hover = d["Index"].astype(str).tolist()
        else:
            hover = d[xcol].astype(str).tolist()
        custom = d[xcol].astype(str).tolist()
        fig.add_trace(go.Bar(
            x=custom,
            y=pd.to_numeric(d[metric], errors="coerce").fillna(0).tolist(),
            customdata=custom,
            hovertext=hover,
            hovertemplate="Click to open: %{customdata}<br>" + metric + ": %{y:.2f}<br>%{hovertext}<extra></extra>",
            marker_color=BLUE,
        ))
    lout = base_layout(height=320, title="")
    lout["margin"] = dict(l=20, r=30, t=16, b=40)
    fig.update_layout(**lout)
    fig.update_yaxes(side="right", gridcolor=GRID_COL)
    return fig


def clickable_rank_chart(fig, key):
    """Render a ranking bar chart. Clicking a U.S.-listed ticker bar jumps to Overview."""
    if not figure_has_displayable_data(fig):
        no_chart_message("No ranking data is available for this filter.")
        return
    fig.update_layout(title=dict(text=""), showlegend=False, clickmode="event+select")
    fig.update_xaxes(title=dict(text=""))
    fig.update_yaxes(title=dict(text=""))
    st.markdown(
        """<style>
        .js-plotly-plot .gtitle,
        .js-plotly-plot .xtitle,
        .js-plotly-plot .ytitle { display:none!important; }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="pro-chart-shell">', unsafe_allow_html=True)
    try:
        event = st.plotly_chart(
            fig,
            use_container_width=True,
            key=key,
            on_select="rerun",
            selection_mode="points",
        )
        pts = event.get("selection", {}).get("points", []) if isinstance(event, dict) else []
        if pts:
            sym = str(pts[0].get("customdata") or pts[0].get("x") or "").strip().upper()
            if sym and all(ch not in sym for ch in ["=", "^", "."]):
                st.session_state.ticker = sym
                st.session_state["section_nav"] = "overview"
                st.rerun()
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown('</div>', unsafe_allow_html=True)


def index_curves_chart(curves):
    fig = go.Figure()
    palette = ["#ffffff", "#facc15", GREEN, BLUE, AMBER, PURPLE, TEAL, RED, "#fb923c", "#f472b6", "#a3e635"]
    for i, (name, ser) in enumerate(curves.items()):
        fig.add_trace(go.Scatter(
            x=ser.index,
            y=ser.values,
            mode="lines",
            name=name,
            line=dict(width=2.1, color=palette[i % len(palette)]),
            hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
        ))
    lout = base_layout(height=430, title="")
    # Put the legend beside the chart instead of floating over the plot area.
    lout["showlegend"] = True
    lout["legend"] = dict(
        orientation="v",
        yanchor="top", y=1,
        xanchor="left", x=1.03,
        font=dict(size=10, color=TEXT_COL),
        bgcolor="#13161e",
        bordercolor="#252a38",
        borderwidth=1,
        itemwidth=30,
    )
    lout["margin"] = dict(l=20, r=245, t=20, b=36)
    fig.update_layout(**lout)
    fig.update_yaxes(title="Normalized to 100", side="right", gridcolor=GRID_COL)
    return fig


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main():

    # ── Sidebar ────────────────────────────────────────────────────
    with st.sidebar:
        # Professional static product header.
        st.markdown("""
        <div style="padding:0.45rem 0 0.75rem;border-bottom:1px solid #1f2937;margin-bottom:0.65rem;">
          <div style="font-size:18px;font-weight:760;color:#e5e7eb;letter-spacing:-0.025em;line-height:1.12;">
            SmartStock</div>
          <div style="font-size:9px;color:#64748b;margin-top:5px;letter-spacing:0.12em;font-weight:650;">
            EQUITY RESEARCH · RISK · NEWS</div>
        </div>""", unsafe_allow_html=True)

        if "ticker" not in st.session_state:
            st.session_state.ticker = "NVDA"

        st.markdown(f'<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    f'letter-spacing:0.1em;margin:0.2rem 0 0.45rem">{tr("Ticker Symbol")}</div>',
                    unsafe_allow_html=True)
        ticker_input = st.text_input("Direct ticker symbol", value=st.session_state.ticker,
                                     placeholder="AAPL, MSFT, TSLA…",
                                     label_visibility="collapsed",
                                     help="Type a ticker directly, or use company-name search below.").upper().strip()
        if ticker_input:
            st.session_state.ticker = ticker_input

        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.1em;margin:0.6rem 0 0.45rem">Search Company by Name</div>', unsafe_allow_html=True)
        company_query = st.text_input(
            "Company keyword search",
            value=st.session_state.get("company_search_query", ""),
            placeholder="apple, microsoft, nvidia, service now…",
            label_visibility="collapsed",
            key="company_search_query",
            help="Search by company name or keyword. Results are ordered by market cap when FMP provides market cap.",
        ).strip()
        if company_query:
            search_rows = search_companies_by_keyword(company_query, max_results=12)
            if search_rows:
                label_map = {_company_search_label(r): r["Ticker"] for r in search_rows}
                selected_company = st.selectbox(
                    "Matching companies",
                    list(label_map.keys()),
                    index=0,
                    label_visibility="collapsed",
                    key="company_search_dropdown",
                )
                if st.button("Use selected company", key="use_company_search_result", use_container_width=True):
                    st.session_state.ticker = label_map[selected_company]
                    st.session_state["section_nav"] = "overview"
                    st.rerun()
            else:
                st.caption("No company matches found. Try a broader keyword or type the ticker directly.")

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # ── Manual Refresh button (top of sidebar, always visible) ──
        if st.button(
            "⟳  Refresh Data",
            type="primary",
            use_container_width=True,
            help="Clear all cached prices, indicators, and fundamentals and re-fetch from FMP.",
        ):
            fetch_stock.clear()
            fetch_chart_history.clear()
            _fmp_build_info.clear()
            calc_ta.clear()
            calc_risk.clear()
            fetch_news_items.clear()
            fetch_market_news.clear()
            fetch_spy.clear()
            st.session_state["_last_manual_refresh"] = datetime.now().strftime("%H:%M:%S")
            st.rerun()

        _last = st.session_state.get("_last_manual_refresh")
        if _last:
            st.caption(f"↺ Last refreshed at {_last}")
        else:
            st.caption("Data is cached · press Refresh for latest prices.")

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    'letter-spacing:0.1em;margin-bottom:8px">Historical Data Range</div>',
                    unsafe_allow_html=True)
        period_map = {"3 Months":"3mo","6 Months":"6mo","1 Year":"1y","2 Years":"2y","5 Years":"5y","10 Years":"10y","20 Years":"20y","Max":"max"}
        period_label = st.selectbox(tr("Data period"), list(period_map.keys()),
                                    index=0, label_visibility="collapsed")
        period = period_map[period_label]

        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    'letter-spacing:0.1em;margin-bottom:8px;margin-top:10px">Chart View Window</div>',
                    unsafe_allow_html=True)
        window_map = {
            "Today intraday (5-minute bars)":     {"period":"1d", "interval":"5m",  "points":99999},
            "Today + Yesterday (5-minute bars)": {"period":"2d", "interval":"5m",  "points":99999},
            "5 Days intraday (15-minute bars)":  {"period":"5d", "interval":"15m", "points":99999},
            "10 Days intraday (30-minute bars)": {"period":"10d","interval":"30m", "points":99999},
            "1 Month  (daily bars)":             {"period":"1mo","interval":"1d",  "points":99999},
            "3 Months (daily bars)":             {"period":"3mo","interval":"1d",  "points":99999},
            "6 Months (daily bars)":             {"period":"6mo","interval":"1d",  "points":99999},
            "1 Year   (daily bars)":             {"period":"1y", "interval":"1d",  "points":99999},
            "2 Years  (daily bars)":             {"period":"2y", "interval":"1d",  "points":99999},
            "5 Years  (daily bars)":             {"period":"5y", "interval":"1d",  "points":99999},
            "10 Years (daily bars)":             {"period":"10y","interval":"1d",  "points":99999},
            "20 Years (daily bars)":             {"period":"20y","interval":"1d",  "points":99999},
            "All available daily data":          {"period":period,"interval":"1d",  "points":99999},
        }
        window_label = st.selectbox(tr("Chart window"), list(window_map.keys()),
                                    index=5, label_visibility="collapsed")
        chart_cfg = window_map[window_label]
        chart_days = chart_cfg["points"]
        show_ext_hours = st.checkbox(
            tr("Show pre-market / after-hours curve"),
            value=False,
            help="Only affects intraday windows. It includes extended-hours bars when FMP provides them."
        )
        chart_is_intraday = is_intraday_interval(chart_cfg["interval"])
        st.session_state["chart_is_intraday"] = chart_is_intraday
        st.session_state["show_ext_hours"] = show_ext_hours
        if chart_is_intraday and not show_ext_hours:
            st.caption(tr("Regular-hours view: 9:30 AM–4:00 PM ET only. Overnight gaps are removed from the x-axis."))

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    'letter-spacing:0.1em;margin-bottom:10px">Price Chart Overlays</div>',
                    unsafe_allow_html=True)
        show_bb      = st.checkbox("Bollinger Bands (20, ±2σ)", value=False)
        show_vol_sub = st.checkbox("Volume & Volatility Panel",  value=True)

        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    'letter-spacing:0.1em;margin:12px 0 8px">Moving Average Lines</div>',
                    unsafe_allow_html=True)
        ma_defaults = {"MA5":True,"MA10":False,"MA20":True,
                       "MA50":False,"MA120":True,"MA200":False}
        _ma_unit = "Bar" if is_intraday_interval(chart_cfg["interval"]) else "Day"
        ma_labels   = {"MA5":f"5-{_ma_unit} SMA","MA10":f"10-{_ma_unit} SMA","MA20":f"20-{_ma_unit} SMA",
                       "MA50":f"50-{_ma_unit} SMA","MA120":f"120-{_ma_unit} SMA","MA200":f"200-{_ma_unit} SMA"}
        active_mas = []
        for ma in ["MA5","MA10","MA20","MA50","MA120","MA200"]:
            current_color = st.session_state.get(f"color_{ma}", MA_COLORS[ma])
            col_dot, col_chk = st.columns([1,9])
            col_dot.markdown(
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{current_color};margin-top:10px"></div>',
                unsafe_allow_html=True)
            enabled = col_chk.checkbox(ma_labels[ma], value=ma_defaults[ma], key=f"ma_{ma}")
            if enabled:
                active_mas.append(ma)

        with st.expander("MA colors", expanded=False):
            for ma in ["MA5","MA10","MA20","MA50","MA120","MA200"]:
                picked_color = st.color_picker(
                    f"{ma} color",
                    value=st.session_state.get(f"color_{ma}", MA_COLORS[ma]),
                    key=f"color_{ma}",
                )
                MA_COLORS[ma] = picked_color

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">AI Score Model</div>', unsafe_allow_html=True)
        render_ai_model_selector("", key="ai_model_sidebar")
        st.caption(ai_model_description())
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        if st.session_state.get("section_nav", "overview") != "overview":
            if st.button("← Back to Overview", key="sidebar_back_overview", use_container_width=True):
                st.session_state["section_nav"] = "overview"
                st.rerun()
        with st.expander("Data / disclaimer", expanded=False):
            st.markdown('<div style="font-size:10px;color:#334155;line-height:1.7">'
                        'Price data: FMP API<br>Indicators: ta library<br>'
                        f'Risk-free rate for Sharpe/alpha: {RISK_FREE_ANNUAL_RATE:.2%} '
                        '(set SMARTSTOCK_RISK_FREE_RATE to change)<br>'
                        'AI Thesis: built-in rule engine<br>⚠️ Not financial advice.</div>',
                        unsafe_allow_html=True)

    ticker = str(st.session_state.ticker).upper().strip()
    st.session_state.ticker = ticker

    # ── Fetch ──────────────────────────────────────────────────────
    # Only show a loading indicator when the ticker or period genuinely changes.
    # All other interactions (tab switches, checkboxes, dropdowns on the same
    # ticker) hit the @st.cache_data cache instantly → no grey overlay, no freeze.
    _load_key = (ticker, period)
    _is_fresh_load = st.session_state.get("_last_load_key") != _load_key
    if _is_fresh_load:
        with st.spinner(f"Loading {ticker}…"):
            data, err = fetch_stock(ticker, period)
        if not err and data:
            st.session_state["_last_load_key"] = _load_key
    else:
        data, err = fetch_stock(ticker, period)  # guaranteed instant cache hit

    if err or not data:
        st.error(f"**{ticker}**: {err or 'Not found'}"); return

    info = data["info"]; hist = data["hist"]

    # Per-section data is loaded after the navigation radio below, so first-click
    # navigation never shows empty/stale charts or indicators.
    chart_hist = hist
    chart_ta = pd.DataFrame()
    hist_ta = pd.DataFrame()
    risk = calc_risk(hist, None)

    # ── Header ─────────────────────────────────────────────────────
    name = info.get("longName", ticker)
    hist_close = pd.to_numeric(hist.get("Close", pd.Series(dtype=float)), errors="coerce").dropna()
    fallback_price = float(hist_close.iloc[-1]) if len(hist_close) else 0.0
    price = float(info.get("currentPrice") or info.get("regularMarketPrice") or fallback_price)
    prev_candidate = info.get("previousClose")
    if prev_candidate in (None, "", 0, 0.0) and len(hist_close) >= 2:
        prev_candidate = hist_close.iloc[-2]
    prev = float(prev_candidate or price or 1.0)
    chg = price - prev
    chg_pct = (chg / prev * 100) if prev else 0.0
    chg_clr = GREEN if chg >= 0 else RED
    sign = "+" if chg >= 0 else ""

    last_index = hist.index[-1] if isinstance(hist, pd.DataFrame) and not hist.empty else datetime.now()
    last_stamp = last_index.strftime('%b %d, %Y %H:%M') if hasattr(last_index, 'strftime') else datetime.now().strftime('%b %d, %Y')
    st.markdown(f"""
    <div class="top-header">
      <div>
        <div class="top-header-name">{html.escape(str(name))}</div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <span class="ticker-badge">{html.escape(str(ticker))}</span>
          <span class="exchange-badge">{html.escape(str(info.get('exchange','')))}</span>
          <span class="exchange-badge">{html.escape(str(info.get('sector','')))}</span>
          <span class="exchange-badge">{html.escape(str(info.get('industry','')))}</span>
        </div>
      </div>
      <div class="top-header-price">
        <div class="top-header-price-main">${price:,.2f}</div>
        <div style="font-size:1.05rem;font-weight:600;color:{chg_clr};font-family:monospace;margin-top:6px;white-space:nowrap">
          {sign}{chg:.2f} &nbsp; ({sign}{chg_pct:.2f}%)</div>
        <div style="font-size:11px;color:#334155;margin-top:5px;white-space:nowrap">{last_stamp} · FMP API</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header-divider"></div>', unsafe_allow_html=True)

    ms = st.columns(6)
    ms[0].metric("Market Cap",  fmtn(info.get("marketCap"),"$"))
    ms[1].metric("P/E (TTM)",   with_avg(f"{info.get('trailingPE',0):.1f}" if info.get("trailingPE") else "—", "pe", info))
    ms[2].metric("52W High",    f"${info.get('fiftyTwoWeekHigh',0):.2f}" if info.get("fiftyTwoWeekHigh") else "—")
    ms[3].metric("52W Low",     f"${info.get('fiftyTwoWeekLow',0):.2f}"  if info.get("fiftyTwoWeekLow")  else "—")
    ms[4].metric("Avg Volume",  fmtn(info.get("averageVolume")))
    ms[5].metric("Div Yield",   with_avg(fpct(info.get("dividendYield")) if info.get("dividendYield") is not None else "—", "div_yield", info))
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── PROFESSIONAL SECTION NAVIGATION ────────────────────────────
    # Tab order: Company → Company AI → Market-wide → Global → Tools
    SECTION_KEYS = [
        # ── Company ──────────────────────────────────────────────
        "overview", "valuation", "risk", "industry", "technical", "comparison",
        "news",
        # ── Company AI (stock-specific) ───────────────────────────
        "ai_thesis", "investor_view",
        # ── Market-wide ───────────────────────────────────────────
        "market_news", "market_rankings",
        # ── Global ────────────────────────────────────────────────
        "global_indexes", "commodities",
        # ── Tools ─────────────────────────────────────────────────
        "bond_calculator", "option_calculator",
    ]
    SECTION_LABELS = {
        "overview":          f"📊 {tr('Overview')}",
        "valuation":         f"💰 {tr('Valuation')}",
        "risk":              f"⚠️ {tr('Risk')}",
        "industry":          f"🏭 {tr('Industry')}",
        "technical":         f"📉 {tr('Technical')}",
        "comparison":        f"🔁 {tr('Comparison')}",
        "news":              f"📰 {tr('Company News')}",
        "ai_thesis":         f"🤖 {tr('AI Thesis')}",
        "investor_view":     f"🧠 {tr('Investor View')}",
        "market_news":       f"🌐 {tr('Market News')}",
        "market_rankings":   f"🏆 {tr('Market Rankings')}",
        "global_indexes":    f"🌍 {tr('Global Indexes')}",
        "commodities":       f"🛢️ {tr('Commodities')}",
        "bond_calculator":   "🧾 Bond Calculator",
        "option_calculator": "📐 Option Calculator",
    }
    if st.session_state.get("section_nav") not in SECTION_KEYS:
        st.session_state["section_nav"] = "overview"

    if st.session_state.get("section_nav") != "overview":
        st.markdown('<div class="pro-back-row">', unsafe_allow_html=True)
        if st.button("← Back to Overview", key="main_back_overview", use_container_width=False):
            st.session_state["section_nav"] = "overview"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pro-subnav"><div class="pro-subnav-title">Terminal Navigation</div>', unsafe_allow_html=True)
    active_tab = st.radio(
        "Terminal Navigation",
        SECTION_KEYS,
        key="section_nav",
        horizontal=True,
        label_visibility="collapsed",
        format_func=lambda k: SECTION_LABELS.get(k, k),
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Load the exact data needed by the selected section after active_tab is known.
    if active_tab == "overview":
        chart_hist, chart_err = fetch_chart_history(ticker, chart_cfg["period"], chart_cfg["interval"], show_ext_hours)
        if chart_err or chart_hist is None or chart_hist.empty:
            chart_hist = hist
            st.warning(f"Recent chart data was unavailable, so the chart fell back to {period_label}: {chart_err}")
        elif chart_is_intraday and not show_ext_hours and uses_us_regular_session_symbol(ticker):
            chart_hist = regular_session_only(chart_hist)
        chart_ta = calc_ta(chart_hist)

    if active_tab == "ai_thesis":
        hist_ta = calc_ta(hist)

    if active_tab in {"industry", "ai_thesis"}:
        spy = fetch_spy(period)
        risk = calc_risk(hist, spy)

    # ══════════ SECTION 1 — OVERVIEW ═══════════════════════════════
    if active_tab == "overview":
        shead("Price Chart")

        # Build legend for price chart
        leg_items = [("Candle Up", GREEN, "bar"), ("Candle Down", RED, "bar")]
        if show_bb:
            leg_items += [("BB Upper/Lower", PURPLE, "dash"), ("BB Mid", PURPLE, "line")]
        for ma in active_mas:
            leg_items.append((ma_labels[ma], MA_COLORS[ma], "line"))
        if show_vol_sub:
            leg_items += [("Volume (green=up, red=down)", GREEN, "bar"),
                          ("Volume MA20", AMBER, "line"),
                          ("Ann. Volatility 20d", PURPLE, "dash")]
        st.markdown(legend_html(leg_items), unsafe_allow_html=True)
        pchart(price_chart(chart_ta, ticker, chart_days, active_mas, show_bb, show_vol_sub),
               "chart_price")

        shead("Fundamentals")
        fund_items = [
            ("Revenue",        fmtn(info.get("totalRevenue"),"$")),
            ("Net Income",     fmtn(info.get("netIncomeToCommon"),"$")),
            ("EBITDA",         fmtn(info.get("ebitda"),"$")),
            ("Free Cash Flow", fmtn(info.get("freeCashflow"),"$")),
            ("EPS (TTM)",      f"${info.get('trailingEps',0):.2f}" if info.get("trailingEps") else "—"),
            ("Forward EPS",    f"${info.get('forwardEps',0):.2f}"  if info.get("forwardEps")  else "—"),
            ("Gross Margin",   with_avg(fpct(info.get("grossMargins")), "gross_margin", info)),
            ("Net Margin",     with_avg(fpct(info.get("profitMargins")), "net_margin", info)),
            ("Op. Margin",     with_avg(fpct(info.get("operatingMargins")), "op_margin", info)),
            ("Rev Growth YoY", with_avg(fpct(info.get("revenueGrowth")), "rev_growth", info)),
            ("EPS Growth",     with_avg(fpct(info.get("earningsGrowth")), "eps_growth", info)),
            ("ROE",            with_avg(fpct(info.get("returnOnEquity")), "roe", info)),
            ("ROA",            with_avg(fpct(info.get("returnOnAssets")), "roa", info)),
            ("Total Debt",     fmtn(info.get("totalDebt"),"$")),
            ("Total Cash",     fmtn(info.get("totalCash"),"$")),
            ("Debt/Equity",    with_avg(f"{info.get('debtToEquity',0)/100:.2f}" if info.get("debtToEquity") else "—", "debt_equity", info)),
            ("Current Ratio",  with_avg(f"{info.get('currentRatio',0):.2f}" if info.get("currentRatio") else "—", "current_ratio", info)),
            ("Quick Ratio",    with_avg(f"{info.get('quickRatio',0):.2f}" if info.get("quickRatio") else "—", "quick_ratio", info)),
            ("Book Value/Sh",  f"${info.get('bookValue',0):.2f}"       if info.get("bookValue")    else "—"),
            ("Payout Ratio",   fpct(info.get("payoutRatio"))           if info.get("payoutRatio")  else "—"),
            ("Beta",           with_avg(f"{info.get('beta',0):.2f}" if info.get("beta") else "—", "beta", info)),
            ("Short % Float",  fpct(info.get("shortPercentOfFloat"))   if info.get("shortPercentOfFloat") else "—"),
            ("Shares Out",     fmtn(info.get("sharesOutstanding"))),
            ("Float",          fmtn(info.get("floatShares"))),
        ]
        cols_f = st.columns(4)
        for i,(lbl,val) in enumerate(fund_items):
            cols_f[i%4].metric(lbl,val)

        shead("About")
        with st.expander("Business Summary", expanded=True):
            st.markdown(f'<div style="font-size:14px;color:#94a3b8;line-height:1.8">'
                        f'{info.get("longBusinessSummary","—")}</div>', unsafe_allow_html=True)
        ba,bb2,bc,bd = st.columns(4)
        offs = info.get("companyOfficers",[])
        for col,lbl,val in [
            (ba,"CEO",offs[0].get("name","—") if offs else "—"),
            (bb2,"Sector",info.get("sector","—")),
            (bc,"Employees",f"{info.get('fullTimeEmployees',0):,}" if info.get("fullTimeEmployees") else "—"),
            (bd,"Country",info.get("country","—")),
        ]:
            col.markdown(f'<div class="stat-label">{lbl}</div>'
                         f'<div style="font-size:13px;color:#e2e8f0;margin-top:2px">{val}</div>',
                         unsafe_allow_html=True)

        page_comment("Reading this page", ["<b>Price trend:</b> rising price above MA20/MA50 usually confirms near-term momentum; a break below them can mean trend weakness.", "<b>Volume:</b> rising volume during a move gives stronger confirmation than price movement alone.", "<b>Fundamentals:</b> margins, growth, debt, and cash flow should be read together; one strong number does not make the stock low-risk."])

    # ══════════ TAB 2 — VALUATION ═════════════════════════════════
    if active_tab == "valuation":
        pe=info.get("trailingPE"); fpe=info.get("forwardPE")
        pb=info.get("priceToBook"); ps=info.get("priceToSalesTrailing12Months")
        peg=info.get("pegRatio"); evE=info.get("enterpriseToEbitda"); evR=info.get("enterpriseToRevenue")

        v_left,v_right = st.columns(2)
        with v_left:
            shead("Valuation Multiples")
            for lbl,val,clr,hint in [
                ("Trailing P/E", with_avg(f"{pe:.1f}" if pe else "—", "pe", info),
                 GREEN if pe and pe<18 else RED if pe and pe>30 else AMBER,"< 18 cheap · > 30 expensive"),
                ("Forward P/E",  with_avg(f"{fpe:.1f}" if fpe else "—", "fpe", info), AMBER,"Forward earnings multiple"),
                ("PEG Ratio",    with_avg(f"{peg:.2f}" if peg else "—", "peg", info),
                 GREEN if peg and peg<1 else AMBER if peg and peg<2 else RED,"< 1 undervalued vs growth"),
                ("Price / Book", with_avg(f"{pb:.2f}" if pb else "—", "pb", info),
                 GREEN if pb and pb<1 else AMBER if pb and pb<3 else RED,"< 1 trades below book"),
                ("Price / Sales",with_avg(f"{ps:.2f}" if ps else "—", "ps", info), AMBER,"Revenue multiple"),
                ("EV / EBITDA",  with_avg(f"{evE:.1f}" if evE else "—", "ev_ebitda", info),
                 GREEN if evE and evE<12 else AMBER if evE and evE<20 else RED,"< 10 cheap · > 20 expensive"),
                ("EV / Revenue", with_avg(f"{evR:.2f}" if evR else "—", "ev_rev", info), AMBER,"Enterprise to revenue"),
            ]:
                c1,c2,c3 = st.columns([3,2,4])
                c1.markdown(f'<div style="font-size:13px;color:#94a3b8;padding:8px 0">{lbl}</div>', unsafe_allow_html=True)
                c2.markdown(f'<div style="font-size:13px;font-family:monospace;font-weight:600;color:{clr};padding:8px 0">{val}</div>', unsafe_allow_html=True)
                c3.markdown(f'<div style="font-size:11px;color:#475569;padding:8px 0">{hint}</div>', unsafe_allow_html=True)
                st.markdown('<div style="height:1px;background:#1a1e2a"></div>', unsafe_allow_html=True)

        with v_right:
            shead("Analyst Consensus")
            tl=float(info.get("targetLowPrice",0) or 0)
            tm=float(info.get("targetMeanPrice",0) or 0)
            th=float(info.get("targetHighPrice",0) or 0)
            na=int(info.get("recommendationAnalystCount") or info.get("numberOfAnalystOpinions",0) or 0)
            rk_raw=(info.get("recommendationKey") or "").strip()
            rm_raw=info.get("recommendationMean", None)
            source=(info.get("recommendationSource") or "").strip()
            has_rec = bool(rk_raw and rm_raw not in (None, "", 0, 0.0) and na > 0)
            has_targets = bool(tm and tm > 0)

            if has_rec:
                rk=rk_raw.replace("_", " ").title()
                rm=float(rm_raw)
                rc=GREEN if rm<=2 else RED if rm>=4 else AMBER
                up=(tm/price-1)*100 if price and tm else 0
                up_c=GREEN if up>0 else RED
                st.markdown(f"""
                <div style="background:#13161e;border:1px solid #1e2433;border-radius:12px;
                            padding:1.5rem;margin-bottom:1rem;text-align:center">
                  <div style="font-size:10px;color:#475569;text-transform:uppercase;
                              letter-spacing:0.1em;margin-bottom:10px">Analyst Consensus · {na} Analysts</div>
                  <div style="font-size:2.5rem;font-weight:800;color:{rc};letter-spacing:-0.02em">{rk}</div>
                  <div style="font-size:12px;color:#475569;margin-top:6px">
                    Score {rm:.1f}/5.0 &nbsp;(1=Strong Buy · 5=Strong Sell)</div>
                  <div style="font-size:10px;color:#334155;margin-top:8px">Source: {source or "FMP analyst consensus"}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
                  <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">LOW TARGET</div>
                    <div style="font-size:1.2rem;font-weight:600;color:{RED};font-family:monospace">{("$" + format(tl, ".0f")) if tl else "—"}</div>
                  </div>
                  <div style="background:#13161e;border:1px solid #252a38;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">CONSENSUS</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{GREEN};font-family:monospace">{("$" + format(tm, ".0f")) if tm else "—"}</div>
                  </div>
                  <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">HIGH TARGET</div>
                    <div style="font-size:1.2rem;font-weight:600;color:{GREEN};font-family:monospace">{("$" + format(th, ".0f")) if th else "—"}</div>
                  </div>
                </div>
                <div style="text-align:center;font-size:1.1rem;font-weight:700;
                            color:{up_c};font-family:monospace">
                  {("▲" if up>0 else "▼") if tm else ""} {f"{abs(up):.1f}% implied upside" if tm else "No price-target upside available"}</div>
                """, unsafe_allow_html=True)
            else:
                up=(tm/price-1)*100 if price and tm else 0
                up_c=GREEN if up>0 else RED
                subtitle = "FMP returned price targets, but no analyst-count/rating breakdown." if has_targets else "No analyst consensus data returned by FMP for this ticker or plan."
                st.markdown(f"""
                <div style="background:#13161e;border:1px solid #1e2433;border-radius:12px;
                            padding:1.5rem;margin-bottom:1rem;text-align:center">
                  <div style="font-size:10px;color:#475569;text-transform:uppercase;
                              letter-spacing:0.1em;margin-bottom:10px">Analyst Consensus</div>
                  <div style="font-size:2rem;font-weight:800;color:{TEXT_COL};letter-spacing:-0.02em">N/A</div>
                  <div style="font-size:12px;color:#64748b;margin-top:8px">{subtitle}</div>
                  <div style="font-size:11px;color:#475569;margin-top:8px">Financial health grades such as “B” are no longer shown as analyst consensus.</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
                  <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">LOW TARGET</div>
                    <div style="font-size:1.2rem;font-weight:600;color:{RED};font-family:monospace">{("$" + format(tl, ".0f")) if tl else "—"}</div>
                  </div>
                  <div style="background:#13161e;border:1px solid #252a38;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">CONSENSUS</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{GREEN};font-family:monospace">{("$" + format(tm, ".0f")) if tm else "—"}</div>
                  </div>
                  <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                    <div style="font-size:10px;color:#475569;margin-bottom:5px">HIGH TARGET</div>
                    <div style="font-size:1.2rem;font-weight:600;color:{GREEN};font-family:monospace">{("$" + format(th, ".0f")) if th else "—"}</div>
                  </div>
                </div>
                <div style="text-align:center;font-size:1.1rem;font-weight:700;
                            color:{up_c};font-family:monospace">
                  {("▲" if up>0 else "▼") if tm else ""} {f"{abs(up):.1f}% implied upside" if tm else "No price-target upside available"}</div>
                """, unsafe_allow_html=True)

        st.markdown(legend_html([("Stock",BLUE,"bar"),("Sector Avg",AMBER,"bar"),("S&P 500","#475569","bar")]),
                    unsafe_allow_html=True)
        pchart(multiples_chart([pe or 0,ps or 0,evE or 0,pb or 0],
                               [24,4,16,3.5],[21,2.7,14,4.2],
                               ["P/E","P/S","EV/EBITDA","P/B"]), "chart_multiples")

        shead("Interactive DCF Fair Value Calculator")
        fcf_raw=float(info.get("freeCashflow") or info.get("operatingCashflow") or 0)
        shares =float(info.get("sharesOutstanding") or 1)
        dc1,dc2,dc3,dc4,dc5 = st.columns(5)
        gr  =dc1.slider("Revenue Growth Rate %",0.0,35.0,min(float((info.get("revenueGrowth") or 0.05)*100),30.0),0.5)
        tg  =dc2.slider("Terminal Growth Rate %",0.5,5.0,3.0,0.1)
        wacc=dc3.slider("Discount Rate (WACC) %",5.0,16.0,10.0,0.5)
        yrs =dc4.slider("Projection Years",5,15,10,1)
        mos =dc5.slider("Margin of Safety %",0,40,20,5)
        if fcf_raw>0:
            if wacc <= tg:
                st.warning("DCF unavailable for this scenario: discount rate must be greater than terminal growth rate.")
            else:
                per_sh=dcf_value(fcf_raw,gr,tg,wacc,yrs)/shares
                safe=per_sh*(1-mos/100)
                ud=(per_sh/price-1)*100 if price else 0
                vc=GREEN if ud>10 else AMBER if ud>-10 else RED
                vt="Undervalued ✓" if ud>10 else "Fairly Valued ≈" if ud>-10 else "Overvalued ✗"
                d1,d2,d3,d4=st.columns(4)
                d1.metric("DCF Intrinsic Value",f"${per_sh:.2f}")
                d2.metric("Buy Below (w/ MoS)", f"${safe:.2f}")
                d3.metric("Current Price",       f"${price:.2f}")
                d4.metric("DCF Upside",          f"{ud:+.1f}%")
                st.markdown(f"""
                <div style="padding:12px 20px;background:#13161e;border-left:3px solid {vc};
                            border-radius:0 10px 10px 0;margin-top:6px">
                  <span style="color:{vc};font-weight:700">{vt}</span>
                  <span style="color:#475569;font-size:12px;margin-left:12px">
                    {gr:.0f}% growth · {wacc:.0f}% WACC · {mos:.0f}% margin of safety</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Free cash flow unavailable — DCF requires positive FCF.")

        shead("Quality & Profitability")
        q1,q2,q3,q4,q5,q6=st.columns(6)
        q1.metric("ROE",          with_avg(fpct(info.get("returnOnEquity")), "roe", info))
        q2.metric("ROA",          with_avg(fpct(info.get("returnOnAssets")), "roa", info))
        q3.metric("Gross Margin", with_avg(fpct(info.get("grossMargins")), "gross_margin", info))
        q4.metric("Net Margin",   with_avg(fpct(info.get("profitMargins")), "net_margin", info))
        q5.metric("Op Margin",    with_avg(fpct(info.get("operatingMargins")), "op_margin", info))
        q6.metric("Rev Growth",   with_avg(fpct(info.get("revenueGrowth")), "rev_growth", info))

        page_comment("Reading this page", ["<b>P/E, P/S, EV/EBITDA:</b> lower can be cheaper, but high-growth firms often trade above industry averages.", "<b>PEG:</b> around 1 is often reasonable; far above 2 can mean price is rich relative to growth.", "<b>DCF:</b> highly sensitive to growth, WACC, and terminal assumptions; use it as a scenario tool, not a precise target.", "<b>ROE / margins:</b> higher usually signals stronger quality, but check debt and business cyclicality."])

    # ══════════ TAB 3 — RISK ══════════════════════════════════════
    if active_tab == "risk":
        rcfg1, rcfg2 = st.columns([1, 4])
        risk_chart_period = rcfg1.selectbox("Risk chart range", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "20y"], index=1, key="risk_chart_period")
        rcfg2.caption("Risk charts use their own range. Default is 3 months.")
        risk_hist_local, risk_err = fetch_chart_history(ticker, risk_chart_period, "1d")
        if risk_err or risk_hist_local is None or risk_hist_local.empty:
            risk_hist_local = hist
        risk_ta_local = calc_ta(risk_hist_local)
        risk_spy_local = fetch_spy(risk_chart_period)
        risk_view = calc_risk(risk_hist_local, risk_spy_local)
        risk_metric = risk_view

        shead("Risk & Performance Metrics vs S&P 500")
        r1,r2,r3,r4,r5,r6,r7=st.columns(7)
        r1.metric("Beta",         with_avg(f"{risk_metric['beta']:.2f}", "beta", info))
        r2.metric("Annual Vol.",  with_avg(f"{risk_metric['vol']:.1f}%", "vol", info))
        r3.metric("Sharpe Ratio", with_avg(f"{risk_metric['sharpe']:.2f}", "sharpe", info))
        r4.metric("Sortino",      with_avg(f"{risk_metric['sortino']:.2f}", "sortino", info))
        r5.metric("Max Drawdown", with_avg(f"{risk_metric['max_dd']:.1f}%", "max_dd", info))
        r6.metric("Calmar Ratio", with_avg(f"{risk_metric['calmar']:.2f}", "calmar", info))
        r7.metric("Period Return", f"{risk_metric['ret1y']:.1f}%")
        r8,r9,r10,r11,r12,r13,r14=st.columns(7)
        r8.metric("Alpha vs SPY", f"{risk_metric['alpha']:.2f}%")
        r9.metric("VaR 95%",      with_avg(f"{risk_metric['var95']:.2f}%", "var95", info))
        r10.metric("CVaR 95%",    with_avg(f"{risk_metric['cvar95']:.2f}%", "cvar95", info))
        r11.metric("Win Rate",    with_avg(f"{risk_metric['win']:.1f}%", "win", info))
        r12.metric("R² vs SPY",   with_avg(f"{risk_metric['r2']:.3f}", "r2", info))
        r13.metric("Tracking Err",with_avg(f"{risk_metric['te']:.2f}%", "te", info))
        r14.metric("Info Ratio",  with_avg(f"{risk_metric['ir']:.2f}", "ir", info))

        ca,cb=st.columns(2)
        with ca:
            shead("Drawdown from Peak")
            st.markdown(legend_html([("Drawdown %", RED, "line")]), unsafe_allow_html=True)
            pchart(drawdown_chart(risk_view["dd_s"]), "chart_drawdown")
        with cb:
            shead("Daily Return Distribution")
            st.markdown(legend_html([("Daily Returns",BLUE,"bar"),("Mean",GREEN,"dash"),("VaR 95%",RED,"dash")]),
                        unsafe_allow_html=True)
            pchart(returns_hist(risk_view["ret_s"]), "chart_returns")

        cc,cd=st.columns(2)
        with cc:
            shead("Rolling 60-Day Sharpe Ratio")
            st.markdown(legend_html([("Sharpe",BLUE,"line"),("Sharpe=1",GREEN,"dash")]),
                        unsafe_allow_html=True)
            pchart(rolling_sharpe_chart(risk_view["roll_sh"]), "chart_sharpe")
        with cd:
            shead("Annualised Rolling Volatility")
            st.markdown(legend_html([("20-Day Vol",PURPLE,"line"),("60-Day Vol",TEAL,"dash")]),
                        unsafe_allow_html=True)
            pchart(vol_chart(risk_ta_local, 99999), "chart_vol_risk")

        shead("Financial Health")
        h1,h2,h3,h4,h5,h6,h7=st.columns(7)
        h1.metric("Debt/Equity",   with_avg(f"{info.get('debtToEquity',0)/100:.2f}" if info.get("debtToEquity") else "—", "debt_equity", info))
        h2.metric("Current Ratio", with_avg(f"{info.get('currentRatio',0):.2f}" if info.get("currentRatio") else "—", "current_ratio", info))
        h3.metric("Quick Ratio",   with_avg(f"{info.get('quickRatio',0):.2f}" if info.get("quickRatio") else "—", "quick_ratio", info))
        h4.metric("Free Cash Flow",fmtn(info.get("freeCashflow"),"$"))
        h5.metric("Total Debt",    fmtn(info.get("totalDebt"),"$"))
        h6.metric("Total Cash",    fmtn(info.get("totalCash"),"$"))
        ebitda=info.get("ebitda") or 0; intexp=abs(info.get("interestExpense") or 0)
        h7.metric("Int. Coverage", f"{ebitda/intexp:.1f}x" if ebitda and intexp else "—")

        page_comment("Reading this page", ["<b>Sharpe ratio:</b> above 1 is generally good; above 2 is strong; below 0 means risk-adjusted return is poor over the selected period.", "<b>Beta:</b> above 1 moves more than SPY on average; below 1 is usually more defensive.", "<b>Max drawdown:</b> shows worst peak-to-trough loss; smaller drawdown is better for capital preservation.", "<b>VaR / CVaR:</b> estimate downside tail risk; CVaR is the average loss in the worst tail, so it is usually more conservative."])

    # ══════════ TAB 4 — INDUSTRY ══════════════════════════════════
    if active_tab == "industry":
        shead("Market Position")
        s1,s2,s3,s4=st.columns(4)
        mcap=info.get("marketCap",0) or 0
        cap_cat=("Mega Cap >$200B" if mcap>200e9 else "Large Cap >$10B"
                 if mcap>10e9 else "Mid Cap >$2B" if mcap>2e9 else "Small Cap")
        s1.metric("Sector",   info.get("sector","—"))
        s2.metric("Industry", info.get("industry","—"))
        s3.metric("Size",     cap_cat)
        s4.metric("Exchange", info.get("exchange","—"))

        shead("Peer Comparison")
        sec=info.get("sector","")
        peer_defaults={
            "Technology":"MSFT,GOOGL,META,AMZN,NVDA,ORCL",
            "Consumer Cyclical":"AMZN,BABA,TGT,WMT,COST,HD",
            "Financial Services":"JPM,BAC,GS,MS,WFC,C",
            "Healthcare":"JNJ,PFE,UNH,ABBV,MRK,LLY",
            "Energy":"XOM,CVX,COP,SLB,EOG,PXD",
            "Communication Services":"GOOGL,META,NFLX,DIS,CMCSA,T",
            "Industrials":"CAT,BA,GE,HON,UPS,MMM",
            "Consumer Defensive":"PG,KO,PEP,WMT,COST,CL",
        }.get(sec,"MSFT,GOOGL,AMZN,META,NVDA")
        peer_raw=st.text_input("Peer Tickers (comma-separated)", value=peer_defaults)
        peer_list=tuple(p.strip().upper() for p in peer_raw.split(",")
                        if p.strip() and p.strip().upper()!=ticker)[:7]
        peers=fetch_peers(peer_list,"1y")

        y1_self=(hist["Close"].iloc[-1]/hist["Close"].iloc[0]-1)*100 if len(hist)>1 else 0
        table_rows=[{"Ticker":f"★ {ticker}","Company":name[:28],"Price":f"${price:.2f}",
                     "P/E":f"{info.get('trailingPE',0):.1f}" if info.get("trailingPE") else "—",
                     "Fwd P/E":f"{info.get('forwardPE',0):.1f}" if info.get("forwardPE") else "—",
                     "Mkt Cap":fmtn(info.get("marketCap"),"$"),"1yr %":f"{y1_self:+.1f}%",
                     "Net Margin":fpct(info.get("profitMargins")),
                     "Rev Growth":fpct(info.get("revenueGrowth")),
                     "Div Yield":fpct(info.get("dividendYield")) if info.get("dividendYield") else "—",
                     "Beta":f"{risk.get('beta', 0):.2f}"}]
        for sym,pd_ in peers.items():
            pi,ph=pd_["info"],pd_["hist"]
            if ph.empty: continue
            p1y=(ph["Close"].iloc[-1]/ph["Close"].iloc[0]-1)*100 if len(ph)>1 else 0
            beta=pi.get("beta")
            table_rows.append({"Ticker":sym,"Company":pi.get("shortName",sym)[:28],
                "Price":f"${float(pi.get('currentPrice') or ph['Close'].iloc[-1]):.2f}",
                "P/E":f"{pi.get('trailingPE',0):.1f}" if pi.get("trailingPE") else "—",
                "Fwd P/E":f"{pi.get('forwardPE',0):.1f}" if pi.get("forwardPE") else "—",
                "Mkt Cap":fmtn(pi.get("marketCap"),"$"),"1yr %":f"{p1y:+.1f}%",
                "Net Margin":fpct(pi.get("profitMargins")),
                "Rev Growth":fpct(pi.get("revenueGrowth")),
                "Div Yield":fpct(pi.get("dividendYield")) if pi.get("dividendYield") else "—",
                "Beta":f"{float(beta):.2f}" if beta else "—"})
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        shead("Normalized Price Performance vs Peers (1 Year · Base = 100)")
        all_tickers=[ticker]+list(peers.keys())
        palette=[BLUE,GREEN,RED,AMBER,PURPLE,TEAL,"#fb923c","#f472b6"]
        st.markdown(legend_html([(t,palette[i%len(palette)],"line") for i,t in enumerate(all_tickers)]),
                    unsafe_allow_html=True)
        pchart(perf_chart(hist,ticker,peers), "chart_perf")

        page_comment("Reading this page", ["<b>Peer comparison:</b> compare companies in the same sector first; cross-sector valuation comparisons can be misleading.", "<b>Normalized performance:</b> base = 100 lets you compare relative returns independent of starting price.", "<b>Market cap:</b> larger firms are often more liquid and stable; smaller firms may move faster but carry more risk."])

    # ══════════ TAB 5 — TECHNICAL ═════════════════════════════════
    if active_tab == "technical":
        tcfg1, tcfg2 = st.columns([1, 4])
        tech_chart_period = tcfg1.selectbox("Technical chart range", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "20y"], index=1, key="tech_chart_period")
        tcfg2.caption("Technical indicators and charts use their own range. Default is 3 months.")
        tech_hist_local, tech_err = fetch_chart_history(ticker, tech_chart_period, "1d")
        if tech_err or tech_hist_local is None or tech_hist_local.empty:
            tech_hist_local = hist
        tech_ta = calc_ta(tech_hist_local)
        tech_days = 99999

        last = tech_ta.iloc[-1]
        tech_price = _finite(last.get("Close"))
        if not np.isfinite(tech_price):
            tech_price = price
        rsi_v = _finite(last.get("RSI"));   rsi_v = rsi_v if np.isfinite(rsi_v) else 50.0
        adx_v = _finite(last.get("ADX"));   adx_v = adx_v if np.isfinite(adx_v) else 0.0
        atr_v = _finite(last.get("ATR"));   atr_v = atr_v if np.isfinite(atr_v) else 0.0
        rvol  = _finite(last.get("RVOL20")); rvol = rvol if np.isfinite(rvol) else 0.0

        tech_signal = technical_signal_model(tech_ta, fallback_price=tech_price)
        score = tech_signal["score"]
        vt = tech_signal["label"]
        vc = tech_signal["color"]
        sigs = [(c["emoji"], f"{c['name']} ({c['weight']:.0f}% weight): {c['detail']}") for c in tech_signal.get("components", [])]

        shead("Technical Summary")
        ts1,ts2,ts3,ts4,ts5=st.columns(5)
        ts1.markdown(f"""
        <div style="background:#13161e;border:1px solid {vc}44;border-radius:10px;
                    padding:14px;text-align:center">
          <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.08em">
            Overall Signal</div>
          <div style="font-size:1rem;font-weight:700;color:{vc};margin:6px 0">{vt}</div>
          <div style="font-size:11px;color:#475569">Score {score:.0f}/100</div>
        </div>""", unsafe_allow_html=True)
        ts2.metric("RSI (14-day)",  with_avg(f"{rsi_v:.1f}", "rsi", info))
        ts3.metric("ADX (14-day)",  with_avg(f"{adx_v:.1f}", "adx", info))
        ts4.metric("ATR (14-day)",  f"${atr_v:.2f}")
        ts5.metric("Volatility 20d",with_avg(f"{rvol:.1f}%", "rvol20", info))

        shead("Moving Average Values vs Current Price")
        ma_cols=st.columns(6)
        for i,lbl in enumerate(["MA5","MA10","MA20","MA50","MA120","MA200"]):
            raw=last.get(lbl)
            if raw is not None and not pd.isna(raw):
                mav=float(raw); dp2=(tech_price/mav-1)*100; clr=GREEN if dp2>0 else RED
                ma_cols[i].markdown(f"""
                <div style="background:#13161e;border:1px solid #1e2433;border-radius:9px;
                            padding:12px;text-align:center">
                  <div style="font-size:10px;color:{MA_COLORS[lbl]};margin-bottom:4px;font-weight:600">
                    {ma_labels[lbl]}</div>
                  <div style="font-size:14px;font-weight:600;font-family:monospace;color:#e2e8f0">
                    ${mav:.2f}</div>
                  <div style="font-size:11px;color:{clr};margin-top:2px">{dp2:+.1f}% from price</div>
                </div>""", unsafe_allow_html=True)
            else:
                ma_cols[i].metric(ma_labels[lbl],"Insufficient data")

        shead("Key Support & Resistance Levels")
        supports,resistances=find_sr(tech_ta)
        src=st.columns(6)
        for i,sv in enumerate(supports[:3]):
            diff=(tech_price/sv-1)*100
            src[i].markdown(f"""
            <div style="background:#13161e;border:1px solid rgba(239,68,68,0.25);
                        border-radius:9px;padding:12px;text-align:center">
              <div style="font-size:10px;color:{RED};margin-bottom:4px">SUPPORT {i+1}</div>
              <div style="font-size:14px;font-weight:600;font-family:monospace;color:#e2e8f0">
                ${sv:.2f}</div>
              <div style="font-size:11px;color:{RED};margin-top:2px">{diff:+.1f}% from price</div>
            </div>""", unsafe_allow_html=True)
        for i,rv in enumerate(resistances[:3]):
            diff=(tech_price/rv-1)*100
            src[i+3].markdown(f"""
            <div style="background:#13161e;border:1px solid rgba(16,185,129,0.25);
                        border-radius:9px;padding:12px;text-align:center">
              <div style="font-size:10px;color:{GREEN};margin-bottom:4px">RESISTANCE {i+1}</div>
              <div style="font-size:14px;font-weight:600;font-family:monospace;color:#e2e8f0">
                ${rv:.2f}</div>
              <div style="font-size:11px;color:{GREEN};margin-top:2px">{diff:+.1f}% from price</div>
            </div>""", unsafe_allow_html=True)

        shead("Indicator Charts")
        ca,cb=st.columns(2)
        with ca:
            st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:4px'>"
                        "RSI (14) — Relative Strength Index</div>", unsafe_allow_html=True)
            st.markdown(legend_html([("RSI 14-day",BLUE,"line"),
                                     ("RSI 9-day MA",AMBER,"dash"),
                                     ("Overbought 70",RED,"dash"),
                                     ("Oversold 30",GREEN,"dash")]), unsafe_allow_html=True)
            pchart(rsi_chart(tech_ta,tech_days), "chart_rsi")

        with cb:
            st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:4px'>"
                        "MACD (12, 26, 9) — Moving Average Convergence Divergence</div>",
                        unsafe_allow_html=True)
            st.markdown(legend_html([("MACD Line",BLUE,"line"),
                                     ("Signal Line",RED,"line"),
                                     ("Histogram (positive)",GREEN,"bar"),
                                     ("Histogram (negative)",RED,"bar")]), unsafe_allow_html=True)
            pchart(macd_chart(tech_ta,tech_days), "chart_macd")

        cc,cd=st.columns(2)
        with cc:
            st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:4px'>"
                        "Stochastic Oscillator (14, 3) — Momentum</div>", unsafe_allow_html=True)
            st.markdown(legend_html([("%K Line",BLUE,"line"),("%D Signal",RED,"dash"),
                                     ("Overbought 80",RED,"dash"),("Oversold 20",GREEN,"dash")]),
                        unsafe_allow_html=True)
            pchart(stoch_chart(tech_ta,tech_days), "chart_stoch")

        with cd:
            st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:4px'>"
                        "Annualised Rolling Volatility — Realised Risk</div>", unsafe_allow_html=True)
            st.markdown(legend_html([("20-Day Volatility",PURPLE,"line"),
                                     ("60-Day Volatility",TEAL,"dash")]), unsafe_allow_html=True)
            pchart(vol_chart(tech_ta,tech_days), "chart_vol_tech")

        shead("Signal Checklist")
        sc1,sc2=st.columns(2)
        for i,(emoji,text) in enumerate(sigs):
            target=sc1 if i%2==0 else sc2
            target.markdown(f'<div class="signal-row">{emoji} {text}</div>', unsafe_allow_html=True)

        page_comment("Reading this page", ["<b>Overall signal:</b> weighted model, not a simple green-icon count. Trend structure and MACD carry the most weight; RSI/stochastic help detect overextension.", "<b>RSI:</b> above 70 is often overbought; below 30 is oversold, but oversold is not automatically bullish until reversal/trend confirmation appears.", "<b>MACD:</b> MACD above signal is bullish momentum; histogram improvement confirms acceleration.", "<b>ADX:</b> above 25 confirms trend strength; the model combines ADX with MA direction because ADX alone has no bullish/bearish direction.", "<b>ATR / volatility:</b> higher means wider expected price swings and usually requires smaller position size."])

    # ══════════ TAB 6 — COMPARISON ═══════════════════════════════
    if active_tab == "comparison":
        shead("Two-Stock Direct Comparison")
        cta, ctb, ctc = st.columns([2,2,1])
        comp1 = cta.text_input("First ticker", value=ticker, key="comp_ticker_1").upper().strip()
        comp2 = ctb.text_input("Second ticker", value="MSFT" if ticker != "MSFT" else "AAPL", key="comp_ticker_2").upper().strip()
        comp_period = ctc.selectbox("Compare period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1, key="comp_period")

        if comp1 and comp2:
            _comp_key = (comp1, comp2, comp_period)
            _comp_fresh = st.session_state.get("_last_comp_key") != _comp_key
            if _comp_fresh:
                with st.spinner(f"Loading {comp1} and {comp2}…"):
                    d1, e1 = fetch_stock(comp1, comp_period)
                    d2, e2 = fetch_stock(comp2, comp_period)
                if not e1 and not e2:
                    st.session_state["_last_comp_key"] = _comp_key
            else:
                d1, e1 = fetch_stock(comp1, comp_period)
                d2, e2 = fetch_stock(comp2, comp_period)
            if e1 or e2 or not d1 or not d2:
                st.error(f"Comparison error: {comp1}: {e1 or 'OK'}; {comp2}: {e2 or 'OK'}")
            else:
                h1, h2 = d1["hist"], d2["hist"]
                i1, i2 = d1["info"], d2["info"]
                ta1, ta2 = calc_ta(h1), calc_ta(h2)
                spy_c = fetch_spy(comp_period)
                rsk1, rsk2 = calc_risk(h1, spy_c), calc_risk(h2, spy_c)

                shead("Normalized Stock Price Chart")
                st.markdown(legend_html([(comp1, BLUE, "line"), (comp2, AMBER, "line")]), unsafe_allow_html=True)
                pchart(compare_price_chart(h1, comp1, h2, comp2), "chart_compare_price")

                shead("Volatility Comparison")
                st.markdown(legend_html([(f"{comp1} 20d Vol", BLUE, "line"), (f"{comp2} 20d Vol", AMBER, "line")]), unsafe_allow_html=True)
                pchart(compare_vol_chart(ta1, comp1, ta2, comp2), "chart_compare_vol")

                shead("Company, Stock, and Risk Ratio Table")
                st.dataframe(comparison_table(comp1, i1, rsk1, ta1, comp2, i2, rsk2, ta2), use_container_width=True)

                shead("Built-in AI-Style Comparison Summary")
                st.markdown(f'<div style="font-size:14px;color:#94a3b8;line-height:1.8">{comparison_paragraph(comp1, i1, rsk1, ta1, comp2, i2, rsk2, ta2)}</div>', unsafe_allow_html=True)

        page_comment("Reading this page", ["<b>Direct comparison:</b> a better candidate usually has stronger trend, lower valuation risk, better profitability, and acceptable volatility.", "<b>Volatility:</b> the more volatile ticker may offer better trading opportunity but needs stricter risk control.", "<b>Ratios:</b> compare against the firm’s industry average, not only against the second ticker."])

    # ══════════ TAB 7 — NEWS ═══════════════════════════════════════
    if active_tab == "news":
        shead("Latest Company News")
        ncol1, ncol2, ncol3 = st.columns([2, 2, 1])
        news_keyword = ncol1.text_input(tr("Search news by keyword"), value="", placeholder="earnings, AI, guidance, lawsuit...", key="news_keyword")
        news_order = ncol2.selectbox(tr("Order news by"), [tr("Importance first"), tr("Newest first")], index=0, key="news_order")
        if "news_refresh_token" not in st.session_state:
            st.session_state.news_refresh_token = 0
        if ncol3.button("⟳ " + tr("Update News"), use_container_width=True):
            st.session_state.news_refresh_token = int(time.time())
            fetch_news_items.clear()

        st.caption(tr("Priority: FMP first, then WSJ/RSS and broad financial news. Duplicate/overlapping headlines are filtered."))
        with st.spinner(f"Updating latest news for {ticker}..."):
            news_items = fetch_news_items(ticker, news_keyword, st.session_state.news_refresh_token)
        if news_order == tr("Newest first") or news_order == "Newest first":
            news_items = sorted(news_items, key=lambda x: x.get("ts", 0), reverse=True)
        else:
            news_items = sorted(news_items, key=lambda x: (x.get("importance", 0), x.get("ts", 0)), reverse=True)

        if not news_items:
            st.info(tr("No matching recent news found. Try a broader keyword or click Update News."))
        else:
            pos = sum(1 for x in news_items if x.get("sentiment") == "Positive")
            neg = sum(1 for x in news_items if x.get("sentiment") == "Negative")
            avg_inf = sum(x.get("influence", 0) for x in news_items[:10]) / max(1, min(10, len(news_items)))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Important Headlines", len(news_items))
            c2.metric("Positive", pos)
            c3.metric("Negative", neg)
            c4.metric("Avg Influence", f"{avg_inf:+.0f}/100")
            for n in news_items:
                render_news_item(n)

        page_comment("Reading this page", ["<b>News sentiment:</b> positive/negative/neutral is a quick classification; price reaction still depends on valuation and expectations.", "<b>Influence score:</b> higher means the headline is more likely to matter for near-term trading.", "<b>Duplicate filter:</b> similar headlines are compressed so the page focuses on important catalysts."])


    # ══════════ TAB 8 — BROAD MARKET NEWS ════════════════════════
    if active_tab == "market_news":
        shead("Latest Market News")
        st.caption(tr("Market news by importance/time with AI-style impact analysis. Sources prioritize FMP and WSJ first, then reliable broad RSS discovery."))
        if "market_news_refresh_token" not in st.session_state:
            st.session_state.market_news_refresh_token = 0

        m1, m2, m3, m4, m5, m6 = st.columns([1.35, .95, 1.05, 1.05, 1.05, .75])
        market_keyword = m1.text_input(tr("Search market news by keyword"), value="", placeholder="Hormuz, Fed, AI, tariffs, earnings...", key="market_news_keyword")
        market_ticker = m2.text_input(tr("Search market news by ticker"), value="", placeholder="AAPL, NOW, NVDA...", key="market_news_ticker").upper().strip()
        market_order = m3.selectbox(tr("Order by"), ["Importance first", "Newest first"], index=0, key="market_news_order", format_func=tr)
        market_country = m4.selectbox(tr("Country Filter"), MARKET_NEWS_COUNTRIES, index=0, key="market_news_country", format_func=tr)
        market_category = m5.selectbox(tr("Category Filter"), MARKET_NEWS_CATEGORIES, index=0, key="market_news_category", format_func=tr)
        if m6.button("⟳ " + tr("Update"), key="market_news_update", use_container_width=True):
            st.session_state.market_news_refresh_token = int(time.time())
            fetch_market_news.clear()

        f1, f2 = st.columns([1.2, 2.8])
        market_industry = f1.selectbox(tr("Industry Impact Filter"), MARKET_NEWS_INDUSTRIES, index=0, key="market_news_industry", format_func=tr)
        max_items = f2.slider(tr("Number of headlines"), min_value=8, max_value=40, value=20, step=4, key="market_news_limit")

        with st.spinner("Updating global and U.S. market news, scoring importance, and mapping industry impact..."):
            market_items = fetch_market_news(market_keyword, market_ticker, st.session_state.market_news_refresh_token)

        if market_country != "All Countries":
            market_items = [x for x in market_items if x.get("country") == market_country]
        if market_category != "All Categories":
            market_items = [x for x in market_items if x.get("category") == market_category]
        if market_industry != "All Industries":
            key = market_industry.lower().split(" /")[0]
            market_items = [x for x in market_items if key in " ".join(x.get("industry_tags", []) + x.get("impact", {}).get("good_for", []) + x.get("impact", {}).get("bad_for", []) + x.get("impact", {}).get("companies", [])).lower()]

        if market_order == "Newest first":
            market_items = sorted(market_items, key=lambda x: x.get("ts", 0), reverse=True)
        else:
            market_items = sorted(market_items, key=lambda x: (x.get("importance", 0), x.get("ts", 0)), reverse=True)
        market_items = market_items[:max_items]

        if not market_items:
            st.info(tr("No broad market news matched these filters. Try a broader keyword, ticker, country, category, or industry filter."))
        else:
            avg_score = sum(x.get("importance", 0) for x in market_items) / max(1, len(market_items))
            policy_count = sum(1 for x in market_items if x.get("category") in {"Policy / Regulation", "Central Bank / Rates", "Geopolitics / Conflict"})
            global_count = sum(1 for x in market_items if x.get("country") != "United States")
            top_theme = market_items[0].get("category", "General Market News")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Headlines", len(market_items))
            c2.metric("Avg Importance", f"{avg_score:.0f}/100")
            c3.metric("Global Items", global_count)
            c4.metric("Top Theme", top_theme)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            for item in market_items:
                render_market_news_item(item)

        page_comment("Reading this page", ["<b>Importance score:</b> ranks event materiality using source priority, category, macro shock keywords, and identified industry/company impact.", "<b>AI-style summary:</b> concise headline and body are generated locally with rules, so no external AI key is required.", "<b>Impact list:</b> good/bad industry mapping is a trading screen, not a guarantee; confirm with price action, volume, and official filings."])


    # ══════════ TAB 8B — INVESTOR VIEW ═══════════════════════════
    if active_tab == "investor_view":
        render_investor_view()

    # ══════════ TAB 9 — MARKET RANKINGS ═══════════════════════════
    if active_tab == "market_rankings":
        shead("Market Movers & Volatility Ranking")
        c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
        industry_choice = c1.selectbox(tr("Industry Filter"), list(RANKING_UNIVERSES.keys()), index=0, key="rank_industry")
        top_n = c2.selectbox(tr("Ranking Size"), [5, 10, 20, 30], index=1, key="rank_n")
        metric_options = [
            "Trader Composite Score", "Change %", "Change $", "5D Momentum %",
            "Opening Gap %", "20D Vol %", "Volume Ratio", "Dollar Volume $M",
            "Liquidity Score", "Market Cap $B"
        ]
        metric = c3.selectbox(tr("Ranking Metric"), metric_options, index=0, key="rank_metric")
        if c4.button(tr("Update Rankings"), key="update_rankings", use_container_width=True):
            st.cache_data.clear()
        with st.spinner("Updating rankings... Fetching latest prices, volatility, volume, and company info."):
            rank_df = ranking_snapshot(tuple(RANKING_UNIVERSES[industry_choice]), period="3mo")
        if rank_df.empty:
            st.warning("No ranking data returned. Try again or choose another industry.")
        else:
            f1, f2, f3, f4 = st.columns([1.4, 1.4, 1.4, 1])
            country_choices = ["All"] + sorted([x for x in rank_df["Country"].dropna().unique().tolist() if x])
            country_choice = f1.selectbox("Country Filter", country_choices, index=0, key="rank_country")
            cap_bucket = f2.selectbox("Market Cap Filter", ["All", "Mega Cap ($200B+)", "Large Cap ($10B-$200B)", "Mid Cap ($2B-$10B)", "Small/Other (<$2B or N/A)"], index=0, key="rank_cap")
            direction = f3.selectbox("Direction", ["High to Low", "Low to High"], index=0, key="rank_direction", help="High to Low shows largest values first. Low to High shows smallest values first.")
            min_liq = f4.selectbox("Min Liquidity", [0, 25, 50, 75], index=0, key="rank_min_liq")

            filtered = rank_df.copy()
            if country_choice != "All":
                filtered = filtered[filtered["Country"] == country_choice]
            if cap_bucket != "All":
                mc = pd.to_numeric(filtered["Market Cap"], errors="coerce").fillna(0)
                if cap_bucket.startswith("Mega"):
                    filtered = filtered[mc >= 200e9]
                elif cap_bucket.startswith("Large"):
                    filtered = filtered[(mc >= 10e9) & (mc < 200e9)]
                elif cap_bucket.startswith("Mid"):
                    filtered = filtered[(mc >= 2e9) & (mc < 10e9)]
                else:
                    filtered = filtered[(mc < 2e9)]
            filtered = filtered[pd.to_numeric(filtered["Liquidity Score"], errors="coerce").fillna(0) >= float(min_liq)]

            if filtered.empty:
                st.warning("No stocks match these filters. Loosen country, market cap, or liquidity filters.")
            else:
                ascending = direction == "Low to High"
                top_df = filtered.sort_values(metric, ascending=ascending).head(int(top_n)).reset_index(drop=True)
                direction_label = "Lowest" if ascending else "Highest"
                shead(f"{direction_label} {metric} Ranking Table")
                display_cols = ["Ticker", "Company", "Country", "Sector", "Market Cap $B", "Last Price", "Change %", "5D Momentum %", "Opening Gap %", "20D Vol %", "Volume Ratio", "Dollar Volume $M", "Liquidity Score", "Trader Composite Score", "Investment Note"]
                table_df = top_df[[c for c in display_cols if c in top_df.columns]].copy()
                table_df["FMP Link"] = table_df["Ticker"].apply(lambda x: f"https://financialmodelingprep.com/financial-summary/{x}")
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"FMP Link": st.column_config.LinkColumn("FMP", display_text="Open")},
                )
                st.markdown("<div style='font-size:11px;color:#64748b;margin:8px 0'>Click a U.S.-listed ticker bar to open that company in the main Overview.</div>", unsafe_allow_html=True)
                ca, cb = st.columns(2)
                with ca:
                    shead(f"{direction_label} {metric} Chart")
                    clickable_rank_chart(ranking_bar_chart(top_df, metric, ascending=ascending), "rank_primary_chart")
                with cb:
                    shead("Top Volatility Chart")
                    vol_df = filtered.sort_values("20D Vol %", ascending=False).head(int(top_n)).reset_index(drop=True)
                    clickable_rank_chart(ranking_bar_chart(vol_df, "20D Vol %", ascending=False), "rank_vol_chart")
                leader = top_df.iloc[0]
                st.markdown(f"""
                <div class="news-card"><div class="news-title">{tr('Investment Note')}</div>
                <div class="news-summary"><b>{leader['Ticker']}</b> is the <b>{direction_label.lower()}</b> result in this filtered ranking by <b>{metric}</b>. The composite score combines price move, volatility, volume confirmation, five-day momentum, and liquidity. For trades, prioritize names with high volume confirmation and clear catalysts; for investing, confirm valuation, earnings quality, balance-sheet strength, and sector trend before acting.</div></div>""", unsafe_allow_html=True)


                shead("AI Thesis Score by Industry / Country")
                ai_c1, ai_c2, ai_c3, ai_c4, ai_c5 = st.columns([1.15, 0.9, 0.95, 1.25, 0.85])
                ai_universe_choice = ai_c1.selectbox("AI score universe", list(RANKING_UNIVERSES.keys()), index=list(RANKING_UNIVERSES.keys()).index(industry_choice) if industry_choice in RANKING_UNIVERSES else 0, key="ai_rank_universe")
                ai_top_n = ai_c2.selectbox("Top per industry", [5, 10, 20], index=1, key="ai_rank_top_n")
                ai_direction = ai_c3.selectbox("Score direction", ["High to Low", "Low to High"], index=0, key="ai_score_direction")
                with ai_c4:
                    ai_model = render_ai_model_selector("Risk preference model", key="ai_model_market_rank")
                if ai_c5.button("Update AI Scores", key="update_ai_rankings", use_container_width=True):
                    st.cache_data.clear()
                st.caption(ai_model_description(ai_model))
                with st.spinner(f"Scoring companies with {AI_RISK_MODEL_NAMES.get(ai_model, ai_model)} model... This checks growth, momentum, quality, valuation, and risk for each ticker."):
                    ai_df = ai_score_universe(tuple(RANKING_UNIVERSES[ai_universe_choice]), period="1y", model=ai_model)
                if ai_df.empty:
                    st.info("No AI score data is available for this universe right now.")
                else:
                    f1, f2 = st.columns([1, 1])
                    ai_countries = ["All"] + sorted([x for x in ai_df["Country"].dropna().unique().tolist() if x])
                    ai_country_filter = f1.selectbox("Show country", ai_countries, index=0, key="ai_country_filter")
                    ai_industries = ["All"] + sorted([x for x in ai_df["Industry"].dropna().unique().tolist() if x])
                    ai_industry_filter = f2.selectbox("Show industry group", ai_industries, index=0, key="ai_industry_filter")
                    ai_view = ai_df.copy()
                    if ai_country_filter != "All":
                        ai_view = ai_view[ai_view["Country"] == ai_country_filter]
                    if ai_industry_filter != "All":
                        ai_view = ai_view[ai_view["Industry"] == ai_industry_filter]
                    ai_ascending = ai_direction == "Low to High"
                    # First select top/bottom N within each country-industry bucket.
                    # Then display the final table in true global score order, so High to Low
                    # never places a lower AI Score above a higher AI Score.
                    ai_view = (
                        ai_view
                        .sort_values("AI Score", ascending=ai_ascending)
                        .groupby(["Country", "Industry"], group_keys=False, sort=False)
                        .head(int(ai_top_n))
                        .sort_values("AI Score", ascending=ai_ascending)
                        .reset_index(drop=True)
                    )
                    ai_cols = ["Country", "Industry", "Ticker", "Company", "Market Cap $B", "Last Price", "AI Score", "Recommendation", "Model", "Growth", "Momentum", "Quality", "Valuation", "Risk Score", "3M Return %", "Sharpe", "Max Drawdown %", "Annual Vol %", "Why It Scores This Way"]
                    st.caption("Sorted globally by AI Score. Country and industry columns show each company’s group; Top per industry still limits how many names can come from each country-industry bucket.")
                    st.dataframe(ai_view[[c for c in ai_cols if c in ai_view.columns]], use_container_width=True, hide_index=True)
                    if not ai_view.empty:
                        top_ai = ai_view.sort_values("AI Score", ascending=ai_ascending).iloc[0]
                        headline = "Lowest AI thesis score" if ai_ascending else "Highest AI thesis score"
                        st.markdown(f"""
                        <div class="news-card"><div class="news-title">{headline}: {top_ai['Ticker']} · {top_ai['AI Score']}/100 · {top_ai['Country']}</div>
                        <div class="news-summary">This list keeps country and industry labels, limits results per country-industry bucket, and is globally sorted {ai_direction.lower()} by your risk-lover AI thesis score. Growth and momentum receive the highest weight, quality and valuation act as secondary filters, and safety/risk is a smaller but still active penalty.</div></div>""", unsafe_allow_html=True)

                page_comment("Reading this page", ["<b>% change:</b> best for ranking short-term market movers across tickers.", "<b>20D volatility:</b> high volatility means larger daily swings; combine it with volume ratio before trading.", "<b>Dollar volume:</b> higher liquidity usually means tighter spreads and easier execution.", "<b>Composite score:</b> blends move size, momentum, volume, volatility, and liquidity for trader-focused screening.", "<b>AI thesis score:</b> ranks companies by your preferred style: growth and momentum first, then quality/valuation, then risk control."])

    # ══════════ TAB 11 — GLOBAL INDEXES ═════════════════════════════
    if active_tab == "global_indexes":
        shead("Global Index Performance")
        ic1, ic2 = st.columns([1, 1])
        index_period = ic1.selectbox("Index period", ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y"], index=2, key="index_period")
        if ic2.button("Update Indexes", key="update_indexes", use_container_width=True):
            st.cache_data.clear()
        with st.spinner("Updating global indexes... Fetching latest market performance."):
            idx_df, curves = index_snapshot(period=index_period)
        if idx_df.empty:
            st.warning("No global index data returned.")
        else:
            shead("Major Index Curves")
            index_options = list(curves.keys())
            default_indexes = [name for name in index_options if "S&P 500" in name]
            if not default_indexes:
                default_indexes = index_options[:1]
            selected_indexes = st.multiselect(
                "Display indexes on chart",
                index_options,
                default=default_indexes,
                key="selected_global_index_curves",
            )
            selected_index_curves = {k: curves[k] for k in selected_indexes if k in curves}
            if selected_index_curves:
                pchart(index_curves_chart(selected_index_curves), "global_index_curves")
            else:
                st.info("Select at least one index to display on the chart.")

            shead("Global Indexes by Continent")
            st.caption("Default order: United States first, then China/Hong Kong, followed by other major global markets grouped by continent.")
            for continent in idx_df["Continent"].drop_duplicates().tolist():
                group = idx_df[idx_df["Continent"] == continent].copy()
                st.markdown(f"<div class='section-head'>{continent}</div>", unsafe_allow_html=True)
                st.dataframe(group[["Country", "Index", "Ticker", "Last Price", "Change $", "Change %", "20D Vol %"]], use_container_width=True, hide_index=True)

            shead("Index Ranking by % Change")
            idx_rank = idx_df.sort_values("Change %", ascending=False).reset_index(drop=True)
            st.dataframe(idx_rank[["Continent", "Country", "Index", "Ticker", "Last Price", "Change %", "20D Vol %"]], use_container_width=True, hide_index=True)
            pchart(ranking_bar_chart(idx_rank, "Change %"), "global_index_rank_chart")

            page_comment("Reading this page", ["<b>Global indexes:</b> U.S. and China are shown first by default because they often drive global risk sentiment.", "<b>Percentage ranking:</b> helps identify which region is leading or lagging over the selected period.", "<b>Index volatility:</b> rising volatility can signal stress even if the index is not down much yet."])

    # ══════════ TAB 10 — COMMODITIES ═══════════════════════════════
    if active_tab == "commodities":
        shead("Commodity Dashboard")
        cm1, cm2 = st.columns([1, 1])
        commodity_period = cm1.selectbox("Commodity period", ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y"], index=2, key="commodity_period")
        if cm2.button("Update Commodities", key="update_commodities", use_container_width=True):
            st.cache_data.clear()
        with st.spinner("Updating commodities... Fetching latest futures prices and indicators."):
            comm_df, comm_curves = commodity_snapshot(period=commodity_period)
        if comm_df.empty:
            st.warning("No commodity data returned.")
        else:
            shead("Commodity Curves")
            commodity_options = list(comm_curves.keys())
            default_commodities = [name for name in commodity_options if "WTI Crude Oil" in name]
            if not default_commodities:
                default_commodities = commodity_options[:1]
            selected_commodities = st.multiselect(
                "Display commodities on chart",
                commodity_options,
                default=default_commodities,
                key="selected_commodity_curves",
            )
            selected_comm_curves = {k: comm_curves[k] for k in selected_commodities if k in comm_curves}
            if selected_comm_curves:
                pchart(index_curves_chart(selected_comm_curves), "commodity_curves")
            else:
                st.info("Select at least one commodity to display on the chart.")
            shead("Commodity Indicators")
            for group in comm_df["Group"].drop_duplicates().tolist():
                gdf = comm_df[comm_df["Group"] == group].copy()
                st.markdown(f"<div class='section-head'>{group}</div>", unsafe_allow_html=True)
                st.dataframe(gdf[["Commodity", "Ticker", "Unit", "Last Price", "Change $", "Change %", "20D Vol %", "RSI 14", "MA20", "MA50", "Trend", "Volume Ratio"]], use_container_width=True, hide_index=True)
            ca, cb = st.columns(2)
            with ca:
                shead("Commodity % Change Ranking")
                pchart(ranking_bar_chart(comm_df.rename(columns={"Commodity": "Company"}), "Change %"), "commodity_change_chart")
            with cb:
                shead("Commodity Volatility Ranking")
                pchart(ranking_bar_chart(comm_df.rename(columns={"Commodity": "Company"}), "20D Vol %"), "commodity_vol_chart")

            strongest = comm_df.sort_values("Change %", ascending=False).iloc[0]
            weakest = comm_df.sort_values("Change %", ascending=True).iloc[0]
            st.markdown(f"""
            <div class="news-card"><div class="news-title">Commodity Market Read</div>
            <div class="news-summary"><b>{strongest['Commodity']}</b> has the strongest recent percentage move, while <b>{weakest['Commodity']}</b> is weakest over the selected period. For trading, compare price momentum with 20D volatility, RSI, and whether price is above or below MA20/MA50. Oil usually reflects growth, supply, and geopolitics; gold/silver often reflect rates, dollar strength, inflation expectations, and risk demand.</div></div>""", unsafe_allow_html=True)

            page_comment("Reading this page", ["<b>Oil and gas:</b> usually react to demand, supply cuts, inventories, and geopolitics.", "<b>Gold and silver:</b> often react to rates, inflation expectations, dollar strength, and risk demand.", "<b>RSI / MA20 / MA50:</b> use them to judge whether a commodity move is stretched or trend-confirmed."])



    # ══════════ TAB 12 — BOND / COUPON CALCULATOR ═════════════════
    if active_tab == "bond_calculator":
        shead("Bond / Coupon Calculator")
        st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px'>Price a coupon bond, estimate yield sensitivity, duration, convexity, and key decision metrics.</div>", unsafe_allow_html=True)
        b1, b2, b3, b4, b5 = st.columns(5)
        face = b1.number_input("Face Value", min_value=1.0, value=1000.0, step=100.0, key="bond_face")
        coupon_rate = b2.number_input("Coupon Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.25, key="bond_coupon") / 100
        ytm = b3.number_input("Yield to Maturity %", min_value=0.0, max_value=40.0, value=5.5, step=0.25, key="bond_ytm") / 100
        years = b4.number_input("Years to Maturity", min_value=0.1, max_value=50.0, value=10.0, step=0.5, key="bond_years")
        freq_label = b5.selectbox("Coupon Frequency", ["Annual", "Semiannual", "Quarterly", "Monthly"], index=1, key="bond_freq")
        freq = {"Annual": 1, "Semiannual": 2, "Quarterly": 4, "Monthly": 12}[freq_label]

        price_b = bond_price(face, coupon_rate, ytm, years, freq)
        mac_dur, mod_dur, conv = bond_duration_convexity(face, coupon_rate, ytm, years, freq)
        current_yield = (face * coupon_rate / price_b) if price_b else 0
        premium_discount = "Premium" if price_b > face else "Discount" if price_b < face else "Par"
        approx_100bp = -mod_dur * 0.01 * price_b + 0.5 * conv * (0.01 ** 2) * price_b

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Estimated Bond Price", f"${price_b:,.2f}")
        m2.metric("Premium / Discount", premium_discount)
        m3.metric("Current Yield", f"{current_yield*100:.2f}%")
        m4.metric("Macaulay Duration", f"{mac_dur:.2f} yrs")
        m5.metric("Modified Duration", f"{mod_dur:.2f}")
        m6.metric("Convexity", f"{conv:.2f}")

        bc1, bc2 = st.columns([1.2, 1])
        with bc1:
            shead("Price Sensitivity to Yield Changes")
            pchart(bond_price_sensitivity_chart(face, coupon_rate, ytm, years, freq), "bond_sensitivity_chart")
        with bc2:
            shead("Decision Read")
            st.markdown(f"""
            <div class="news-card"><div class="news-title">Bond Risk Summary</div>
            <div class="news-summary">This bond is priced at <b>${price_b:,.2f}</b>, so it trades at a <b>{premium_discount.lower()}</b> versus par. Modified duration of <b>{mod_dur:.2f}</b> means a 1 percentage point rise in yield is roughly associated with a price move of about <b>${approx_100bp:,.2f}</b> per bond after convexity adjustment. Higher duration means more interest-rate risk; higher convexity generally makes the bond more favorable when rates move sharply.</div></div>
            """, unsafe_allow_html=True)
            shead("Cash Flow Schedule")
            st.dataframe(bond_cashflow_table(face, coupon_rate, ytm, min(years, 10), freq), use_container_width=True, hide_index=True)
        page_comment("Reading this page", ["<b>Bond price:</b> if coupon rate is below YTM, the bond usually trades below par; if coupon is above YTM, it usually trades above par.", "<b>Modified duration:</b> approximate % price change for a 1 percentage point yield move.", "<b>Convexity:</b> improves the duration estimate for larger rate changes.", "<b>Current yield:</b> annual coupon divided by price; it is not the same as YTM."])

    # ══════════ TAB 13 — OPTION CALCULATOR ════════════════════════
    if active_tab == "option_calculator":
        shead("Option Calculator")
        st.markdown("<div style='font-size:12px;color:#64748b;margin-bottom:12px'>Black-Scholes estimate for calls/puts, Greeks, breakeven, intrinsic value, and payoff at expiration.</div>", unsafe_allow_html=True)
        o1, o2, o3, o4 = st.columns(4)
        option_type = o1.selectbox("Option Type", ["Call", "Put"], index=0, key="opt_type")
        default_s = float(price) if price else 100.0
        S = o2.number_input("Underlying Price", min_value=0.01, value=float(round(default_s, 2)), step=1.0, key="opt_s")
        K = o3.number_input("Strike Price", min_value=0.01, value=float(round(default_s, 2)), step=1.0, key="opt_k")
        days_exp = o4.number_input("Days to Expiration", min_value=1, max_value=3650, value=30, step=1, key="opt_days")

        o5, o6, o7, o8 = st.columns(4)
        iv = o5.number_input("Implied Volatility %", min_value=0.1, max_value=300.0, value=35.0, step=1.0, key="opt_iv") / 100
        rf_rate = o6.number_input("Risk-Free Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.25, key="opt_rf") / 100
        div_yield = o7.number_input("Dividend Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.25, key="opt_q") / 100
        contract_qty = o8.number_input("Contracts", min_value=1, max_value=10000, value=1, step=1, key="opt_contracts")

        T = days_exp / 365.0
        opt = black_scholes(S, K, T, rf_rate, iv, option_type, div_yield)
        premium = opt["price"]
        breakeven = K + premium if option_type == "Call" else K - premium
        total_cost = premium * 100 * contract_qty
        moneyness = S / K - 1 if option_type == "Call" else K / S - 1
        prob_itm = _norm_cdf(opt["d2"]) if option_type == "Call" else _norm_cdf(-opt["d2"])

        om1, om2, om3, om4, om5, om6 = st.columns(6)
        om1.metric("Theoretical Premium", f"${premium:.2f}")
        om2.metric("Contract Cost", f"${total_cost:,.2f}")
        om3.metric("Breakeven", f"${breakeven:.2f}")
        om4.metric("Intrinsic Value", f"${opt['intrinsic']:.2f}")
        om5.metric("Time Value", f"${opt['time_value']:.2f}")
        om6.metric("Approx. ITM Probability", f"{prob_itm*100:.1f}%")

        g1, g2, g3, g4, g5 = st.columns(5)
        g1.metric("Delta", f"{opt['delta']:.3f}")
        g2.metric("Gamma", f"{opt['gamma']:.4f}")
        g3.metric("Theta / Day", f"${opt['theta']:.3f}")
        g4.metric("Vega / 1% IV", f"${opt['vega']:.3f}")
        g5.metric("Rho / 1% Rate", f"${opt['rho']:.3f}")

        oc1, oc2 = st.columns([1.2, 1])
        with oc1:
            shead("Expiration Payoff Curve")
            pchart(option_payoff_chart(S, K, premium, option_type), "option_payoff_chart")
        with oc2:
            shead("Decision Read")
            direction_note = "bullish" if option_type == "Call" else "bearish / hedge"
            st.markdown(f"""
            <div class="news-card"><div class="news-title">Option Risk Summary</div>
            <div class="news-summary">This <b>{option_type}</b> has a model premium of <b>${premium:.2f}</b> and breakeven at <b>${breakeven:.2f}</b>. Delta of <b>{opt['delta']:.3f}</b> shows directional exposure, while theta of <b>${opt['theta']:.3f}/day</b> shows daily time decay. Vega of <b>${opt['vega']:.3f}</b> means the option is sensitive to implied volatility changes. This is generally a <b>{direction_note}</b> instrument; position sizing matters because one contract controls 100 shares.</div></div>
            """, unsafe_allow_html=True)
            st.dataframe(pd.DataFrame([
                {"Metric": "Moneyness", "Value": f"{moneyness*100:+.2f}%"},
                {"Metric": "Max Loss for Buyer", "Value": f"${total_cost:,.2f}"},
                {"Metric": "Share Equivalent Delta", "Value": f"{opt['delta']*100*contract_qty:,.1f} shares"},
                {"Metric": "Daily Theta Estimate", "Value": f"${opt['theta']*100*contract_qty:,.2f}/day"},
                {"Metric": "Vega for Position", "Value": f"${opt['vega']*100*contract_qty:,.2f} per 1 IV point"},
            ]), use_container_width=True, hide_index=True)
        page_comment("Reading this page", ["<b>Delta:</b> directional exposure; 0.50 call delta behaves roughly like 50 shares per contract.", "<b>Theta:</b> time decay; usually negative for option buyers.", "<b>Vega:</b> sensitivity to implied volatility; high vega benefits if IV rises after entry.", "<b>Breakeven:</b> expiration price needed to cover premium, not a guarantee of profit before expiration."])

    # ══════════ TAB 8 — AI THESIS ═════════════════════════════════
    if active_tab == "ai_thesis":
        shead("Built-in AI Investment Thesis")
        st.markdown("""
        <div style="font-size:12px;color:#64748b;margin-bottom:12px">
          This thesis is generated from the dashboard's own valuation, quality, growth,
          momentum, and risk metrics. No Anthropic API key is needed.
        </div>""", unsafe_allow_html=True)
        ai_model = render_ai_model_selector("Risk preference model", key="ai_model_thesis_tab")
        st.caption(ai_model_description(ai_model))

        ai=built_in_ai_thesis(ticker,info,risk,hist_ta,model=ai_model)
        if not ai:
            st.error("AI thesis returned empty — try again.")
            return

        rec=ai.get("recommendation","—")
        rc=GREEN if rec in ("Buy", "Strong Buy") else RED if rec=="Sell" else AMBER

        ah1,ah2,ah3,ah4=st.columns(4)
        with ah1:
            st.markdown(f"""
            <div class="verdict-card" style="border-color:{rc};background:{rc}0d">
              <div style="font-size:10px;color:{rc};text-transform:uppercase;
                          letter-spacing:0.1em;margin-bottom:10px">AI Recommendation</div>
              <div style="font-size:2.5rem;font-weight:800;color:{rc};
                          letter-spacing:-0.02em">{rec}</div>
              <div style="font-size:12px;color:{rc};margin-top:8px">
                {ai.get('confidence',0)}% confidence</div>
            </div>""", unsafe_allow_html=True)
        with ah2:
            tgt=ai.get("price_target",0); up=ai.get("upside_pct",0)
            st.metric("12-Month Price Target",f"${tgt:.2f}" if tgt else "—")
            st.metric("Implied Upside / Downside",f"{up:+.1f}%" if up else "—")
        with ah3:
            st.metric("Investment Style",ai.get("style","—"))
            st.metric("Time Horizon",ai.get("horizon","—"))
            st.metric("Competitive Moat",ai.get("moat","—"))
        with ah4:
            st.metric("ESG Score",f"{ai.get('esg_score',0)}/100")
            st.metric("Overall Score",f"{ai.get('overall_score',0)}/100")
            st.metric("Insider Signal",ai.get("insider","—"))

        shead("Factor Scores")
        for lbl,sc in [
            ("Valuation",  ai.get("valuation_score", 50)),
            ("Quality",    ai.get("quality_score",   50)),
            ("Growth",     ai.get("growth_score",    50)),
            ("Momentum",   ai.get("momentum_score",  50)),
            ("Safety",     100-ai.get("risk_score",  50)),
        ]:
            score_bar(lbl,sc)

        shead("Investment Summary")
        st.markdown(f'<div style="font-size:14px;color:#94a3b8;line-height:1.8">'
                    f'{ai.get("summary","")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:12px;color:#475569;margin-top:8px">'
                    f'Moat: {ai.get("moat_desc","")}</div>', unsafe_allow_html=True)

        shead("Bull vs Bear Case")
        bb1,bb2=st.columns(2)
        with bb1:
            st.markdown(f"""
            <div class="bull-card">
              <div style="color:#10b981;font-weight:700;margin-bottom:10px;font-size:14px">▲ Bull Case</div>
              <div style="font-size:13px;color:#6ee7b7;line-height:1.8">{ai.get("bull","")}</div>
            </div>""", unsafe_allow_html=True)
        with bb2:
            st.markdown(f"""
            <div class="bear-card">
              <div style="color:#ef4444;font-weight:700;margin-bottom:10px;font-size:14px">▼ Bear Case</div>
              <div style="font-size:13px;color:#fca5a5;line-height:1.8">{ai.get("bear","")}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        cat_col,risk_col=st.columns(2)
        with cat_col:
            shead("Catalysts to Watch")
            for c_ in ai.get("catalysts",[]):
                st.markdown(f'<div class="signal-row">→ {c_}</div>', unsafe_allow_html=True)
        with risk_col:
            shead("Key Risks to Monitor")
            for r_ in ai.get("risks",[]):
                st.markdown(f'<div class="signal-row" style="border-color:rgba(239,68,68,0.25)">'
                            f'▲ {r_}</div>', unsafe_allow_html=True)

        shead("ESG Assessment")
        st.markdown(f'<div style="font-size:13px;color:#94a3b8;line-height:1.8">'
                    f'{ai.get("esg_notes","")}</div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:2rem;padding:12px 18px;background:#0d0f14;
                    border:1px solid #1e2433;border-radius:8px;
                    font-size:11px;color:#334155;line-height:1.7">
          ⚠️ Built-in thesis analysis is for informational purposes only and does not constitute
          financial advice. Always conduct your own due diligence and consult a
          qualified financial advisor before making investment decisions.
        </div>""", unsafe_allow_html=True)

        page_comment("Reading this page", ["<b>AI thesis:</b> this is a rule-based dashboard summary, not external financial advice.", "<b>Scores:</b> combine valuation, quality, growth, momentum, and risk; confirm with news and filings before trading.", "<b>Best use:</b> use it as a checklist to spot strengths and weaknesses quickly."])

if __name__ == "__main__":
    main()
