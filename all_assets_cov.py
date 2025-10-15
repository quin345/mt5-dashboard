"""
mt5_marketwatch_portfolio.py

Requirements:
    pip install MetaTrader5 pandas numpy scipy openpyxl

Notes:
    - MT5 terminal must be running and logged in.
    - Script uses daily bars (TIMEFRAME_D1) by default and a lookback in days.
    - Converts asset quotes into USD using available FX pairs on MT5 (tries <CURRENCY>USD or USD<CURRENCY> and inverts if needed).
    - Produces: returns dataframe, annualized covariance matrix, expected returns, and max-Sharpe weights.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.optimize import minimize
import math
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ---------- User params ----------
LOOKBACK_DAYS = 252         # lookback (trading days) used to compute returns
TIMEFRAME = mt5.TIMEFRAME_H4
RISK_FREE_RATE_ANNUAL = 0.02   # annual risk-free rate (decimal). Change if desired.
ALLOW_SHORTS = False           # set True to allow negative weights
OUTPUT_XLSX = "mt5_portfolio_output.xlsx"
# ----------------------------------

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize() failed, error code = {mt5.last_error()}")
    logging.info("MT5 initialized.")

def shutdown_mt5():
    mt5.shutdown()
    logging.info("MT5 shutdown.")

def get_marketwatch_symbols():
    """
    Return list of symbol names visible in Market Watch.
    We fetch all symbols and filter those with symbol_info.visible == True.
    """
    all_symbols = mt5.symbols_get()
    symbols = []
    for s in all_symbols:
        info = mt5.symbol_info(s.name)
        # Some builds expose .visible attribute -> True if in Market Watch
        visible = getattr(info, "visible", None)
        if visible is None:
            # fallback heuristic: check if symbol is selectable (has tick)
            tick = mt5.symbol_info_tick(s.name)
            if tick is not None:
                symbols.append(s.name)
        else:
            if visible:
                symbols.append(s.name)
    logging.info("Found %d symbols in Market Watch (or selectable list).", len(symbols))
    return sorted(list(set(symbols)))

def fetch_closes(symbol, bars):
    """
    Fetch 'bars' daily close prices for symbol. Returns DataFrame with time index.
    """
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df['close']

def find_fx_rate_for_currency(currency, cached_symbols):
    """
    Find a symbol that converts 'currency' -> USD.
    Strategy:
      1) Try f"{currency}USD" (direct)
      2) Try f"USD{currency}" (inverse)
      3) Try other common prefixes/suffixes among cached_symbols
    Returns tuple (fx_symbol, invert_flag) or (None, None)
    """
    # direct
    cand_direct = f"{currency}USD"
    cand_inverse = f"USD{currency}"
    if cand_direct in cached_symbols:
        return cand_direct, False
    if cand_inverse in cached_symbols:
        return cand_inverse, True
    # try searching cached_symbols heuristically (e.g., EURUSD.r -> actual symbol may have suffix)
    # We'll attempt to find symbol that startswith currency and contains 'USD'
    for s in cached_symbols:
        if s.upper().startswith(currency.upper()) and 'USD' in s.upper():
            return s, False
    for s in cached_symbols:
        if s.upper().startswith('USD') and currency.upper() in s.upper():
            return s, True
    return None, None

def convert_series_to_usd(symbol_close, symbol_name, symbol_info, cached_symbols, bars=LOOKBACK_DAYS):
    """
    symbol_close: pandas Series of closes for the asset as quoted (in its quote currency)
    symbol_info: mt5.symbol_info(symbol_name) object (if available)
    Returns pandas Series of USD-denominated closes (aligned by date)
    """
    # Attempt to determine quote currency from symbol_info
    base = getattr(symbol_info, "currency_base", None)
    profit_currency = getattr(symbol_info, "currency_profit", None)
    quote_currency = None
    # For many non-forex instruments, currency_base indicates the asset currency (e.g., JPY for JP225)
    # Use currency_base first
    if base:
        quote_currency = base.upper()
    elif profit_currency:
        quote_currency = profit_currency.upper()

    if quote_currency is None:
        # fallback: try to infer from symbol name (not reliable)
        # e.g., symbols like "US500" -> USD, "JP225" -> JPY
        if any(symbol_name.upper().startswith(prefix) for prefix in ("USD", "US")):
            quote_currency = "USD"
        else:
            # unknown: return None to indicate we couldn't convert
            logging.warning("Could not determine currency for %s (no currency_base/profit).", symbol_name)
            return None

    if quote_currency == "USD":
        return symbol_close.rename(symbol_name)

    fx_symbol, invert = find_fx_rate_for_currency(quote_currency, cached_symbols)
    if fx_symbol is None:
        logging.warning("No FX pair found to convert %s (currency %s) to USD for symbol %s.", symbol_name, quote_currency, symbol_name)
        return None

    # Fetch fx closes
    fx_closes = fetch_closes(fx_symbol, bars)
    if fx_closes is None:
        logging.warning("No price history for FX symbol %s.", fx_symbol)
        return None

    # Align indices by date; both are indexed by timestamps
    df = pd.concat([symbol_close, fx_closes], axis=1, join='inner')
    df.columns = ['asset', 'fx']
    if df.empty or df['fx'].isnull().all():
        logging.warning("After aligning, no overlapping price data for %s and %s.", symbol_name, fx_symbol)
        return None

    # Convert: if fx is direct (CURUSD) then USD_price = asset * fx
    # if fx is inverse (USDcur) then USD_price = asset / fx
    if invert:
        usd_price = df['asset'] / df['fx']
    else:
        usd_price = df['asset'] * df['fx']
    usd_price = usd_price.dropna().rename(symbol_name)
    logging.info("Converted %s denominated in %s to USD using %s (invert=%s).", symbol_name, quote_currency, fx_symbol, invert)
    return usd_price

def build_usd_price_panel(symbols, bars=LOOKBACK_DAYS):
    """
    For each symbol in symbols, fetch close series and convert to USD.
    Returns DataFrame: rows = dates, cols = symbols (USD closes)
    """
    cached_symbols = symbols  # use market watch set for fx lookup (could expand to all symbols)
    usd_series_list = {}
    for symbol in symbols:
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logging.debug("symbol_info returned None for %s", symbol)
                continue
            close_ser = fetch_closes(symbol, bars)
            if close_ser is None or len(close_ser) < 20:
                logging.debug("Insufficient history for %s; skipping.", symbol)
                continue
            # For pure forex pairs already quoted in USD (e.g., EURUSD), the base currency is typically the first
            # But our convert function checks currency_base
            usd_ser = convert_series_to_usd(close_ser, symbol, info, cached_symbols, bars=bars)
            if usd_ser is not None and len(usd_ser) >= 10:
                usd_series_list[symbol] = usd_ser
        except Exception as e:
            logging.exception("Error handling symbol %s: %s", symbol, e)
            continue

    if not usd_series_list:
        raise RuntimeError("No USD-converted series obtained. Check that MT5 has FX pairs and Market Watch symbols.")
    # Align all series by inner join on date
    panel = pd.concat(usd_series_list.values(), axis=1, join='inner')
    panel.columns = list(usd_series_list.keys())
    logging.info("Built USD price panel with shape %s", panel.shape)
    return panel.sort_index()

def compute_returns_and_stats(price_panel, freq_per_year=252):
    """
    price_panel: DataFrame of USD closes (dates x symbols)
    Returns:
      - returns_df: daily log returns
      - mu_annual: expected annual returns (arithmetic) (series)
      - cov_annual: annualized covariance matrix
    """
    # Use log returns to be robust
    ret = np.log(price_panel).diff().dropna()
    # daily mean and cov
    mu_daily = ret.mean(axis=0)
    cov_daily = ret.cov()
    mu_annual = mu_daily * freq_per_year
    cov_annual = cov_daily * freq_per_year
    return ret, mu_annual, cov_annual

def max_sharpe_portfolio(mu, cov, risk_free=RISK_FREE_RATE_ANNUAL):
    """
    Solve for LONG-ONLY weights that maximize Sharpe ratio:
        maximize (w^T mu - rf) / sqrt(w^T cov w)
    subject to:
        sum(w) = 1
        w_i >= 0

    Returns:
        weights (pd.Series), portfolio_return, portfolio_vol, sharpe_ratio
    """
    # Preserve index for output
    if isinstance(mu, pd.Series):
        idx = mu.index
    elif isinstance(cov, pd.DataFrame):
        idx = cov.index
    else:
        n_guess = len(mu) if hasattr(mu, "__len__") else cov.shape[0]
        idx = [f"asset_{i}" for i in range(n_guess)]

    mu_arr = np.asarray(mu, dtype=float)
    cov_arr = np.asarray(cov, dtype=float)
    n = len(mu_arr)
    rf = risk_free

    # Objective: minimize negative Sharpe ratio
    def neg_sharpe(w):
        port_ret = np.dot(w, mu_arr)
        port_vol = np.sqrt(max(1e-12, np.dot(w, np.dot(cov_arr, w))))
        sharpe = (port_ret - rf) / port_vol
        return -sharpe

    # Constraints: fully invested (sum w = 1)
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1},)
    # Bounds: long-only
    bounds = tuple((0.0, 1.0) for _ in range(n))
    # Initial guess: equal weights
    x0 = np.ones(n) / n

    # Optimize
    opt = minimize(
        neg_sharpe, x0=x0, bounds=bounds, constraints=constraints,
        method='SLSQP', options={'ftol': 1e-4, 'maxiter': 1000}
    )

    if not opt.success:
        logging.warning("Optimization did not fully converge: %s", opt.message)

    w = opt.x
    port_ret = float(np.dot(w, mu_arr))
    port_vol = float(np.sqrt(np.dot(w, np.dot(cov_arr, w))))
    sharpe = (port_ret - rf) / port_vol

    weights_series = pd.Series(w, index=idx)
    return weights_series, port_ret, port_vol, sharpe


    # constraints: sum(weights)=1
    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},)
    # bounds
    if allow_shorts:
        bnds = [(-1.0, 1.0) for _ in range(n)]
    else:
        bnds = [(0.0, 1.0) for _ in range(n)]
    # start: equal weights (safe fallback if n>0)
    x0 = np.repeat(1.0 / n, n)

    opt = minimize(neg_sharpe, x0=x0, bounds=bnds, constraints=cons, method='SLSQP',
                   options={'ftol':1e-10, 'maxiter':500})
    if not opt.success:
        logging.warning("Optimization did not converge: %s", opt.message)
    w = opt.x

    # compute final metrics using numpy
    port_ret = float(w.dot(mu_arr))
    port_vol = float(math.sqrt(max(1e-12, w.dot(cov_arr).dot(w))))
    sharpe = (port_ret - rf) / port_vol

    # return weights as a pandas Series with preserved index
    weights_series = pd.Series(w, index=idx)
    return weights_series, port_ret, port_vol, sharpe


def main():
    try:
        init_mt5()
        symbols = get_marketwatch_symbols()
        if len(symbols) == 0:
            raise RuntimeError("No market watch symbols found.")
        logging.info("Using %d symbols from Market Watch.", len(symbols))

        price_panel = build_usd_price_panel(symbols, bars=LOOKBACK_DAYS)
        # drop columns with too many NaNs or tiny history
        price_panel = price_panel.dropna(axis=1, how='any')  # keep strict inner join
        if price_panel.shape[1] < 2:
            raise RuntimeError("Not enough assets after USD conversion and alignment.")

        ret_df, mu_annual, cov_annual = compute_returns_and_stats(price_panel)
        # convert mu_annual and cov_annual to pandas Series/DataFrame with asset names
        mu_annual = pd.Series(mu_annual, index=ret_df.columns)
        cov_annual = pd.DataFrame(cov_annual, index=ret_df.columns, columns=ret_df.columns)

        # Solve for max Sharpe
        weights, p_ret, p_vol, p_sharpe = max_sharpe_portfolio(mu_annual, cov_annual, risk_free=RISK_FREE_RATE_ANNUAL)
     
      

        # Results
        result_table = pd.DataFrame({
            'weight': weights,
            'mu_annual': mu_annual,
        })
        result_table['contribution_ret'] = result_table['weight'] * result_table['mu_annual']

        # Log summary
        logging.info("Max-Sharpe portfolio (Sharpe=%.4f): return=%.4f, vol=%.4f", p_sharpe, p_ret, p_vol)
        logging.info("\nTop allocations:")
        logging.info(result_table.sort_values('weight', ascending=False).head(20).to_string())

        # Save outputs
        with pd.ExcelWriter(OUTPUT_XLSX) as writer:
            price_panel.to_excel(writer, sheet_name='USD_Prices')
            ret_df.to_excel(writer, sheet_name='Log_Returns')
            mu_annual.to_frame('mu_annual').to_excel(writer, sheet_name='Mu_Annual')
            cov_annual.to_excel(writer, sheet_name='Cov_Annual')
            result_table.to_excel(writer, sheet_name='MaxSharpe_Portfolio')
        logging.info("Results saved to %s", OUTPUT_XLSX)

        # Print final concise results
        print("\n=== Max-Sharpe Portfolio Summary ===")
        print(f"Sharpe ratio (annual) = {p_sharpe:.4f}")
        print(f"Expected annual return = {p_ret:.4%}")
        print(f"Expected annual vol    = {p_vol:.4%}\n")
        print(result_table.sort_values('weight', ascending=False).to_string())

    finally:
        shutdown_mt5()

if __name__ == "__main__":
    main()
