import logging
import MetaTrader5 as mt5
import pandas as pd
from .data_fetcher import fetch_closes


def get_fx_series(pair, cached_symbols, bars, timeframe):
    """
    Ensure pair is in MarketWatch (cached_symbols is a set of symbol names).
    Then fetch closes via fetch_closes and return a pandas Series (or None).
    """
    # Ensure type: cached_symbols must be a set (not dict)
    if not isinstance(cached_symbols, set):
        logging.warning("cached_symbols is not a set; converting to set locally for safety.")
        cached_symbols = set(cached_symbols)

    # Try to ensure the symbol is available at broker/marketwatch
    if pair not in cached_symbols:
        added = mt5.symbol_select(pair, True)
        if added:
            cached_symbols.add(pair)
            logging.info(f"📈 Auto-added missing FX pair {pair} to MarketWatch.")
        else:
            logging.debug(f"FX pair {pair} not available in broker symbol list.")
            return None

    fx_data = fetch_closes(pair, bars, timeframe)
    if fx_data is None or (hasattr(fx_data, "empty") and fx_data.empty):
        logging.debug(f"No data returned for {pair}.")
        return None

    # Normalize to pandas Series of closes
    if isinstance(fx_data, pd.DataFrame):
        if "close" in fx_data.columns:
            fx_series = fx_data["close"]
        else:
            # fallback: single-column dataframe -> take first column
            fx_series = fx_data.iloc[:, 0]
    else:
        fx_series = fx_data

    return fx_series


def convert_series_to_usd(symbol_close, symbol_name, symbol_info, cached_symbols, bars, timeframe):
    """
    Convert any symbol (FX, index, commodity) into USD terms using MT5 contract info.

    - cached_symbols is expected to be a set of symbol names already added to MarketWatch.
    - This function will call get_fx_series(...) to fetch required FX rates.
    """
    base = getattr(symbol_info, "currency_base", None)
    quote = getattr(symbol_info, "currency_profit", None)
    path = getattr(symbol_info, "path", "") or ""
    sym_type = getattr(symbol_info, "type", None)  # note: MT5 uses .type in many bindings

    logging.info(f"Converting {symbol_name:<10} | Base={base} | Quote={quote} | Path={path} | Type={sym_type}")

    # Quick sanity for incoming series
    if symbol_close is None or (hasattr(symbol_close, "empty") and symbol_close.empty):
        logging.warning(f"No price data provided for {symbol_name}.")
        return None

    # 1) If already quoted in USD -> leave as is
    if quote == "USD":
        logging.debug(f"{symbol_name} already quoted in USD -> no conversion.")
        logging.debug(f"sample: {symbol_close.head()}")
        return symbol_close

    # 2) Indices: handle first (use path or type if available)
    # Use path string search OR symbol type constant if available
    is_index = False
    try:
        if path and ("Index" in path or "Indices" in path):
            is_index = True
        elif sym_type is not None and sym_type == getattr(mt5, "SYMBOL_TYPE_INDEX", sym_type):
            is_index = True
    except Exception:
        # defensive: any error here -> don't crash, continue
        is_index = False

    if is_index:
        logging.info(f"Detected Index: {symbol_name} quoted in {quote}. Converting to USD.")

        # Prefer direct local->USD pair (e.g., CHFUSD), else try USDlocal (USDCHF)
        fx_direct = f"{quote}USD"   # CHFUSD
        fx_inverse = f"USD{quote}"  # USDCHF

        # Try direct
        fx_series = get_fx_series(fx_direct, cached_symbols, bars, timeframe)
        if fx_series is not None:
            logging.info(f"{symbol_name}: converting via {fx_direct} (multiply by {fx_direct}).")
            converted = symbol_close * fx_series
            logging.debug(f"index head:\n{symbol_close.head()}")
            logging.debug(f"fx head ({fx_direct}):\n{fx_series.head()}")
            logging.debug(f"converted head:\n{converted.head()}")
            return converted

        # Try inverse
        fx_series = get_fx_series(fx_inverse, cached_symbols, bars, timeframe)
        if fx_series is not None:
            logging.info(f"{symbol_name}: converting via inverted {fx_inverse} (divide by {fx_inverse}).")
            converted = symbol_close / fx_series
            logging.debug(f"index head:\n{symbol_close.head()}")
            logging.debug(f"fx head ({fx_inverse}):\n{fx_series.head()}")
            logging.debug(f"converted head:\n{converted.head()}")
            return converted

        logging.warning(f"⚠ No FX conversion path found for index {symbol_name} (quote={quote}). Returning None.")
        return None

    # 3) Commodities - leave as is
    is_commodity = False
    try:
        if path and ("Metal" in path or "Metals" in path or "Commodity" in path or "Commodities" in path):
            is_commodity = True
        elif sym_type is not None and sym_type == getattr(mt5, "SYMBOL_TYPE_COMMODITY", -1):
            is_commodity = True
    except Exception:
        is_commodity = False

    if is_commodity:
        logging.debug(f"{symbol_name} detected as commodity -> left as is.")
        logging.debug(f"sample: {symbol_close.head()}")
        return symbol_close

    # 4) FX detection (after filtering indices/commodities)
    is_fx = False
    try:
        if path and "Forex" in path:
            is_fx = True
        elif sym_type is not None and sym_type == getattr(mt5, "SYMBOL_TYPE_FOREX", sym_type):
            is_fx = True
        else:
            # conservative: only mark as FX if both base and quote look like currency codes
            if base and quote and len(str(base)) == 3 and len(str(quote)) == 3:
                # But prefer path/type; set False unless path hinted Forex
                is_fx = ("Forex" in path)
    except Exception:
        is_fx = False

    if is_fx:
        logging.debug(f"{symbol_name} treated as FX pair.")

        # FX pairs starting with USD -> invert (USDxxx -> 1 / USDxxx)
        if base == "USD":
            logging.debug(f"{symbol_name} starts with USD -> inverting.")
            fx_series = get_fx_series(f"{base}{quote}", cached_symbols, bars, timeframe)
            if fx_series is not None:
                converted = 1 / fx_series
                logging.debug(f"sample fx:\n{fx_series.head()}")
                logging.debug(f"sample inverted:\n{converted.head()}")
                return converted
            logging.warning(f"⚠ FX pair {base}{quote} not available for inversion.")
            return None

        # FX pairs ending with USD -> already USD quoted
        if quote == "USD":
            logging.debug(f"{symbol_name} ends with USD -> left as is.")
            logging.debug(f"sample: {symbol_close.head()}")
            return symbol_close

        # Cross pair -> leave as is (per strict rules)
        logging.debug(f"{symbol_name} is a cross pair -> left as is.")
        logging.debug(f"sample: {symbol_close.head()}")
        return symbol_close

    # 5) Everything else -> leave as is
    logging.debug(f"No rule matched for {symbol_name} -> left as is.")
    logging.debug(f"sample: {symbol_close.head()}")
    return symbol_close
