"""
currency_converter.py
---------------------
Convert instrument price series into USD terms.

Rules implemented:
 - If instrument is truly USD-denominated (no FX needed) -> return as-is.
 - If instrument symbol starts with "USD" (e.g. USDJPY) -> invert (1 / price) to express USD per unit.
 - If instrument currency_profit != "USD" -> find appropriate FX (EURUSD or USDJPY) and convert.
 - If no FX available, return original series but log a warning.
"""

import logging
import pandas as pd
from .data_fetcher import fetch_closes


def find_fx_symbol_for_currency(currency, cached_symbols):
    """
    Find a usable FX symbol to convert `currency` -> USD.

    Returns (fx_symbol, invert_flag)
      - fx_symbol: string name of pair available on broker, or None
      - invert_flag: if True, use division (asset / fx) else multiplication (asset * fx)
    """
    if not currency:
        return None, None

    # Prefer direct pair like EURUSD (multiply)
    direct = f"{currency}USD"   # EURUSD -> multiply by fx to get USD
    inverse = f"USD{currency}"  # USDJPY -> invert (divide) to get USD

    if direct in cached_symbols:
        return direct, False
    if inverse in cached_symbols:
        return inverse, True
    return None, None


def is_fx_pair(symbol):
    """Quick heuristic: FX pairs are commonly 6-character codes like EURUSD, USDJPY, GBPUSD, etc."""
    if not symbol or len(symbol) < 6:
        return False
    # crude check: contains 'USD' or known pattern - keep it lightweight
    return "USD" in symbol


def convert_series_to_usd(symbol_close, symbol_name, symbol_info, cached_symbols, bars, timeframe):
    """
    Convert a Pandas Series `symbol_close` (indexed by datetime) into USD terms.

    Args:
      symbol_close: pd.Series (close prices for the instrument)
      symbol_name:  str, instrument name on MT5 (e.g. "JP225", "USDJPY", "AAPL")
      symbol_info:  object, MT5 symbol info (should have currency_profit attribute ideally)
      cached_symbols: set/list of symbol names available on the broker (for FX lookup)
      bars: int, number of bars to fetch when an FX is required
      timeframe: mt5 timeframe constant or string accepted by fetch_closes

    Returns:
      pd.Series (USD-valued prices) or the original series if conversion not possible
    """

    # Defensive renaming
    original = symbol_close.rename(symbol_name)

    # Attempt to read specified profit/currency attribute
    currency = getattr(symbol_info, "currency_profit", None)

    # Case A: instrument itself is an FX pair that starts with USD (e.g. "USDJPY")
    # We must invert it (1 / price) to get USD per unit of the quoted currency
    if is_fx_pair(symbol_name) and symbol_name.startswith("USD"):
        # If symbol is USDXXX and we want USD per instrument unit, invert.
        # Example: USDJPY = JPY per USD -> 1 / (JPY per USD) = USD per JPY
        # If you actually want USD per instrument unit (instrument unit is usually base currency),
        # this inversion matches the "1 / USDXXX" request.
        try:
            inverted = 1.0 / original.replace(0, float("nan"))  # avoid divide-by-zero
        except Exception:
            logging.exception("Failed to invert FX pair %s", symbol_name)
            return original
        return inverted.dropna().rename(symbol_name)

    # Case B: instrument currency is USD (but instrument name is NOT an FX starting with USD)
    # e.g., an index priced in USD or a USD-denominated instrument -> return as-is
    if currency == "USD":
        return original

    # Case C: instrument is priced in a foreign currency (indices, local stocks, etc.)
    # Find FX pair for that currency and convert.
    fx_symbol, invert = find_fx_symbol_for_currency(currency, cached_symbols)
    if not fx_symbol:
        logging.warning("No FX pair found to convert %s (currency=%s) to USD. Returning original.", symbol_name, currency)
        return original

    fx_closes = fetch_closes(fx_symbol, bars, timeframe)
    if fx_closes is None:
        logging.warning("FX data unavailable for %s while converting %s. Returning original.", fx_symbol, symbol_name)
        return original

    # Align on timestamps (inner join) to avoid misaligned arithmetic
    df = pd.concat([original, fx_closes.rename(fx_symbol)], axis=1, join="inner")
    if df.shape[0] == 0:
        logging.warning("No overlapping timestamps for %s and %s. Returning original.", symbol_name, fx_symbol)
        return original

    df.columns = ["asset", "fx"]

    # If fx is USD<currency> (invert=True), we must divide asset by fx to get USD
    # Example: currency = JPY, fx_symbol = USDJPY (invert=True). For asset priced in JPY:
    #    USD_value = asset (JPY) / (USDJPY (JPY per USD)) = USD
    # Else (direct e.g. EURUSD), multiply:
    try:
        usd_price = df["asset"] / df["fx"] if invert else df["asset"] * df["fx"]
    except Exception:
        logging.exception("Error while converting %s using FX %s", symbol_name, fx_symbol)
        return original

    return usd_price.dropna().rename(symbol_name)
