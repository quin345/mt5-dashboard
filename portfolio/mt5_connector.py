"""
mt5_connector.py
----------------
Handles MT5 initialization, shutdown, and retrieval of Market Watch symbols.
"""

import MetaTrader5 as mt5
import logging

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed, error={mt5.last_error()}")
    logging.info("MT5 initialized.")

def shutdown_mt5():
    mt5.shutdown()
    logging.info("MT5 shutdown.")

def get_marketwatch_symbols():
    """Return all visible symbols in Market Watch."""
    all_symbols = mt5.symbols_get()
    symbols = [s.name for s in all_symbols if getattr(mt5.symbol_info(s.name), "visible", True)]
    logging.info("Found %d symbols in Market Watch.", len(symbols))
    return sorted(list(set(symbols)))
