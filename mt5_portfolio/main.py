"""
main.py
-------
Master script for MT5 Portfolio Optimizer.
"""
import logging
import pandas as pd
import MetaTrader5 as mt5

from .config import *
from .mt5_connector import init_mt5, shutdown_mt5, get_marketwatch_symbols
from .data_fetcher import fetch_closes
from .currency_converter import convert_series_to_usd
from .portfolio_math import compute_returns_and_stats
from .optimizer import max_sharpe_portfolio, plot_efficient_frontier
from .io_utils import save_results


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(message)s"
)


def main():
    try:
        init_mt5()
        symbols = get_marketwatch_symbols()
        cached_symbols = set(symbols)  # for fast FX lookup
        usd_panel = {}

        for sym in symbols:
            data = fetch_closes(sym, LOOKBACK_DAYS, TIMEFRAME)
            if data is None or data.empty:
                logging.warning("No price data for %s, skipping.", sym)
                continue

            info = mt5.symbol_info(sym)
            if info is None:
                logging.warning("No symbol info for %s, skipping.", sym)
                continue

            usd_series = convert_series_to_usd(
                symbol_close=data,
                symbol_name=sym,
                symbol_info=info,
                cached_symbols=cached_symbols,
                bars=LOOKBACK_DAYS,
                timeframe=TIMEFRAME
            )

            if usd_series is not None and not usd_series.empty:
                usd_panel[sym] = usd_series

        if not usd_panel:
            logging.error("No valid USD-converted data found. Exiting.")
            return

        # Align all series on common timestamps
        price_panel = pd.concat(usd_panel.values(), axis=1, join='inner')
        price_panel.columns = list(usd_panel.keys())

        returns, mu, cov = compute_returns_and_stats(price_panel)
        weights, p_ret, p_vol, sharpe = max_sharpe_portfolio(mu, cov, RISK_FREE_RATE_ANNUAL, ALLOW_SHORTS)

        results = pd.DataFrame({
            'weight': weights,
            'mu_annual': mu,
            'contribution_ret': weights * mu
        })

        logging.info("Sharpe: %.4f | Return: %.4f | Volatility: %.4f", sharpe, p_ret, p_vol)
        save_results(OUTPUT_XLSX, price_panel, returns, mu, cov, results)

        print("\n=== Max-Sharpe Portfolio ===\n")
        print(results.sort_values('weight', ascending=False))

        # --- Plot Efficient Frontier ---
        try:
            print("\n>>> Generating efficient frontier plot...")
            plot_efficient_frontier(mu, cov, RISK_FREE_RATE_ANNUAL, allow_shorts=ALLOW_SHORTS)
            print("✅ Efficient frontier plot saved as efficient_frontier.png")
        except Exception as e:
            logging.error("Failed to plot efficient frontier: %s", e)

    finally:
        shutdown_mt5()


if __name__ == "__main__":
    main()
