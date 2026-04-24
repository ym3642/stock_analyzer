"""
Stock Analyzer Pro — Premium Trading Terminal
Webull-style charts · Clean legends · No overlaps · Built-in AI thesis
Run: streamlit run app.py
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
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
import json, re, copy

st.set_page_config(
    page_title="Stock Analyzer Pro",
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
.block-container{padding:1.5rem 2rem 3rem!important;max-width:1600px!important;}

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

.comment-box{background:#10131a;border:1px solid #243044;border-radius:12px;padding:13px 15px;margin-top:18px;color:#94a3b8;font-size:12px;line-height:1.65;}
.comment-box b{color:#e2e8f0;}
.comment-title{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#64748b;font-weight:800;margin-bottom:6px;}
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
#  LANGUAGE / TRANSLATION LAYER
# ══════════════════════════════════════════════════════════════════
LANG_OPTIONS = {"English": "en", "简体中文": "zh"}

ZH = {
    "Stock Analyzer": "股票分析器", "PROFESSIONAL EDITION": "专业版", "Language": "语言",
    "Overview": "概览", "Valuation": "估值", "Risk": "风险", "Industry": "行业", "Technical": "技术分析", "Comparison": "对比", "News": "新闻", "Market Rankings": "市场排名", "Global Indexes": "全球指数", "Commodities": "大宗商品", "AI Thesis": "AI投资论点",
    "Price Chart": "价格图表", "Fundamentals": "基本面", "About": "公司简介", "Business Summary": "业务摘要", "Valuation Multiples": "估值倍数", "Analyst Consensus": "分析师共识",
    "Interactive DCF Fair Value Calculator": "交互式DCF公允价值计算器", "Quality & Profitability": "质量与盈利能力", "Risk & Performance Metrics vs S&P 500": "相对标普500的风险与表现指标",
    "Drawdown from Peak": "峰值回撤", "Daily Return Distribution": "日收益率分布", "Rolling 60-Day Sharpe Ratio": "60日滚动夏普比率", "Annualised Rolling Volatility": "年化滚动波动率",
    "Financial Health": "财务健康状况", "Industry Snapshot": "行业概况", "Peer Comparison": "同业比较", "Technical Indicators": "技术指标", "Support / Resistance": "支撑位 / 阻力位",
    "Latest Stock / Company News": "最新股票/公司新闻", "Built-in AI Investment Thesis": "内置AI投资论点", "Built-in AI-Style Comparison Summary": "内置AI风格对比总结",
    "Ticker Symbol": "股票代码", "Historical Data Range": "历史数据范围", "Chart View Window": "图表显示窗口", "Price Chart Overlays": "价格图表叠加指标", "Moving Average Lines": "移动平均线",
    "Data period": "数据周期", "Chart window": "图表窗口", "Show pre-market / after-hours curve": "显示盘前/盘后曲线",
    "Regular-hours view: 9:30 AM–4:00 PM ET only. Overnight gaps are removed from the x-axis.": "常规交易时段视图：仅显示美国东部时间上午9:30至下午4:00，横轴会移除隔夜空白。",
    "Market Cap": "市值", "P/E (TTM)": "市盈率(TTM)", "52W High": "52周高点", "52W Low": "52周低点", "Avg Volume": "平均成交量", "Div Yield": "股息率",
    "Revenue": "营收", "Net Income": "净利润", "EBITDA": "EBITDA", "Free Cash Flow": "自由现金流", "EPS (TTM)": "每股收益(TTM)", "Forward EPS": "预期每股收益",
    "Gross Margin": "毛利率", "Net Margin": "净利率", "Op. Margin": "营业利润率", "Rev Growth YoY": "营收同比增长", "EPS Growth": "EPS增长", "ROE": "净资产收益率", "ROA": "资产收益率",
    "Total Debt": "总债务", "Total Cash": "总现金", "Debt/Equity": "债务/权益", "Current Ratio": "流动比率", "Quick Ratio": "速动比率", "Book Value/Sh": "每股账面价值", "Payout Ratio": "派息率",
    "Beta": "贝塔系数", "Short % Float": "流通股做空比例", "Shares Out": "发行股数", "Float": "流通股", "CEO": "首席执行官", "Sector": "板块", "Employees": "员工数", "Country": "国家",
    "Trailing P/E": "历史市盈率", "Forward P/E": "预期市盈率", "PEG Ratio": "PEG比率", "Price / Book": "市净率", "Price / Sales": "市销率", "EV / EBITDA": "企业价值/EBITDA", "EV / Revenue": "企业价值/营收",
    "DCF Intrinsic Value": "DCF内在价值", "Buy Below (w/ MoS)": "安全边际买入价", "Current Price": "当前价格", "DCF Upside": "DCF上涨空间",
    "Annual Vol.": "年化波动率", "Sharpe Ratio": "夏普比率", "Sortino": "索提诺比率", "Max Drawdown": "最大回撤", "Calmar Ratio": "卡玛比率", "1yr Return": "1年收益率",
    "Alpha vs SPY": "相对SPY阿尔法", "VaR 95%": "95%风险价值", "CVaR 95%": "95%条件风险价值", "Win Rate": "胜率", "R² vs SPY": "相对SPY的R²", "Tracking Err": "跟踪误差", "Info Ratio": "信息比率",
    "Size": "规模", "Exchange": "交易所", "RSI (14-day)": "RSI(14日)", "ADX (14-day)": "ADX(14日)", "ATR (14-day)": "ATR(14日)", "Volatility 20d": "20日波动率",
    "Important Headlines": "重要新闻数", "Positive": "利好", "Negative": "利空", "Neutral": "中性", "Avg Influence": "平均影响", "Search news by keyword": "按关键词搜索新闻", "Order news by": "新闻排序",
    "Importance first": "重要性优先", "Newest first": "最新优先", "Update News": "更新新闻", "Open source": "打开来源", "Influence": "股价影响", "Importance": "重要性",
    "No short summary was provided by the source.": "来源未提供简短摘要。", "No matching recent news found. Try a broader keyword or click Update News.": "未找到匹配的近期新闻。请尝试更宽泛的关键词，或点击更新新闻。",
    "Priority: Yahoo Finance/yfinance first, then WSJ/RSS and broad financial news. Duplicate/overlapping headlines are filtered.": "优先级：Yahoo Finance/yfinance优先，其次为WSJ/RSS和其他财经新闻；重复或重叠标题会被过滤。",
    "Market Movers & Volatility Ranking": "市场异动与波动率排名", "Global Index Performance": "全球主要指数表现", "Industry Filter": "行业筛选", "Ranking Size": "排名数量", "Ranking Metric": "排名指标", "Update Rankings": "更新排名", "Top Movers Table": "异动股票表", "Top Price Change Chart": "价格变动排名图", "Top Volatility Chart": "波动率排名图", "All Industries": "全部行业", "Technology": "科技", "Semiconductors": "半导体", "Software": "软件", "Financials": "金融", "Energy": "能源", "Healthcare": "医疗保健", "Consumer": "消费", "Ticker": "股票代码", "Company": "公司", "Last Price": "最新价", "Change $": "价格变化$", "Change %": "涨跌幅%", "20D Vol %": "20日波动率%", "Volume Ratio": "成交量倍数", "Investment Note": "投资备注", "Major Index Curves": "主要指数走势", "Index Ranking by % Change": "按涨跌幅排名的指数", "Commodity Dashboard": "大宗商品仪表盘", "Commodity Curves": "大宗商品走势", "Commodity Indicators": "大宗商品指标", "Display indexes on chart": "选择图表显示的指数", "Display commodities on chart": "选择图表显示的大宗商品",
}

FIN_GLOSSARY = {
    "earnings": "财报/盈利", "revenue": "营收", "guidance": "业绩指引", "analyst": "分析师", "rating": "评级", "price target": "目标价", "upgrade": "上调评级", "downgrade": "下调评级",
    "shares": "股票", "stock": "股票", "market": "市场", "profit": "利润", "loss": "亏损", "margin": "利润率", "cash flow": "现金流", "free cash flow": "自由现金流", "valuation": "估值",
    "volatility": "波动率", "risk": "风险", "lawsuit": "诉讼", "investigation": "调查", "acquisition": "收购", "merger": "合并", "dividend": "股息", "buyback": "回购",
    "cloud": "云业务", "AI": "人工智能", "software": "软件", "subscription": "订阅", "demand": "需求", "growth": "增长",
}

def lang_code():
    return st.session_state.get("lang_code", "en")

def tr(text):
    if lang_code() != "zh":
        return text
    return ZH.get(str(text).strip(), text)

@st.cache_data(ttl=86400, show_spinner=False)
def translate_text_optional(text, target_lang="zh"):
    text = clean_text(text or "") if 'clean_text' in globals() else (text or "")
    if not text or target_lang != "zh":
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="zh-CN").translate(text[:4500])
        if translated:
            return translated
    except Exception:
        pass
    out = text
    for en, zh in sorted(FIN_GLOSSARY.items(), key=lambda x: -len(x[0])):
        out = re.sub(rf"\b{re.escape(en)}\b", zh, out, flags=re.I)
    return out

try:
    from streamlit.delta_generator import DeltaGenerator
    _orig_metric = DeltaGenerator.metric
    def _metric_translated(self, label, value, delta=None, *args, **kwargs):
        return _orig_metric(self, tr(label), value, delta, *args, **kwargs)
    DeltaGenerator.metric = _metric_translated
except Exception:
    pass

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
#  DATA LAYER
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fetch_stock(ticker, period="2y"):
    try:
        stk  = yf.Ticker(ticker)
        info = stk.info
        if not info or "longName" not in info:
            return None, f"Ticker '{ticker}' not found."
        hist = stk.history(period=period, auto_adjust=True)
        if hist.empty:
            return None, "No price history returned."
        return {"info": info, "hist": hist}, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_chart_history(ticker, period="1y", interval="1d", prepost=False):
    """Fetch chart data separately so short windows can use intraday bars.
    prepost=True includes pre-market and after-hours bars for intraday charts.
    """
    try:
        h = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True, prepost=prepost)
        if h.empty:
            return None, "No chart history returned."
        return h, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_peers(tickers: tuple, period="1y"):
    out = {}
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period=period, auto_adjust=True)
            if not h.empty:
                out[t] = {"info": s.info, "hist": h}
        except: pass
    return out


@st.cache_data(ttl=300, show_spinner=False)
def fetch_spy(period="2y"):
    return yf.Ticker("SPY").history(period=period, auto_adjust=True)


# ══════════════════════════════════════════════════════════════════
#  TECHNICALS
# ══════════════════════════════════════════════════════════════════
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
    c = df["Close"].values
    highs, lows = [], []
    for i in range(window, len(c) - window):
        seg = c[i-window:i+window+1]
        if c[i] == seg.max(): highs.append(float(c[i]))
        if c[i] == seg.min(): lows.append(float(c[i]))
    def cluster(pts, tol=0.01):
        if not pts: return []
        pts = sorted(set(pts)); out = [pts[0]]
        for p in pts[1:]:
            if (p-out[-1])/out[-1] > tol: out.append(p)
        return out
    cur = float(c[-1])
    return (sorted([x for x in cluster(lows)  if x < cur], reverse=True)[:n],
            sorted([x for x in cluster(highs) if x > cur])[:n])


# ══════════════════════════════════════════════════════════════════
#  RISK
# ══════════════════════════════════════════════════════════════════
def calc_risk(hist, spy):
    """Risk metrics using date-aligned daily returns.

    Notes:
    - Uses adjusted close from yfinance histories.
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

    rf = 0.053 / 252
    std_r = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
    std_b = float(np.std(b, ddof=1)) if len(b) > 1 else 0.0
    beta = float(np.cov(r, b, ddof=1)[0, 1] / np.var(b, ddof=1)) if len(r) > 2 and np.var(b, ddof=1) else 0.0
    mu_r = float(np.mean(r)) * 252 if len(r) else 0.0
    mu_b = float(np.mean(b)) * 252 if len(b) else 0.0
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
        ret1y=round(mu_r * 100, 2), sharpe=round(sharpe, 3), sortino=round(sortino, 3),
        calmar=round(calmar, 3), max_dd=round(max_dd, 2), var95=round(var95, 2),
        cvar95=round(cvar95, 2), win=round(win, 1), r2=round(r2, 3),
        te=round(te, 2), ir=round(ir, 3),
        ret_s=ret_s, cum_s=cum_s, dd_s=dd_s, roll_sh=roll_sh,
    )


# ══════════════════════════════════════════════════════════════════
#  DCF
# ══════════════════════════════════════════════════════════════════
def dcf_value(fcf, g, tg, wacc, yrs=10):
    if fcf<=0: return 0.0
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

def score_from_metrics(info, risk, hist_ta=None):
    pe = safe_float(info.get("trailingPE"), 0)
    fpe = safe_float(info.get("forwardPE"), pe)
    ps = safe_float(info.get("priceToSalesTrailing12Months"), 0)
    rev_g = safe_float(info.get("revenueGrowth"), 0) * 100
    margin = safe_float(info.get("profitMargins"), 0) * 100
    roe = safe_float(info.get("returnOnEquity"), 0) * 100
    debt_eq = safe_float(info.get("debtToEquity"), 0) / 100
    beta = safe_float(risk.get("beta"), 1)
    sharpe = safe_float(risk.get("sharpe"), 0)
    vol = safe_float(risk.get("vol"), 30)
    max_dd = abs(safe_float(risk.get("max_dd"), 25))

    valuation = 55
    valuation += 18 if pe and pe < 18 else 8 if pe and pe < 28 else -10 if pe and pe > 45 else 0
    valuation += 6 if fpe and pe and fpe < pe else 0
    valuation += -8 if ps and ps > 10 else 5 if ps and ps < 4 else 0

    quality = 45 + min(max(margin, -10), 35) * 0.8 + min(max(roe, 0), 40) * 0.45
    quality += 5 if debt_eq < 0.6 else -10 if debt_eq > 2 else 0
    growth = 50 + min(max(rev_g, -20), 40) * 0.9

    momentum = 50
    if hist_ta is not None and len(hist_ta) > 60:
        last = hist_ta.iloc[-1]
        price = safe_float(last.get("Close"), 0)
        ma20 = safe_float(last.get("MA20"), 0)
        ma50 = safe_float(last.get("MA50"), 0)
        rsi = safe_float(last.get("RSI"), 50)
        momentum += 10 if ma20 and price > ma20 else 0
        momentum += 10 if ma50 and price > ma50 else 0
        momentum += 5 if 45 <= rsi <= 65 else 0
        momentum += -10 if rsi > 75 else -5 if rsi < 30 else 0

    risk_score = 50 + beta * 8 + max(vol - 25, 0) * 0.6 + max(max_dd - 20, 0) * 0.6 - sharpe * 8
    safety = 100 - risk_score
    overall = 0.24 * valuation + 0.24 * quality + 0.18 * growth + 0.18 * momentum + 0.16 * safety
    return {
        "valuation_score": clamp(valuation),
        "quality_score": clamp(quality),
        "growth_score": clamp(growth),
        "momentum_score": clamp(momentum),
        "risk_score": clamp(risk_score),
        "overall_score": clamp(overall),
    }

def built_in_ai_thesis(ticker, info, risk, hist_ta=None):
    scores = score_from_metrics(info, risk, hist_ta)
    overall = scores["overall_score"]
    rec = "Buy" if overall >= 68 else "Hold" if overall >= 45 else "Sell"
    confidence = clamp(50 + abs(overall - 50) * 0.8)
    price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"), 0)
    upside = (overall - 55) * 0.9
    target = price * (1 + upside / 100) if price else 0
    sector = info.get("sector", "the market") or "the market"
    industry = info.get("industry", "its industry") or "its industry"
    pe = info.get("trailingPE", "N/A")
    rev_g = safe_float(info.get("revenueGrowth"), 0) * 100
    margin = safe_float(info.get("profitMargins"), 0) * 100
    beta = safe_float(risk.get("beta"), 1)
    sharpe = safe_float(risk.get("sharpe"), 0)
    vol = safe_float(risk.get("vol"), 0)
    style = "Quality Growth" if scores["quality_score"] >= 65 and scores["growth_score"] >= 60 else "Value / Stability" if scores["valuation_score"] >= 65 else "Cyclical / Momentum" if scores["momentum_score"] >= 65 else "Balanced"
    moat = "Wide" if scores["quality_score"] >= 72 else "Moderate" if scores["quality_score"] >= 55 else "Unclear"

    bull = f"{ticker} screens best where its quality, growth, and momentum scores are strongest. Revenue growth is about {rev_g:.1f}% and net margin is about {margin:.1f}%, which gives a quick view of operating strength. If the company keeps converting growth into earnings and the trend remains above key moving averages, the stock has room to outperform peers in {industry}."
    bear = f"The main weakness is risk and valuation discipline. Beta is about {beta:.2f}, annualized volatility is about {vol:.1f}%, and Sharpe is about {sharpe:.2f}. If earnings expectations fall, valuation multiples such as P/E ({pe}) can compress quickly."
    summary = f"Built-in thesis: {ticker} is rated {rec} with an overall score of {overall}/100. The view is based on valuation, profitability, growth, momentum, and risk metrics from the dashboard, not an external paid API."

    return {
        "recommendation": rec, "confidence": confidence, "price_target": round(target, 2),
        "upside_pct": round(upside, 1), "style": style, "horizon": "6-12 months",
        "overall_score": overall, **scores, "moat": moat,
        "moat_desc": f"Moat assessment is inferred from margins, ROE, balance sheet strength, and industry position within {sector}.",
        "bull": bull, "bear": bear, "summary": summary,
        "catalysts": ["Earnings beats and higher guidance", "Improving margins or free cash flow", "Sustained strength above moving averages", "Sector rotation into " + sector],
        "risks": ["Multiple compression", "Revenue growth slowdown", "High volatility or market beta", "Technical breakdown below support"],
        "esg_score": clamp(55 + scores["quality_score"] * 0.25),
        "esg_notes": "ESG is not deeply modeled here; this score is a conservative placeholder inferred from company stability and quality metrics.",
        "insider": "Neutral", "peers": [],
    }

def comparison_paragraph(t1, info1, risk1, ta1, t2, info2, risk2, ta2):
    s1 = score_from_metrics(info1, risk1, ta1)
    s2 = score_from_metrics(info2, risk2, ta2)
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
    publisher = clean_text(publisher or (content.get("publisher") if isinstance(content, dict) else "") or (item.get("publisher", "Yahoo Finance") if isinstance(item, dict) else "Yahoo Finance"))
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
    return {"ticker": ticker, "title": title, "summary": summary, "publisher": publisher or "Yahoo Finance", "link": link, "ts": ts, "source_rank": 1}


def sentiment_and_impact(title, summary, ticker=""):
    text = f"{title} {summary}".lower()
    pos_words = {"beat": 10, "beats": 10, "raises": 10, "raised": 8, "upgrade": 9, "upgraded": 9, "buy rating": 8, "strong demand": 8, "record": 7, "profit": 5, "growth": 5, "partnership": 5, "contract": 6, "launch": 4, "outperform": 8, "higher target": 8, "surge": 6, "rally": 5, "approval": 7, "expands": 5}
    neg_words = {"miss": -10, "misses": -10, "cuts": -9, "cut": -6, "downgrade": -9, "downgraded": -9, "sell rating": -8, "lawsuit": -8, "probe": -8, "investigation": -8, "sec": -5, "slump": -6, "drops": -5, "falls": -5, "weak": -5, "slowdown": -7, "guidance cut": -12, "layoff": -5, "loss": -5, "warning": -6, "tariff": -4, "concern": -4, "risk": -3, "bearish": -6, "underperform": -8}
    score = 0
    hits = []
    for w, v in pos_words.items():
        if w in text:
            score += v; hits.append(w)
    for w, v in neg_words.items():
        if w in text:
            score += v; hits.append(w)
    importance_terms = ["earnings", "revenue", "guidance", "analyst", "rating", "target", "acquisition", "merger", "lawsuit", "investigation", "fed", "rate", "ai", "cloud", "ceo", "cfo", "sec"]
    importance = min(100, 25 + min(len(hits) * 9, 35) + sum(6 for term in importance_terms if term in text))
    if ticker and ticker.lower() in text:
        importance = min(100, importance + 10)
    if score > 5:
        sent = "Positive"
    elif score < -5:
        sent = "Negative"
    else:
        sent = "Neutral"
    influence = max(-100, min(100, score * 3 + (importance - 50) * (1 if score > 0 else -1 if score < 0 else 0) * 0.35))
    return sent, int(round(influence)), int(round(importance))


@st.cache_data(ttl=900, show_spinner=False)
def fetch_news_items(ticker, keyword="", refresh_token=0):
    del refresh_token
    items = []
    try:
        yf_news = yf.Ticker(ticker).news or []
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
    kw = keyword.strip().lower()
    dedup = {}
    for n in items:
        title = n.get("title", "")
        summary = n.get("summary", "")
        if not title:
            continue
        if kw and kw not in f"{title} {summary} {n.get('publisher','')}".lower():
            continue
        key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()[:90]
        sent, influence, importance = sentiment_and_impact(title, summary, ticker)
        n.update({"sentiment": sent, "influence": influence, "importance": importance})
        old = dedup.get(key)
        if old is None or (n["source_rank"], -n["ts"], -n["importance"]) < (old["source_rank"], -old["ts"], -old["importance"]):
            dedup[key] = n
    out = list(dedup.values())
    out.sort(key=lambda x: (x.get("importance", 0), x.get("ts", 0)), reverse=True)
    return out[:20]


def render_news_item(n):
    ts = n.get("ts") or 0
    when = datetime.fromtimestamp(ts).strftime("%b %d, %Y %I:%M %p") if ts else "Recent"
    sent = n.get("sentiment", "Neutral")
    sent_display = tr(sent)
    cls = "news-positive" if sent == "Positive" else "news-negative" if sent == "Negative" else "news-neutral"
    link = n.get("link", "")
    raw_title = n.get("title", "Untitled")
    raw_summary = n.get("summary", "")
    title = html.escape(translate_text_optional(raw_title, lang_code()) if lang_code() == "zh" else raw_title)
    summary = html.escape(translate_text_optional(raw_summary, lang_code()) if lang_code() == "zh" else raw_summary)
    publisher = html.escape(n.get("publisher", "News"))
    url_html = f'<a href="{html.escape(link)}" target="_blank" style="color:#60a5fa;text-decoration:none">{tr("Open source")} ↗</a>' if link else ""
    body = f'''
    <div class="news-card">
      <div class="news-meta">{publisher} · {when}</div>
      <div class="news-title">{title}</div>
      <span class="news-pill {cls}">{sent_display}</span>
      <span class="news-pill">{tr("Influence")} {n.get('influence',0):+d}/100</span>
      <span class="news-pill">{tr("Importance")} {n.get('importance',0)}/100</span>
      <div class="news-summary">{summary if summary else tr('No short summary was provided by the source.')}</div>
      <div style="font-size:12px;margin-top:8px">{url_html}</div>
    </div>
    '''
    st.markdown(body, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  CHART BUILDERS  — clean Webull style, legends as HTML below
# ══════════════════════════════════════════════════════════════════

def price_chart(df, ticker, days, active_mas, show_bb, show_vol):
    """Main OHLCV candlestick chart with optional MA, BB, volume+vol panel."""
    dp = df.tail(days)
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
    r   = (ret*100).round(3)
    mn  = float(r.mean())
    var = float(np.percentile(r, 5))
    fig = _indicator_fig(220)
    fig.add_trace(go.Histogram(x=r, nbinsx=80,
        marker=dict(color=BLUE, opacity=0.55), name="Returns",
        hovertemplate="Return: %{x:.2f}%%<br>Count: %{y}"))
    fig.add_vline(x=mn,  line_dash="dash", line_color=GREEN, line_width=1.5,
                  annotation=dict(text=f"Mean {mn:.2f}%", font_color=GREEN,
                                  font_size=10, y=1.0, yref="paper"))
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


def apply_market_axis(fig):
    """Make intraday charts skip overnight/weekend gaps when extended hours are hidden."""
    intraday = bool(st.session_state.get("chart_is_intraday", False))
    show_ext = bool(st.session_state.get("show_ext_hours", False))
    if intraday and not show_ext:
        fig.update_xaxes(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[16, 9.5], pattern="hour"),
            ],
            tickformat="%b %d<br>%I:%M %p",
            hoverformat="%b %d, %Y %I:%M %p",
        )
    elif intraday:
        fig.update_xaxes(
            tickformat="%b %d<br>%I:%M %p",
            hoverformat="%b %d, %Y %I:%M %p",
        )
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
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

def pchart(fig, key):
    # Keep Plotly labels clean, remove stray Plotly/Streamlit "undefined" text,
    # and compress intraday axes so hidden non-trading hours do not appear as 00:00 gaps.
    fig.update_layout(title=dict(text=""), showlegend=False)
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
    st.plotly_chart(fig, use_container_width=True, key=key)



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
@st.cache_data(ttl=300, show_spinner=False)
def ranking_snapshot(tickers_tuple, period="3mo"):
    rows=[]
    for t in tickers_tuple:
        try:
            y=yf.Ticker(t); h=y.history(period=period, auto_adjust=True)
            if h is None or h.empty or len(h)<2: continue
            close=h["Close"].dropna(); last=float(close.iloc[-1]); prev=float(close.iloc[-2])
            chg=last-prev; pct=chg/prev*100 if prev else 0.0
            ret=close.pct_change().dropna(); vol20=float(ret.tail(20).std()*np.sqrt(252)*100) if len(ret)>=2 else 0.0
            v=h["Volume"].dropna() if "Volume" in h else pd.Series(dtype=float)
            vol_ratio=float(v.iloc[-1]/v.tail(20).mean()) if len(v)>=5 and v.tail(20).mean() else 0.0
            try: inf=y.get_info()
            except Exception: inf={}
            market_cap = float(inf.get("marketCap") or 0)
            dollar_vol = float(last * v.iloc[-1]) if len(v) else 0.0
            momentum_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 and close.iloc[-6] else pct
            gap_pct = float((h["Open"].iloc[-1] / close.iloc[-2] - 1) * 100) if "Open" in h and len(close) >= 2 and close.iloc[-2] else 0.0
            liquidity_score = min(100.0, max(0.0, np.log10(max(dollar_vol, 1)) * 10 - 35))
            trader_score = (abs(pct) * 1.8) + (vol20 * 0.20) + (vol_ratio * 7.0) + (abs(momentum_5d) * 0.8) + (liquidity_score * 0.15)
            rows.append({
                "Ticker": t,
                "Company": str(inf.get("shortName") or inf.get("longName") or t)[:42],
                "Country": inf.get("country") or "Unknown",
                "Sector": inf.get("sector") or "Unknown",
                "Industry": inf.get("industry") or "Unknown",
                "Market Cap": round(market_cap, 0),
                "Market Cap $B": round(market_cap / 1e9, 2) if market_cap else 0,
                "Last Price": round(last, 2),
                "Change $": round(chg, 2),
                "Change %": round(pct, 2),
                "5D Momentum %": round(momentum_5d, 2),
                "Opening Gap %": round(gap_pct, 2),
                "20D Vol %": round(vol20, 2),
                "Volume Ratio": round(vol_ratio, 2),
                "Dollar Volume $M": round(dollar_vol / 1e6, 2),
                "Liquidity Score": round(liquidity_score, 1),
                "Trader Composite Score": round(trader_score, 1),
                "Investment Note": _ranking_note(pct, vol20, vol_ratio),
            })
        except Exception: continue
    return pd.DataFrame(rows)
@st.cache_data(ttl=300, show_spinner=False)
def index_snapshot(period="1mo"):
    rows = []
    curves = {}
    for order, meta in enumerate(GLOBAL_INDEXES):
        name, sym = meta["Index"], meta["Ticker"]
        try:
            h = yf.Ticker(sym).history(period=period, auto_adjust=True)
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

@st.cache_data(ttl=300, show_spinner=False)
def commodity_snapshot(period="3mo"):
    rows = []
    curves = {}
    for meta in COMMODITIES:
        name, sym = meta["Commodity"], meta["Ticker"]
        try:
            h = yf.Ticker(sym).history(period=period, auto_adjust=True)
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
                st.rerun()
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key)


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
        # Professional static product header first; language selector sits below it.
        st.markdown("""
        <div style="padding:0.45rem 0 0.75rem;border-bottom:1px solid #1f2937;margin-bottom:0.65rem;">
          <div style="font-size:18px;font-weight:760;color:#e5e7eb;letter-spacing:-0.025em;line-height:1.12;">
            Stock Analyzer Pro</div>
          <div style="font-size:9px;color:#64748b;margin-top:5px;letter-spacing:0.12em;font-weight:650;">
            EQUITY RESEARCH · RISK · NEWS</div>
        </div>""", unsafe_allow_html=True)

        lang_choice = st.selectbox("Language / 语言", list(LANG_OPTIONS.keys()), index=0, key="language_select")
        st.session_state["lang_code"] = LANG_OPTIONS.get(lang_choice, "en")

        if "ticker" not in st.session_state:
            st.session_state.ticker = "AAPL"

        st.markdown(f'<div style="font-size:10px;color:#475569;text-transform:uppercase;'
                    f'letter-spacing:0.1em;margin:0.2rem 0 0.45rem">{tr("Ticker Symbol")}</div>',
                    unsafe_allow_html=True)
        ticker_input = st.text_input("ticker_sym", value=st.session_state.ticker,
                                     placeholder="AAPL, MSFT, TSLA…",
                                     label_visibility="collapsed").upper().strip()
        if ticker_input: st.session_state.ticker = ticker_input

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
            help="Only affects intraday windows. It includes extended-hours bars when Yahoo Finance provides them."
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
        ma_labels   = {"MA5":"5-Day SMA","MA10":"10-Day SMA","MA20":"20-Day SMA",
                       "MA50":"50-Day SMA","MA120":"120-Day SMA","MA200":"200-Day SMA"}
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
        st.button("⟳  Analyze", type="primary", use_container_width=True)
        with st.expander("Data / disclaimer", expanded=False):
            st.markdown('<div style="font-size:10px;color:#334155;line-height:1.7">'
                        'Price data: Yahoo Finance<br>Indicators: ta library<br>'
                        'AI Thesis: built-in rule engine<br>⚠️ Not financial advice.</div>',
                        unsafe_allow_html=True)

    ticker = st.session_state.ticker

    # ── Fetch ──────────────────────────────────────────────────────
    with st.spinner(f"Fetching {ticker}…"):
        data, err = fetch_stock(ticker, period)
    if err or not data:
        st.error(f"**{ticker}**: {err or 'Not found'}"); return

    info = data["info"]; hist = data["hist"]
    with st.spinner("Fetching chart window…"):
        chart_hist, chart_err = fetch_chart_history(ticker, chart_cfg["period"], chart_cfg["interval"], show_ext_hours)
        if chart_err or chart_hist is None or chart_hist.empty:
            chart_hist = hist
            st.warning(f"Recent chart data was unavailable, so the chart fell back to {period_label}: {chart_err}")
        elif chart_is_intraday and not show_ext_hours:
            chart_hist = regular_session_only(chart_hist)

    with st.spinner("Calculating indicators…"):
        hist_ta = calc_ta(hist)
        chart_ta = calc_ta(chart_hist)
    with st.spinner("Running risk analytics vs S&P 500…"):
        spy  = fetch_spy(period); risk = calc_risk(hist, spy)

    # ── Header ─────────────────────────────────────────────────────
    name    = info.get("longName", ticker)
    price   = float(info.get("currentPrice") or info.get("regularMarketPrice") or hist["Close"].iloc[-1])
    prev    = float(info.get("previousClose") or hist["Close"].iloc[-2])
    chg     = price-prev; chg_pct = chg/prev*100
    chg_clr = GREEN if chg>=0 else RED; sign = "+" if chg>=0 else ""

    last_stamp = chart_ta.index[-1].strftime('%b %d, %Y %H:%M') if hasattr(chart_ta.index[-1], 'strftime') else datetime.now().strftime('%b %d, %Y')
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
        <div style="font-size:11px;color:#334155;margin-top:5px;white-space:nowrap">{last_stamp} · Yahoo Finance</div>
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
    ms[5].metric("Div Yield",   with_avg(fpct(info.get("dividendYield")) if info.get("dividendYield") else "None", "div_yield", info))
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── TABS ───────────────────────────────────────────────────────
    tabs = st.tabs([f"  📊  {tr('Overview')}  ", f"  💰  {tr('Valuation')}  ", f"  ⚠️  {tr('Risk')}  ",
                    f"  🏭  {tr('Industry')}  ", f"  📉  {tr('Technical')}  ", f"  🔁  {tr('Comparison')}  ",
                    f"  📰  {tr('News')}  ", f"  🤖  {tr('AI Thesis')}  ", f"  🏆  {tr('Market Rankings')}  ",
                    f"  🛢️  {tr('Commodities')}  ", f"  🌍  {tr('Global Indexes')}  "])

    # ══════════ TAB 1 — OVERVIEW ══════════════════════════════════
    with tabs[0]:
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
    with tabs[1]:
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
            na=int(info.get("numberOfAnalystOpinions",0) or 0)
            rk=(info.get("recommendationKey") or "—").upper()
            rm=float(info.get("recommendationMean",3) or 3)
            rc=GREEN if rm<=2 else RED if rm>=4 else AMBER
            up=(tm/price-1)*100 if price and tm else 0
            up_c=GREEN if up>0 else RED
            st.markdown(f"""
            <div style="background:#13161e;border:1px solid #1e2433;border-radius:12px;
                        padding:1.5rem;margin-bottom:1rem;text-align:center">
              <div style="font-size:10px;color:#475569;text-transform:uppercase;
                          letter-spacing:0.1em;margin-bottom:10px">Consensus · {na} Analysts</div>
              <div style="font-size:2.5rem;font-weight:800;color:{rc};letter-spacing:-0.02em">{rk}</div>
              <div style="font-size:12px;color:#475569;margin-top:6px">
                Score {rm:.1f}/5.0 &nbsp;(1=Strong Buy · 5=Strong Sell)</div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
              <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:10px;color:#475569;margin-bottom:5px">LOW TARGET</div>
                <div style="font-size:1.2rem;font-weight:600;color:{RED};font-family:monospace">${tl:.0f}</div>
              </div>
              <div style="background:#13161e;border:1px solid #252a38;border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:10px;color:#475569;margin-bottom:5px">CONSENSUS</div>
                <div style="font-size:1.5rem;font-weight:700;color:{GREEN};font-family:monospace">${tm:.0f}</div>
              </div>
              <div style="background:#13161e;border:1px solid #1e2433;border-radius:10px;padding:12px;text-align:center">
                <div style="font-size:10px;color:#475569;margin-bottom:5px">HIGH TARGET</div>
                <div style="font-size:1.2rem;font-weight:600;color:{GREEN};font-family:monospace">${th:.0f}</div>
              </div>
            </div>
            <div style="text-align:center;font-size:1.1rem;font-weight:700;
                        color:{up_c};font-family:monospace">
              {"▲" if up>0 else "▼"} {abs(up):.1f}% implied upside</div>
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
    with tabs[2]:
        rcfg1, rcfg2 = st.columns([1, 4])
        risk_chart_period = rcfg1.selectbox("Risk chart range", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "20y"], index=1, key="risk_chart_period")
        rcfg2.caption("Risk charts use their own range. Default is 3 months.")
        with st.spinner(f"Updating risk charts for {risk_chart_period}..."):
            risk_data, risk_err = fetch_stock(ticker, risk_chart_period)
            risk_hist_local = risk_data["hist"] if risk_data and not risk_err else hist
            risk_ta_local = calc_ta(risk_hist_local)
            risk_spy_local = fetch_spy(risk_chart_period)
            risk_view = calc_risk(risk_hist_local, risk_spy_local)

        shead("Risk & Performance Metrics vs S&P 500")
        r1,r2,r3,r4,r5,r6,r7=st.columns(7)
        r1.metric("Beta",         with_avg(f"{risk['beta']:.2f}", "beta", info))
        r2.metric("Annual Vol.",  with_avg(f"{risk['vol']:.1f}%", "vol", info))
        r3.metric("Sharpe Ratio", with_avg(f"{risk['sharpe']:.2f}", "sharpe", info))
        r4.metric("Sortino",      with_avg(f"{risk['sortino']:.2f}", "sortino", info))
        r5.metric("Max Drawdown", with_avg(f"{risk['max_dd']:.1f}%", "max_dd", info))
        r6.metric("Calmar Ratio", with_avg(f"{risk['calmar']:.2f}", "calmar", info))
        r7.metric("1yr Return",   f"{risk['ret1y']:.1f}%")
        r8,r9,r10,r11,r12,r13,r14=st.columns(7)
        r8.metric("Alpha vs SPY", f"{risk['alpha']:.2f}%")
        r9.metric("VaR 95%",      with_avg(f"{risk['var95']:.2f}%", "var95", info))
        r10.metric("CVaR 95%",    with_avg(f"{risk['cvar95']:.2f}%", "cvar95", info))
        r11.metric("Win Rate",    with_avg(f"{risk['win']:.1f}%", "win", info))
        r12.metric("R² vs SPY",   with_avg(f"{risk['r2']:.3f}", "r2", info))
        r13.metric("Tracking Err",with_avg(f"{risk['te']:.2f}%", "te", info))
        r14.metric("Info Ratio",  with_avg(f"{risk['ir']:.2f}", "ir", info))

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
        ebitda=info.get("ebitda") or 0; intexp=info.get("interestExpense") or 0
        h7.metric("Int. Coverage", f"{ebitda/max(intexp,1):.1f}x" if ebitda and intexp else "—")

        page_comment("Reading this page", ["<b>Sharpe ratio:</b> above 1 is generally good; above 2 is strong; below 0 means risk-adjusted return is poor over the selected period.", "<b>Beta:</b> above 1 moves more than SPY on average; below 1 is usually more defensive.", "<b>Max drawdown:</b> shows worst peak-to-trough loss; smaller drawdown is better for capital preservation.", "<b>VaR / CVaR:</b> estimate downside tail risk; CVaR is the average loss in the worst tail, so it is usually more conservative."])

    # ══════════ TAB 4 — INDUSTRY ══════════════════════════════════
    with tabs[3]:
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
        with st.spinner("Fetching peer data…"):
            peers=fetch_peers(peer_list,"1y")

        y1_self=(hist["Close"].iloc[-1]/hist["Close"].iloc[0]-1)*100 if len(hist)>1 else 0
        table_rows=[{"Ticker":f"★ {ticker}","Company":name[:28],"Price":f"${price:.2f}",
                     "P/E":f"{info.get('trailingPE',0):.1f}" if info.get("trailingPE") else "—",
                     "Fwd P/E":f"{info.get('forwardPE',0):.1f}" if info.get("forwardPE") else "—",
                     "Mkt Cap":fmtn(info.get("marketCap"),"$"),"1yr %":f"{y1_self:+.1f}%",
                     "Net Margin":fpct(info.get("profitMargins")),
                     "Rev Growth":fpct(info.get("revenueGrowth")),
                     "Div Yield":fpct(info.get("dividendYield")) if info.get("dividendYield") else "—",
                     "Beta":f"{risk['beta']:.2f}"}]
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
    with tabs[4]:
        tcfg1, tcfg2 = st.columns([1, 4])
        tech_chart_period = tcfg1.selectbox("Technical chart range", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "20y"], index=1, key="tech_chart_period")
        tcfg2.caption("Technical indicators and charts use their own range. Default is 3 months.")
        with st.spinner(f"Updating technical charts for {tech_chart_period}..."):
            tech_data, tech_err = fetch_stock(ticker, tech_chart_period)
            tech_hist_local = tech_data["hist"] if tech_data and not tech_err else hist
            tech_ta = calc_ta(tech_hist_local)
            tech_days = 99999

        last    = tech_ta.iloc[-1]
        rsi_v   = float(last.get("RSI",   50) or 50)
        adx_v   = float(last.get("ADX",    0) or 0)
        atr_v   = float(last.get("ATR",    0) or 0)
        macd_v  = float(last.get("MACD",   0) or 0)
        msig_v  = float(last.get("MACD_SIG",0) or 0)
        ma20_v  = float(last.get("MA20", price) or price)
        ma50_v  = float(last.get("MA50", price) or price)
        ma200_v = float(last.get("MA200",price) or price)
        stk_k   = float(last.get("STOCH_K",50) or 50)
        rvol    = float(last.get("RVOL20",  0) or 0)

        sigs=[]
        def s(e,t): sigs.append((e,t))
        if price>ma20_v:   s("🟢",f"Price above 20-Day MA (${ma20_v:.2f})")
        else:              s("🔴",f"Price below 20-Day MA (${ma20_v:.2f})")
        if price>ma50_v:   s("🟢",f"Price above 50-Day MA (${ma50_v:.2f})")
        else:              s("🔴",f"Price below 50-Day MA (${ma50_v:.2f})")
        if price>ma200_v:  s("🟢",f"Price above 200-Day MA (${ma200_v:.2f}) — long-term bullish")
        else:              s("🔴",f"Price below 200-Day MA (${ma200_v:.2f}) — long-term bearish")
        if ma50_v>ma200_v: s("🟢","Golden Cross: 50-Day MA > 200-Day MA")
        else:              s("🔴","Death Cross: 50-Day MA < 200-Day MA")
        if 30<rsi_v<70:    s("🟡",f"RSI {rsi_v:.1f} — neutral zone (30–70)")
        elif rsi_v>=70:    s("🔴",f"RSI {rsi_v:.1f} — overbought (above 70)")
        else:              s("🟢",f"RSI {rsi_v:.1f} — oversold (below 30), potential bounce")
        if macd_v>msig_v:  s("🟢","MACD line above signal line — bullish momentum")
        else:              s("🔴","MACD line below signal line — bearish momentum")
        if adx_v>25:       s("🟡",f"ADX {adx_v:.1f} — strong trend present (>25)")
        else:              s("🟡",f"ADX {adx_v:.1f} — weak / ranging market (<25)")
        if stk_k<20:       s("🟢",f"Stochastic %K {stk_k:.1f} — oversold (below 20)")
        elif stk_k>80:     s("🔴",f"Stochastic %K {stk_k:.1f} — overbought (above 80)")
        else:              s("🟡",f"Stochastic %K {stk_k:.1f} — neutral")

        score=sum(1 for e,_ in sigs if e=="🟢")/len(sigs)*100
        vt=("Strongly Bullish" if score>=80 else "Bullish" if score>=60
            else "Neutral" if score>=40 else "Bearish" if score>=20 else "Strongly Bearish")
        vc=GREEN if score>=60 else RED if score<40 else AMBER

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
                mav=float(raw); dp2=(price/mav-1)*100; clr=GREEN if dp2>0 else RED
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
            diff=(price/sv-1)*100
            src[i].markdown(f"""
            <div style="background:#13161e;border:1px solid rgba(239,68,68,0.25);
                        border-radius:9px;padding:12px;text-align:center">
              <div style="font-size:10px;color:{RED};margin-bottom:4px">SUPPORT {i+1}</div>
              <div style="font-size:14px;font-weight:600;font-family:monospace;color:#e2e8f0">
                ${sv:.2f}</div>
              <div style="font-size:11px;color:{RED};margin-top:2px">{diff:+.1f}% from price</div>
            </div>""", unsafe_allow_html=True)
        for i,rv in enumerate(resistances[:3]):
            diff=(price/rv-1)*100
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

        page_comment("Reading this page", ["<b>RSI:</b> above 70 is often overbought; below 30 is often oversold, but strong trends can stay extreme.", "<b>MACD:</b> MACD above signal is bullish momentum; crossing below signal is weakening momentum.", "<b>ADX:</b> above 25 suggests a stronger trend; ADX does not tell direction, only trend strength.", "<b>ATR / volatility:</b> higher means wider expected price swings and usually requires smaller position size."])

    # ══════════ TAB 6 — COMPARISON ═══════════════════════════════
    with tabs[5]:
        shead("Two-Stock Direct Comparison")
        cta, ctb, ctc = st.columns([2,2,1])
        comp1 = cta.text_input("First ticker", value=ticker, key="comp_ticker_1").upper().strip()
        comp2 = ctb.text_input("Second ticker", value="MSFT" if ticker != "MSFT" else "AAPL", key="comp_ticker_2").upper().strip()
        comp_period = ctc.selectbox("Compare period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1, key="comp_period")

        if comp1 and comp2:
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
                st.markdown(f'<div style="font-size:14px;color:#94a3b8;line-height:1.8">{translate_text_optional(comparison_paragraph(comp1, i1, rsk1, ta1, comp2, i2, rsk2, ta2), lang_code()) if lang_code()=="zh" else comparison_paragraph(comp1, i1, rsk1, ta1, comp2, i2, rsk2, ta2)}</div>', unsafe_allow_html=True)

        page_comment("Reading this page", ["<b>Direct comparison:</b> a better candidate usually has stronger trend, lower valuation risk, better profitability, and acceptable volatility.", "<b>Volatility:</b> the more volatile ticker may offer better trading opportunity but needs stricter risk control.", "<b>Ratios:</b> compare against the firm’s industry average, not only against the second ticker."])

    # ══════════ TAB 7 — NEWS ═══════════════════════════════════════
    with tabs[6]:
        shead("Latest Stock / Company News")
        ncol1, ncol2, ncol3 = st.columns([2, 2, 1])
        news_keyword = ncol1.text_input(tr("Search news by keyword"), value="", placeholder="earnings, AI, guidance, lawsuit...", key="news_keyword")
        news_order = ncol2.selectbox(tr("Order news by"), [tr("Importance first"), tr("Newest first")], index=0, key="news_order")
        if "news_refresh_token" not in st.session_state:
            st.session_state.news_refresh_token = 0
        if ncol3.button("⟳ " + tr("Update News"), use_container_width=True):
            st.session_state.news_refresh_token = int(time.time())
            fetch_news_items.clear()

        st.caption(tr("Priority: Yahoo Finance/yfinance first, then WSJ/RSS and broad financial news. Duplicate/overlapping headlines are filtered."))
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

    # ══════════ TAB 9 — MARKET RANKINGS ═══════════════════════════
    with tabs[8]:
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
                table_df["Yahoo Link"] = table_df["Ticker"].apply(lambda x: f"https://finance.yahoo.com/quote/{x}")
                st.dataframe(
                    table_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Yahoo Link": st.column_config.LinkColumn("Yahoo", display_text="Open")},
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

                page_comment("Reading this page", ["<b>% change:</b> best for ranking short-term market movers across tickers.", "<b>20D volatility:</b> high volatility means larger daily swings; combine it with volume ratio before trading.", "<b>Dollar volume:</b> higher liquidity usually means tighter spreads and easier execution.", "<b>Composite score:</b> blends move size, momentum, volume, volatility, and liquidity for trader-focused screening."])

    # ══════════ TAB 11 — GLOBAL INDEXES ═════════════════════════════
    with tabs[10]:
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
    with tabs[9]:
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

    # ══════════ TAB 8 — AI THESIS ═════════════════════════════════
    with tabs[7]:
        shead("Built-in AI Investment Thesis")
        st.markdown("""
        <div style="font-size:12px;color:#64748b;margin-bottom:12px">
          This thesis is generated from the dashboard's own valuation, quality, growth,
          momentum, and risk metrics. No Anthropic API key is needed.
        </div>""", unsafe_allow_html=True)

        cache_key=f"ai_{ticker}_{period}_{len(hist_ta)}"
        if st.button("⚡  Generate AI Thesis",type="primary") or cache_key in st.session_state:
            if cache_key not in st.session_state:
                ai=built_in_ai_thesis(ticker,info,risk,hist_ta)
                st.session_state[cache_key]=ai

            ai=st.session_state.get(cache_key,{})
            if not ai:
                st.error("AI thesis returned empty — try again.")
                return

            rec=ai.get("recommendation","—")
            rc=GREEN if rec=="Buy" else RED if rec=="Sell" else AMBER

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
