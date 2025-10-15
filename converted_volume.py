"""
mt5_portfolio_summary.py

Produces a portfolio summary DataFrame with columns:
    symbol | volume_converted | market_value | price_open | price_current | weights

Follows the logic provided:
 - Inverts USD-leading pairs early (stores price_open_inverted, price_current_inverted).
 - Computes volume_converted per rules.
 - market_value = price_current_inverted * volume_converted (USD).
 - VWAP for price_open per symbol using price_open_inverted weighted by abs(volume_converted).
 - Aggregates per symbol, computes weights, sorts by descending weight.
 - Saves to Excel (.xlsx) if openpyxl available, otherwise CSV. Has dry-run mode.

Requires: MetaTrader5, pandas, numpy, openpyxl (optional).
"""

import argparse
import logging
import sys
from typing import Optional

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")
    logger.info("Connected to MetaTrader 5 terminal.")


def shutdown_mt5():
    try:
        mt5.shutdown()
        logger.info("MT5 shutdown completed.")
    except Exception as e:
        logger.warning(f"Error shutting down MT5: {e}")


def fetch_positions_df() -> pd.DataFrame:
    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError(f"Error fetching positions: {mt5.last_error()}")
    if len(positions) == 0:
        return pd.DataFrame()  # caller handles empty
    rows = []
    for p in positions:
        # Position object attributes might vary by MT5 build; use safe access
        rows.append({
            "ticket": int(p.ticket),
            "symbol": p.symbol,
            "volume": float(p.volume),        # lots
            "price_open": float(p.price_open),
            "type": int(p.type),             # 0=buy, 1=sell (mt5.POSITION_TYPE_BUY/SELL)
            "magic": getattr(p, "magic", None),
            "time": getattr(p, "time", None),
            "comment": getattr(p, "comment", None),
        })
    df = pd.DataFrame(rows)
    return df


def safe_symbol_info(symbol: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        logger.warning(f"symbol_info() missing for {symbol}")
        return {
            "trade_contract_size": 1.0,
            "currency_base": None,
            "currency_profit": None,
            "is_tradeable": False
        }
    # Some symbols may not have attributes; use getattr with defaults
    return {
        "trade_contract_size": float(getattr(info, "trade_contract_size", 1.0) or 1.0),
        "currency_base": getattr(info, "currency_base", None),
        "currency_profit": getattr(info, "currency_profit", None),
        "is_tradeable": getattr(info, "trade_mode", None) is not None or True
    }


def get_mid_price(symbol: str) -> Optional[float]:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.warning(f"symbol_info_tick() missing for {symbol}")
        return None
    bid = getattr(tick, "bid", None)
    ask = getattr(tick, "ask", None)
    last = getattr(tick, "last", None)
    if bid is not None and ask is not None:
        return float((bid + ask) / 2.0)
    if last is not None:
        return float(last)
    logger.warning(f"Cannot determine current price for {symbol}; tick lacked bid/ask/last.")
    return None


def compute_portfolio_summary(df_positions: pd.DataFrame, dry_run: bool = False) -> pd.DataFrame:
    if df_positions.empty:
        logger.info("No open positions found.")
        return pd.DataFrame(columns=["symbol", "volume_converted", "market_value", "price_open", "price_current", "weights"])

    # Enrich with symbol info
    symbol_info_cache = {}
    enriched_rows = []
    for _, r in df_positions.iterrows():
        sym = r["symbol"]
        if sym not in symbol_info_cache:
            symbol_info_cache[sym] = safe_symbol_info(sym)
        info = symbol_info_cache[sym]
        enriched_rows.append({
            **r.to_dict(),
            "trade_contract_size": info["trade_contract_size"],
            "currency_base": info["currency_base"],
            "currency_profit": info["currency_profit"]
        })

    df = pd.DataFrame(enriched_rows)

    # Normalize types & names
    df["lots"] = df["volume"].astype(float)  # lots
    df["contract_size"] = df["trade_contract_size"].astype(float)
    df["position_type"] = df["type"].astype(int)
    # Determine direction: BUY -> +1, SELL -> -1
    df["direction"] = np.where(df["position_type"] == mt5.POSITION_TYPE_BUY, 1.0, -1.0)

    # Fetch current price and compute inversion logic
    price_current_list = []
    price_open_list = []
    price_current_inverted = []
    price_open_inverted = []

    for _, row in df.iterrows():
        symbol = row["symbol"]
        # price_open from position
        po = float(row["price_open"])
        # price_current via tick (mid)
        pc = get_mid_price(symbol)
        if pc is None:
            # fallback: use position price_open as current if tick missing
            logger.warning(f"Using price_open as price_current fallback for {symbol}")
            pc = po

        # If symbol starts with USD -> invert early
        if symbol.upper().startswith("USD"):
            # store inverted form
            # avoid division by zero
            if po == 0 or pc == 0:
                raise ZeroDivisionError(f"Encountered zero price for {symbol} while inverting.")
            po_inv = 1.0 / po
            pc_inv = 1.0 / pc
        else:
            po_inv = po
            pc_inv = pc

        price_open_list.append(po)
        price_current_list.append(pc)
        price_open_inverted.append(po_inv)
        price_current_inverted.append(pc_inv)

    df["price_open_raw"] = price_open_list
    df["price_current_raw"] = price_current_list
    df["price_open_inverted"] = price_open_inverted
    df["price_current_inverted"] = price_current_inverted

    # Compute volume_converted per the rules
    def compute_volume_converted(row):
        sym = row["symbol"].upper()
        lots = float(row["lots"])
        contract = float(row["contract_size"])
        po_inv = float(row["price_open_inverted"])  # already inverted when needed
        # RULES:
        # If symbol starts with USD -> volume = lots * contract_size * (1 / price_open_inverted) (quote currency units)
        # If symbol ends with USD -> volume = lots * contract_size (base currency units)
        # For commodities, indices, crypto -> volume = lots * contract_size
        if sym.startswith("USD"):
            # avoid division by zero
            if po_inv == 0:
                logger.warning(f"price_open_inverted is zero for {sym}; setting volume to 0")
                return 0.0
            return lots * contract * (1.0 / po_inv)
        elif sym.endswith("USD"):
            return lots * contract
        else:
            # commodities, indices, crypto, other FX where USD not leading or trailing
            return lots * contract

    df["volume_converted"] = df.apply(compute_volume_converted, axis=1)
    # apply direction sign
    df["volume_converted"] = df["volume_converted"] * df["direction"]

    # Compute market_value = price_current_inverted * volume_converted (USD value)
    df["market_value"] = df["price_current_inverted"].astype(float) * df["volume_converted"].astype(float)

    # Prepare for VWAP: per position price_open_inverted weighted by abs(volume_converted)
    df["abs_volume_converted"] = df["volume_converted"].abs()
    df["price_open_inverted_times_vol"] = df["price_open_inverted"].astype(float) * df["abs_volume_converted"].astype(float)

    # Aggregate per symbol
    agg = df.groupby("symbol").agg(
        volume_converted=("volume_converted", "sum"),
        market_value=("market_value", "sum"),
        price_current_inverted=("price_current_inverted", "last"),  # last observed current inverted price
        vwap_numer=("price_open_inverted_times_vol", "sum"),
        vwap_denom=("abs_volume_converted", "sum"),
    ).reset_index()

    # Compute VWAP (price_open)
    # VWAP = sum(price_open_inverted_i * abs(volume_converted_i)) / sum(abs(volume_converted_i))
    agg["price_open"] = np.where(
        agg["vwap_denom"] == 0,
        np.nan,
        agg["vwap_numer"] / agg["vwap_denom"]
    )

    # set price_current to price_current_inverted (all prices are USD per asset unit under our transform)
    agg["price_current"] = agg["price_current_inverted"]

    # Keep necessary columns, ensure numeric types
    final = agg[["symbol", "volume_converted", "market_value", "price_open", "price_current"]].copy()
    final["volume_converted"] = final["volume_converted"].astype(float)
    final["market_value"] = final["market_value"].astype(float)
    final["price_open"] = final["price_open"].astype(float)
    final["price_current"] = final["price_current"].astype(float)

    # Compute portfolio weights
    total_abs_mv = final["market_value"].abs().sum()
    if total_abs_mv == 0 or np.isnan(total_abs_mv):
        logger.warning("Total absolute market value is zero or NaN. Setting weights to NaN.")
        final["weights"] = np.nan
    else:
        final["weights"] = final["market_value"].abs() / total_abs_mv

    final = final.sort_values("weights", ascending=False).reset_index(drop=True)

    # rename columns to match exact spec: symbol | volume_converted | market_value | price_open | price_current | weights
    final = final[["symbol", "volume_converted", "market_value", "price_open", "price_current", "weights"]]

    # final sanity checks
    # Replace inf with NaN
    final.replace([np.inf, -np.inf], np.nan, inplace=True)

    if dry_run:
        logger.info("Dry-run mode: not saving to file. Returning DataFrame.")
        return final

    return final


def save_df(df: pd.DataFrame, filename_base: str = "portfolio_summary"):
    if df.empty:
        logger.info("Empty DataFrame; nothing to save.")
        return None
    xlsx_path = f"{filename_base}.xlsx"
    csv_path = f"{filename_base}.csv"
    try:
        # try to save to Excel first
        df.to_excel(xlsx_path, index=False)
        logger.info(f"Saved portfolio summary to Excel: {xlsx_path}")
        return xlsx_path
    except Exception as e:
        logger.warning(f"Failed to save to Excel ({e}). Falling back to CSV.")
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved portfolio summary to CSV: {csv_path}")
        return csv_path


def main(dry_run: bool = False):
    try:
        init_mt5()
        positions_df = fetch_positions_df()
        if positions_df.empty:
            logger.info("No positions open. Exiting.")
            return

        summary_df = compute_portfolio_summary(positions_df, dry_run=dry_run)
        # If dry_run, compute_portfolio_summary returns the DataFrame without saving.
        if dry_run:
            pd.set_option("display.float_format", lambda x: f"{x:,.6f}")
            print("\n=== Portfolio Summary (Dry-run) ===")
            print(summary_df.to_string(index=False))
            total_mv = summary_df["market_value"].abs().sum()
            logger.info(f"Total absolute market value: {total_mv:,.2f}")
        else:
            saved_path = save_df(summary_df)
            logger.info(f"Final portfolio summary saved at: {saved_path}")
            pd.set_option("display.float_format", lambda x: f"{x:,.6f}")
            print("\n=== Portfolio Summary Saved ===")
            print(summary_df.to_string(index=False))

    except Exception as exc:
        logger.exception(f"An error occurred: {exc}")
    finally:
        shutdown_mt5()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MT5 Portfolio Summary with VWAP and USD inversion logic")
    parser.add_argument("--dry-run", action="store_true", help="Do not save file; print the DataFrame and exit.")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
