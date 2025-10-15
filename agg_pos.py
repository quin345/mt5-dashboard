# save as mt5_aggregate_positions.py
import MetaTrader5 as mt5
import pandas as pd

# ---------- Connect to MetaTrader5 ----------
if not mt5.initialize():
    raise RuntimeError("Failed to initialize MT5 connection")

# ---------- Fetch open positions ----------
positions = mt5.positions_get()
if not positions:
    print("No open positions found.")
    mt5.shutdown()
    exit()

# Convert to DataFrame
df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())

# ---------- Aggregate data ----------
agg = (
    df.groupby("symbol")
    .agg({
        "volume": "sum",
        "profit": "sum",
        "price_open": "mean",
        "price_current": "mean"
    })
    .reset_index()
)

# Compute market value approximation
agg["market_value"] = agg["volume"] * agg["price_current"]

# Optional: Add total portfolio-level aggregation
total = pd.DataFrame([{
    "symbol": "TOTAL",
    "volume": agg["volume"].sum(),
    "profit": agg["profit"].sum(),
    "price_open": None,
    "price_current": None,
    "market_value": agg["market_value"].sum()
}])

agg = pd.concat([agg, total], ignore_index=True)

# ---------- Output ----------
print(agg.to_string(index=False))

# ---------- Clean up ----------
mt5.shutdown()
