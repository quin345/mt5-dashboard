# 🧠 Active Portfolio Management Tool

A modular **portfolio management system** for **active investors and hedge fund managers**.
It integrates with multiple **brokerage and trading platforms** — including **Interactive Brokers (IBKR)**, **MetaTrader 5 (MT5)**, and **cTrader** — to provide unified access to account data, positions, and performance analytics.

This project serves as the foundation for **quantitative active portfolio management**, enabling seamless **data ingestion**, **risk monitoring**, and **multi-platform trade analysis**.

---

## 🚀 Features

* **Multi-broker integration**

  * Fetch open positions, account equity, and trade history from:

    * 🧩 Interactive Brokers (IBKR)
    * ⚙️ MetaTrader 5 (MT5)
    * 📊 cTrader (via API bridge)

* **Unified portfolio view**

  * Aggregate and normalize exposure across all brokers and asset classes
  * Consolidate PnL, margin, and risk metrics in one dashboard

* **Active portfolio management**

  * Dynamic risk and return analytics
  * Stop-loss and rebalancing logic at both **asset** and **portfolio** levels

* **Vectorized backtesting (planned)**

  * Test allocation and stop-loss logic on historical data in a high-speed, vectorized pipeline

* **Flexible data pipeline**

  * Modular API wrappers for brokers
  * Unified data schema for positions and orders

* **Extensible architecture**

  * Ready for future alpha models, Black-Litterman optimization, or machine learning layers

---

## 🧩 Architecture Overview

```
+--------------------------+
|   Broker APIs / Feeds    |
|  (IBKR, MT5, cTrader)    |
+------------+-------------+
             |
             v
+--------------------------+
|   Data Normalization     |
|   - Position schema      |
|   - Currency conversion  |
|   - Broker-specific fixes|
+------------+-------------+
             |
             v
+--------------------------+
|   Portfolio Engine       |
|   - Aggregation          |
|   - PnL attribution      |
|   - Risk metrics         |
+------------+-------------+
             |
             v
+--------------------------+
|   Strategy / Execution   |
|   - Active allocation    |
|   - Stop loss control    |
|   - Optimization layer   |
+--------------------------+
```

---

## ⚙️ Installation

```bash
git clone https://github.com/yourusername/active-portfolio-manager.git
cd active-portfolio-manager
pip install -r requirements.txt
```

**Requirements**

* Python 3.10+
* Access to at least one broker API (IBKR, MT5, or cTrader)
* Dependencies: `pandas`, `numpy`, `requests`, `plotly`, `sqlalchemy`

---

## 🔑 Broker Setup

### 1. Interactive Brokers (IBKR)

* Configure **IBKR TWS API** or **IB Gateway**
* Add credentials to `.env`:

  ```env
  IBKR_HOST=127.0.0.1
  IBKR_PORT=7497
  IBKR_CLIENT_ID=1
  ```

### 2. MetaTrader 5 (MT5)

* Install the MetaTrader5 Python package
* Log in to your trading account:

  ```python
  import MetaTrader5 as mt5
  mt5.initialize(login=1234567, password="xxxx", server="Broker-Server")
  ```

### 3. cTrader

* Use the **Open API** bridge for cTrader
* Add credentials to `.env`:

  ```env
  CTRADER_CLIENT_ID=your_client_id
  CTRADER_CLIENT_SECRET=your_client_secret
  CTRADER_ACCESS_TOKEN=your_access_token
  ```

---

## 📈 Example Usage

```python
from portfolio.core import PortfolioEngine
from connectors import IBKRConnector, MT5Connector, CTraderConnector

ibkr = IBKRConnector()
mt5 = MT5Connector()
ctrader = CTraderConnector()

# Fetch all positions
positions = ibkr.get_positions() + mt5.get_positions() + ctrader.get_positions()

# Aggregate portfolio
engine = PortfolioEngine(positions)
summary = engine.aggregate()

print(summary)
engine.plot_exposure()
```

---

## 🧮 Roadmap

| Milestone                                             | Status         |
| ----------------------------------------------------- | -------------- |
| Broker connectors (IBKR, MT5, cTrader)                | ✅ Done         |
| Portfolio aggregation                                 | ✅ Done         |
| PnL and exposure normalization                        | ✅ Done         |
| Risk dashboard (VaR, beta, volatility)                | 🔄 In Progress |
| Vectorized backtesting engine                         | 🔜 Planned     |
| Optimization module (Black-Litterman / Treynor-Black) | 🔜 Planned     |

---

## 🧱 Folder Structure

```
active-portfolio-manager/
│
├── connectors/
│   ├── ibkr_connector.py
│   ├── mt5_connector.py
│   ├── ctrader_connector.py
│
├── portfolio/
│   ├── core.py
│   ├── risk.py
│   ├── optimization.py
│
├── utils/
│   ├── config_loader.py
│   ├── currency_tools.py
│
├── notebooks/
│   ├── demo_analysis.ipynb
│
├── requirements.txt
└── README.md
```

---

## 🔒 Disclaimer

This project is for **educational and research purposes only**.
It **does not constitute financial advice**, and is not a solicitation to invest or trade.
Use at your own risk and comply with your broker’s API terms and local regulations.

---

## 🧬 License

MIT License © 2025 [Your Name or Fund Name]

---

## 🤝 Contributing

Pull requests are welcome!
For major changes, please open an issue first to discuss your ideas.

---

## 🌐 Contact

For collaboration or fund integration inquiries:
📧 **[contact@yourfundname.com](mailto:contact@yourfundname.com)**

