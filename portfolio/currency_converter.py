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

    # --- Extract base & quote currency ---
    base_currency = getattr(symbol_info, "currency_base", None)
    quote_currency = getattr(symbol_info, "currency_profit", None)

    if not base_currency or not quote_currency:
        logging.warning("Missing currency info for %s, returning original", symbol_name)
        return original

    base_currency = base_currency.upper()
    quote_currency = quote_currency.upper()

    # --- FX pair handling ---
    # Case 1: quote currency is USD (XXXUSD) -> already USD/unit -> leave as-is
    if quote_currency == "USD":
        return original

    # Case 2: base currency is USD (USDXXX) -> invert to get USD/unit
    if base_currency == "USD":
        try:
            usd_price = 1.0 / original.replace(0, float("nan"))
        except Exception:
            logging.exception("Failed to invert FX %s", symbol_name)
            return original
        return usd_price.dropna().rename(symbol_name)

    # --- Non-FX instruments: convert quote currency -> USD ---
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

    # Convert to USD
    try:
        usd_price = df["asset"] / df["fx"] if invert else df["asset"] * df["fx"]
    except Exception:
        logging.exception("Error converting %s using FX %s", symbol_name, fx_symbol)
        return original

    return usd_price.dropna().rename(symbol_name)
