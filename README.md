# 📈 Stock Analyzer Pro — Python Edition

Full-featured stock analysis dashboard built with Streamlit, yfinance, and Claude AI.

---

## Features

| Tab | What you get |
|---|---|
| **Overview** | Candlestick chart, 24 fundamental metrics, business description |
| **Valuation** | P/E, P/S, EV/EBITDA, P/B, analyst consensus, interactive DCF calculator |
| **Risk & Volatility** | Beta, Sharpe, Sortino, Calmar, VaR, CVaR, drawdown chart, rolling Sharpe |
| **Industry & Peers** | Customizable peer comparison table, normalized 1yr performance chart |
| **Technical Analysis** | RSI, MACD, Stochastic, Bollinger Bands, OBV, ADX, ATR, support/resistance |
| **AI Analysis** | Claude-powered bull/bear thesis, factor scores, catalysts, ESG assessment |

---

## Setup (takes ~2 minutes)

### 1. Prerequisites
- Python 3.9 or higher
- Check: `python --version`

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# macOS / Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
streamlit run app.py
```

The browser opens automatically at `http://localhost:8501`

---

## AI Analysis (Optional)

The AI tab uses Claude (Anthropic). To enable it:

1. Get a free API key at https://console.anthropic.com
2. Paste the key into the **Anthropic API Key** field in the sidebar
3. Click **Generate AI Thesis**

You are NOT required to use AI — all other tabs work without an API key.

---

## Usage

1. Type any stock ticker in the sidebar (e.g. `AAPL`, `NVDA`, `BRK-B`)
2. Or click one of the quick-pick buttons
3. Select a data period and chart window
4. Toggle Moving Averages / Bollinger Bands overlays
5. Navigate tabs for different analysis views
6. In Industry & Peers, edit the peer tickers text box to compare any stocks

---

## Data Sources

- **Price & Fundamentals**: Yahoo Finance via `yfinance` (free, no API key needed)
- **Technical Indicators**: Calculated in real-time via `ta` library
- **AI Thesis**: Anthropic Claude API (optional, requires key)
- **Benchmark**: S&P 500 via SPY ETF

---

## Troubleshooting

**"Module not found"** — Make sure your virtual environment is activated and you ran `pip install -r requirements.txt`

**"Ticker not found"** — Double-check the symbol. International stocks use suffixes: `TSM` (Taiwan), `005930.KS` (Samsung), `BARC.L` (Barclays)

**Slow loading** — Data is cached for 5 minutes. First load per ticker takes ~3-5 seconds.

**AI tab not working** — Check that your API key starts with `sk-ant-` and has credits available.

---

## Disclaimer

This tool is for **educational and informational purposes only**.  
It does not constitute financial advice.  
Always do your own research before making investment decisions.
