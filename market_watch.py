# save as mt5_market_watch_summary.py
import MetaTrader5 as mt5
import pandas as pd
import os

# ---------- Connect to MetaTrader5 ----------
if not mt5.initialize():
    raise RuntimeError("Failed to initialize MT5 connection")

# ---------- Fetch visible symbols from Market Watch ----------
symbols = mt5.symbols_get()
if not symbols:
    print("No symbols found.")
    mt5.shutdown()
    exit()

# Filter only visible symbols
visible_symbols = [s for s in symbols if s.visible]

# ---------- Build DataFrame ----------
df = pd.DataFrame([{
    "symbol": s.name,
    "description": s.description,
    "path": s.path,
    "spread": s.spread,
    "digits": s.digits,
    "trade_mode": s.trade_mode,
    "select": s.select,
    "visible": s.visible
} for s in visible_symbols])

# ---------- Output ----------
print(df.to_string(index=False))

# ---------- Save to CSV ----------
output_file = os.path.join(os.getcwd(), "market_watch_symbols.csv")
df.to_csv(output_file, index=False)
print(f"\nCSV file saved to: {output_file}")

# ---------- Clean up ----------
mt5.shutdown()
