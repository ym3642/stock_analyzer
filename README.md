# 📈 SmartStock — Premium Trading Terminal

A professional-grade stock analysis web app built with Python and Streamlit. Analyze any stock with real-time data, AI-powered investment thesis, famous investor simulations, backtesting, and global market coverage.

🌐 **Live at: [smartstock.trading](https://smartstock.trading)**

---

## Features

### 📊 Company Analysis
- **Overview** — Live price chart (Webull-style candlesticks), key metrics, 52-week range, volume, dividends
- **Valuation** — P/E, Forward P/E, P/S, PEG, EV/EBITDA, interactive DCF fair value calculator, analyst price targets, financial statements
- **Risk** — Sharpe ratio, Sortino, Calmar, Max Drawdown, VaR/CVaR, Beta vs S&P 500, rolling risk metrics
- **Industry** — Sector comparison, peer benchmarking, industry averages
- **Technical** — RSI, MACD, Bollinger Bands, moving averages, volume analysis
- **Comparison** — Side-by-side comparison of any two stocks across 30+ metrics
- **Company News** — Latest news with sentiment tagging

### 🤖 AI & Investor Intelligence
- **AI Thesis** — Rule-based AI investment thesis with bull/bear case, factor scores, ESG assessment, catalysts and risks
- **Investor View** — Simulate portfolios of famous investors (Buffett, Dalio, Lynch, Ackman, and more) with:
  - Live factor scoring (Quality, Value, Growth, Momentum, Stability)
  - Market regime detection (VIX, SPY/QQQ/IWM breadth)
  - News shock overlay
  - Full backtest engine with SPY benchmark comparison
  - Monthly returns heatmap, rolling Sharpe, return distribution
  - Alpha, Beta, R², Treynor, Omega Ratio, Ulcer Index, and more

### 🌐 Market & Global
- **Market News** — Global market headlines with sentiment and impact analysis
- **Market Rankings** — Top movers screener with AI scoring across global markets
- **Global Indexes** — World market overview across all continents
- **Commodities** — Oil, gold, silver, natural gas, and more

### 🔧 Tools
- **Bond Calculator** — Yield to maturity, duration, convexity, cashflow table
- **Option Calculator** — Black-Scholes pricing with full Greeks (Delta, Gamma, Theta, Vega, Rho)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Charts | Plotly |
| Data | Yahoo Finance (yfinance) |
| Technical Analysis | pandas-ta |
| Hosting | Render |
| Domain | Cloudflare |
| Language | Python 3.11+ |

---

## Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/ym3642/stock_analyzer.git
cd stock_analyzer
```

**2. Create a virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the app**
```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## Deployment

The app is deployed on **Render** with automatic deploys from this GitHub repo.

Every `git push` to `main` triggers a redeploy automatically:

```
Local code  →  git push  →  GitHub  →  Render auto-deploy  →  smartstock.trading
```

---

## Project Structure

```
stock_analyzer/
├── app.py              # Main application (all-in-one)
├── Procfile            # Render/Railway start command
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Disclaimer

SmartStock is for **educational and informational purposes only**. Nothing on this platform constitutes financial advice. Always conduct your own due diligence and consult a qualified financial advisor before making investment decisions. Data is sourced from Yahoo Finance and may be delayed or inaccurate.

---

## License

MIT 