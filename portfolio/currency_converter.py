"""
currency_converter.py
---------------------
Convert instrument price series to USD based on quote currency.

Rules:
 - Detect quote currency (for FX, usually second currency in pair).
 - If quote currency is USD, return series as-is.
 - Otherwise, fetch FX and convert to USD.
 - Works for stocks, indices, FX pairs, commodities.
"""

import logging
import pandas as pd
from .data_fetcher import fetch_closes


def find_fx_symbol_for_quote_currency(quote_currency, cached_symbols):
    """
    Find FX pair to convert quote_currency -> USD.

    Returns:
      fx_symbol: broker symbol or None
      invert_flag: True if USD<currency> (divide), False if currencyUSD (multiply)
    """
    if not quote_currency or quote_currency.upper() == "USD":
        return None, None

    quote_currency = quote_currency.upper()
    direct = f"{quote_currency}USD"  # multiply
    inverse = f"USD{quote_currency}"  # divide

    if direct in cached_symbols:
        return direct, False
    if inverse in cached_symbols:
        return inverse, True
    return None, None

def convert_series_to_usd(symbol_close, symbol_name, symbol_info, cached_symbols, bars, timeframe):
    original = symbol_close.rename(symbol_name)

    # Determine quote currency
    quote_currency = getattr(symbol_info, "currency_profit", None)
    base_currency = getattr(symbol_info, "currency_base", None)

    if quote_currency is None or base_currency is None:
        logging.warning("Symbol info missing currencies for %s. Returning original.", symbol_name)
        return original

    quote_currency = quote_currency.upper()
    base_currency = base_currency.upper()

    # If quote currency is USD, just multiply by 1
    if quote_currency == "USD":
        return original

    # If base currency is USD (USDXXX), invert FX
    if base_currency == "USD":
        fx_symbol = symbol_name
        invert = True
        fx_closes = original  # use own series for inversion
        try:
            usd_price = 1.0 / fx_closes.replace(0, float("nan"))
        except Exception:
            logging.exception("Failed to invert FX %s", symbol_name)
            return original
        return usd_price.dropna().rename(symbol_name)

    # Else: convert quote currency -> USD using FX
    fx_symbol, invert = find_fx_symbol_for_quote_currency(quote_currency, cached_symbols)
    if not fx_symbol:
        logging.warning(
            "No FX pair found to convert %s (quote_currency=%s) to USD. Returning original.",
            symbol_name,
            quote_currency,
        )
        return original

    fx_closes = fetch_closes(fx_symbol, bars, timeframe)
    if fx_closes is None:
        logging.warning(
            "FX data unavailable for %s while converting %s. Returning original.",
            fx_symbol,
            symbol_name,
        )
        return original

    # Align timestamps
    df = pd.concat([original, fx_closes.rename(fx_symbol)], axis=1, join="inner")
    if df.shape[0] == 0:
        logging.warning(
            "No overlapping timestamps for %s and %s. Returning original.",
            symbol_name,
            fx_symbol,
        )
        return original

    df.columns = ["asset", "fx"]

    try:
        usd_price = df["asset"] / df["fx"] if invert else df["asset"] * df["fx"]
    except Exception:
        logging.exception("Error converting %s using FX %s", symbol_name, fx_symbol)
        return original

    return usd_price.dropna().rename(symbol_name)
