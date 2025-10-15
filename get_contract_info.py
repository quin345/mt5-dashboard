import MetaTrader5 as mt5
import pandas as pd
import streamlit as st

# ---------------------------
# CONNECT TO METATRADER 5
# ---------------------------
if not mt5.initialize():
    print("❌ Failed to connect to MetaTrader 5. Make sure it’s open and logged in.")
    quit()

# ---------------------------
# GET OPEN POSITIONS
# ---------------------------
positions = mt5.positions_get()
if not positions:
    print("⚠️ No open positions found.")
    mt5.shutdown()
    quit()

# Convert to DataFrame
df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())

# Extract unique symbols from open positions
symbols = sorted(df["symbol"].unique())

print(f"\n✅ Found {len(symbols)} unique symbols in open positions:")
print(symbols)

# ---------------------------
# EXTRACT CONTRACT INFO
# ---------------------------
info_list = []

for sym in symbols:
    symbol_info = mt5.symbol_info(sym)
    if symbol_info is None:
        print(f"⚠️ Could not fetch info for {sym}")
        continue

    info_list.append({
        "Symbol": sym,
        "Description": symbol_info.description,
        "Base Currency": symbol_info.currency_base,
        "Profit Currency": symbol_info.currency_profit,
        "Contract Size": symbol_info.trade_contract_size,
        "Tick Size": symbol_info.trade_tick_size,
        "Tick Value": symbol_info.trade_tick_value,
        "Margin Initial": symbol_info.margin_initial,
        "Margin Maintenance": symbol_info.margin_maintenance,
    })

mt5.shutdown()

# ---------------------------
# OUTPUT TABLE
# ---------------------------
info_df = pd.DataFrame(info_list)
info_df.sort_values("Symbol", inplace=True)
print("\n=== CONTRACT INFORMATION ===\n")
print(info_df.to_string(index=False))

