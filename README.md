```markdown

\# 🧠 Active Portfolio Management Tool



A modular \*\*portfolio management system\*\* designed for \*\*active investors and hedge fund managers\*\*.  

It integrates with multiple \*\*brokerage and trading platforms\*\* — including \*\*Interactive Brokers (IBKR)\*\*, \*\*MetaTrader 5 (MT5)\*\*, and \*\*cTrader\*\* — to provide unified access to account data, positions, and performance analytics.



This project serves as the foundation for \*\*quantitative active portfolio management\*\*, enabling seamless \*\*data ingestion\*\*, \*\*risk monitoring\*\*, and \*\*multi-platform trade analysis\*\*.



---



\## 🚀 Features



\- \*\*Multi-broker integration\*\*

&nbsp; - Fetch open positions, account equity, and trade history from:

&nbsp;   - 🧩 Interactive Brokers (IBKR)

&nbsp;   - ⚙️ MetaTrader 5 (MT5)

&nbsp;   - 📊 cTrader (via API bridge)

\- \*\*Unified portfolio view\*\*

&nbsp; - Aggregate and normalize exposure across all brokers and asset classes

&nbsp; - Consolidate PnL, margin, and risk metrics in one dashboard

\- \*\*Active portfolio management\*\*

&nbsp; - Dynamic risk and return analytics

&nbsp; - Stop-loss and rebalancing logic at both \*\*asset\*\* and \*\*portfolio\*\* level

\- \*\*Vectorized backtesting (planned)\*\*

&nbsp; - Test allocation and stop-loss logic on historical data in a vectorized, high-speed pipeline

\- \*\*Flexible data pipeline\*\*

&nbsp; - Modular API wrappers for brokers

&nbsp; - Unified data schema for positions and orders

\- \*\*Extensible architecture\*\*

&nbsp; - Designed for integration with future alpha models, Black-Litterman optimization, or machine-learning layers



---



\## 🧩 Architecture Overview



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



````



---



\## ⚙️ Installation



```bash

git clone https://github.com/yourusername/active-portfolio-manager.git

cd active-portfolio-manager

pip install -r requirements.txt

````



\*\*Requirements\*\*



\* Python 3.10+

\* Access to at least one broker API (IBKR, MT5, or cTrader)

\* Pandas, NumPy, Requests, Plotly, and SQLAlchemy



---



\## 🔑 Broker Setup



\### 1. Interactive Brokers (IBKR)



\* Configure \*\*IBKR TWS API\*\* or \*\*IB Gateway\*\*

\* Update credentials in `.env`:



&nbsp; ```env

&nbsp; IBKR\_HOST=127.0.0.1

&nbsp; IBKR\_PORT=7497

&nbsp; IBKR\_CLIENT\_ID=1

&nbsp; ```



\### 2. MetaTrader 5 (MT5)



\* Install MetaTrader5 Python package

\* Login to your trading account using:



&nbsp; ```python

&nbsp; import MetaTrader5 as mt5

&nbsp; mt5.initialize(login=1234567, password="xxxx", server="Broker-Server")

&nbsp; ```



\### 3. cTrader



\* Use the \*\*Open API\*\* bridge for cTrader

\* Add API credentials to `.env`:



&nbsp; ```env

&nbsp; CTRADER\_CLIENT\_ID=your\_client\_id

&nbsp; CTRADER\_CLIENT\_SECRET=your\_client\_secret

&nbsp; CTRADER\_ACCESS\_TOKEN=your\_access\_token

&nbsp; ```



---



\## 📈 Example Usage



```python

from portfolio.core import PortfolioEngine

from connectors import IBKRConnector, MT5Connector, CTraderConnector



ibkr = IBKRConnector()

mt5 = MT5Connector()

ctrader = CTraderConnector()



\# Fetch all positions

positions = ibkr.get\_positions() + mt5.get\_positions() + ctrader.get\_positions()



\# Aggregate portfolio

engine = PortfolioEngine(positions)

summary = engine.aggregate()



print(summary)

engine.plot\_exposure()

```



---



\## 🧮 Roadmap



| Milestone                                             | Status         |

| ----------------------------------------------------- | -------------- |

| Broker connectors (IBKR, MT5, cTrader)                | ✅              |

| Portfolio aggregation                                 | ✅              |

| PnL and exposure normalization                        | ✅              |

| Risk dashboard (VaR, beta, volatility)                | 🔄 In Progress |

| Vectorized backtesting engine                         | 🔜 Planned     |

| Optimization module (Black-Litterman / Treynor-Black) | 🔜 Planned     |



---



\## 🧱 Folder Structure



```

active-portfolio-manager/

│

├── connectors/

│   ├── ibkr\_connector.py

│   ├── mt5\_connector.py

│   ├── ctrader\_connector.py

│

├── portfolio/

│   ├── core.py

│   ├── risk.py

│   ├── optimization.py

│

├── utils/

│   ├── config\_loader.py

│   ├── currency\_tools.py

│

├── notebooks/

│   ├── demo\_analysis.ipynb

│

├── requirements.txt

└── README.md

```



---



\## 🔒 Disclaimer



This project is for \*\*educational and research purposes only\*\*.

It does \*\*not constitute financial advice\*\*, and is not a solicitation to invest or trade.

Use at your own risk. Always comply with your broker’s API terms and financial regulations.



---



\## 🧬 License



MIT License © 2025 \[Your Name or Fund Name]



---



\## 🤝 Contributing



Pull requests are welcome!

If you plan major changes, please open an issue first to discuss what you’d like to modify or add.



---



\## 🌐 Contact



For collaboration or fund integration inquiries:

📧 \*\*\[contact@yourfundname.com](mailto:contact@yourfundname.com)\*\*



```



---



Would you like me to make it \*\*leaner and investor-facing\*\* (for a private GitHub repo you’ll show to potential LPs),  

or \*\*developer-oriented\*\* (for open-source collaboration)?

```



