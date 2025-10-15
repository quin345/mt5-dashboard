"""
data_fetcher.py
---------------
Robust fetcher for historical close prices from MetaTrader5.

Features:
- Normalizes symbols to avoid accidental duplicates (strip + upper).
- In-process cache to avoid refetching already-fetched symbols.
- Thread-safe to protect cache when used concurrently.
- Drops incomplete series (< lookback_days).
- Aligns valid series on common timestamps (inner join).
"""

from __future__ import annotations
import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime
from threading import Lock
from typing import Iterable, Optional, Dict

# Simple in-memory cache (process-lifetime). Stores pd.Series (closes) or None for failed fetch.
_FETCH_CACHE: Dict[str, Optional[pd.Series]] = {}
_CACHE_LOCK = Lock()


def _normalize_symbol(sym: str) -> str:
    """Normalize a symbol to canonical form for de-duplication."""
    if not isinstance(sym, str):
        return str(sym)
    return sym.strip().upper()


def ensure_history(symbol: str, timeframe, bars: int) -> bool:
    """Ensure MT5 server has enough historical data for the symbol."""
    try:
        mt5.symbol_select(symbol, True)
        preload = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars * 2)
    except Exception as e:  # keep MT5 exceptions from crashing caller
        logging.warning(f"[HISTORY] Exception preloading {symbol}: {e}")
        return False

    if preload is None or len(preload) == 0:
        logging.warning(f"[HISTORY] Unable to preload {symbol}")
        return False
    return True


def fetch_closes(symbol: str, bars: int, timeframe, lookback_days: Optional[int] = None) -> Optional[pd.Series]:
    """
    Fetch close prices for a given symbol and timeframe.
    Uses the module-level cache to avoid duplicate MT5 calls within this process.
    Returns a pd.Series indexed by datetime (name == original symbol string) or None on failure.
    """
    norm = _normalize_symbol(symbol)

    # First check cache under lock
    with _CACHE_LOCK:
        if norm in _FETCH_CACHE:
            cached = _FETCH_CACHE[norm]
            if cached is None:
                logging.info(f"[CACHE-HIT] {symbol} previously failed; skipping.")
                return None
            # Return a copy to avoid outside mutation of cached object
            logging.info(f"[CACHE-HIT] Using cached data for {symbol}")
            return cached.copy()

    # Resolve timeframe constant
    timeframe_const = getattr(mt5, timeframe, timeframe) if isinstance(timeframe, str) else timeframe
    if timeframe_const is None:
        logging.error(f"[TIMEFRAME] Invalid timeframe: {timeframe}")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    # Ensure history loaded
    if not ensure_history(symbol, timeframe_const, bars):
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    # Fetch rates
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe_const, 0, bars)
    except Exception as e:
        logging.warning(f"[FETCH] Exception fetching {symbol}: {e}")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    if rates is None or len(rates) == 0:
        logging.warning(f"[FETCH] No data fetched for {symbol}")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    # Convert to DataFrame and clean
    df = pd.DataFrame(rates)
    if 'time' not in df.columns:
        logging.warning(f"[FETCH] Unexpected data format for {symbol}")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[~df.index.duplicated(keep='last')]
    df = df[df.index <= datetime.now()]

    if 'close' not in df.columns:
        logging.warning(f"[FETCH] No 'close' column for {symbol}")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    closes = df['close'].rename(symbol)
    actual_bars = len(closes)

    # Check completeness
    if lookback_days is not None and actual_bars < lookback_days:
        logging.warning(f"[DROP] {symbol} only has {actual_bars}/{lookback_days} bars — dropped.")
        with _CACHE_LOCK:
            _FETCH_CACHE[norm] = None
        return None

    logging.info(f"[OK] {symbol} fetched successfully ({actual_bars} bars)")

    # Cache the result (store a copy to be safe)
    with _CACHE_LOCK:
        _FETCH_CACHE[norm] = closes.copy()

    return closes.copy()


def fetch_multiple(symbols: Iterable[str], bars: int, timeframe, lookback_days: int) -> Optional[pd.DataFrame]:
    """
    Fetch closes for many symbols.
    - Normalizes symbols and skips duplicates (first-occurrence wins).
    - Uses in-process cache to prevent redundant MT5 calls.
    - Returns DataFrame aligned by inner join (common timestamps) with only valid symbols,
      or None if nothing valid.
    """
    # Preserve order while deduping: map normalized -> original first seen
    norm_to_original: Dict[str, str] = {}
    for sym in symbols:
        norm = _normalize_symbol(sym)
        if norm not in norm_to_original:
            norm_to_original[norm] = sym
        else:
            logging.info(f"[SKIP] Duplicate input symbol (normalized) skipped: {sym} -> {norm_to_original[norm]}")

    valid_series: Dict[str, pd.Series] = {}

    for norm, original_sym in norm_to_original.items():
        closes = fetch_closes(original_sym, bars, timeframe, lookback_days)
        if closes is None:
            logging.warning(f"[SKIP] {original_sym} excluded (no / incomplete data).")
            continue
        # final length check (defensive)
        if lookback_days is not None and len(closes) < lookback_days:
            logging.warning(f"[SKIP] {original_sym} excluded after length check ({len(closes)} < {lookback_days}).")
            continue
        valid_series[original_sym] = closes

    if not valid_series:
        logging.error("[RESULT] No valid symbols fetched.")
        return None

    # Align by inner join: only keep timestamps common to all series
    df = pd.DataFrame(valid_series).dropna(how='any')  # inner join behavior

    if df.empty:
        logging.warning("[ALIGN] No overlapping timestamps across valid symbols. Returning original per-series data as separate columns where possible.")
        # If you prefer to return outer-join instead, change behavior here.
        # For now, return a DataFrame constructed from valid_series without dropna (outer join)
        df_outer = pd.DataFrame(valid_series)
        # final filter for per-column completeness
        cols = [c for c in df_outer.columns if len(df_outer[c].dropna()) >= lookback_days]
        df_outer = df_outer[cols]
        if df_outer.empty:
            logging.error("[RESULT] After alignment no symbol meets lookback_days requirement.")
            return None
        return df_outer

    # Final completeness check (after alignment)
    final_cols = [c for c in df.columns if len(df[c].dropna()) >= lookback_days]
    df = df[final_cols]

    if df.empty:
        logging.error("[RESULT] No columns remain after final completeness check.")
        return None

    logging.info(f"[RESULT] {len(df.columns)} valid symbols retained after filtering incomplete data.")
    return df
