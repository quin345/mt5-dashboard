"""
main.py
-------
Master script for MT5 Portfolio Optimizer.
"""
import MetaTrader5 as mt5
import logging
import pandas as pd
from .config import *
from .mt5_connector import init_mt5, shutdown_mt5, get_marketwatch_symbols
from .data_fetcher import fetch_closes
from .currency_converter import convert_series_to_usd
from .portfolio_math import compute_returns_and_stats
from .optimizer import max_sharpe_portfolio
from .io_utils import save_results

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s %(levelname)s %(message)s")

def main():
    try:
        init_mt5()
        symbols = get_marketwatch_symbols()
        usd_panel = {}

        for sym in symbols:
            data = fetch_closes(sym, LOOKBACK_DAYS, TIMEFRAME)
            if data is not None:
                info = mt5.symbol_info(sym)
                usd_series = convert_series_to_usd(data, sym, info, symbols, LOOKBACK_DAYS, TIMEFRAME)
                if usd_series is not None:
                    usd_panel[sym] = usd_series

        price_panel = pd.concat(usd_panel.values(), axis=1, join='inner')
        returns, mu, cov = compute_returns_and_stats(price_panel)
        weights, p_ret, p_vol, sharpe = max_sharpe_portfolio(mu, cov, RISK_FREE_RATE_ANNUAL, ALLOW_SHORTS)

        results = pd.DataFrame({'weight': weights, 'mu_annual': mu})
        results['contribution_ret'] = results['weight'] * results['mu_annual']

        logging.info("Sharpe: %.4f  Return: %.4f  Vol: %.4f", sharpe, p_ret, p_vol)
        save_results(OUTPUT_XLSX, price_panel, returns, mu, cov, results)
        print("\n=== Max-Sharpe Portfolio ===\n", results.sort_values('weight', ascending=False))

    finally:
        shutdown_mt5()

if __name__ == "__main__":
    main()
