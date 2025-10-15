"""
config.py
----------
Central configuration file for MT5 Portfolio Optimizer.
Adjust parameters here instead of modifying main modules.
"""

LOOKBACK_DAYS = 1000
TIMEFRAME = "TIMEFRAME_H4"   # will be evaluated dynamically in mt5_connector
RISK_FREE_RATE_ANNUAL = 0.02
ALLOW_SHORTS = False
OUTPUT_XLSX = "mt5_portfolio_output.xlsx"
LOG_LEVEL = "INFO"
