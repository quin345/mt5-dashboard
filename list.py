import MetaTrader5 as mt5

# Connect to MetaTrader 5
if not mt5.initialize():
    print("MT5 initialization failed:", mt5.last_error())
    quit()

# Get all symbols and filter only those visible in Market Watch
selected_symbols = [symbol for symbol in mt5.symbols_get() if symbol.visible]

# Display symbol name and description
print("Selected symbols in Market Watch:")
for symbol in selected_symbols:
    print(f"{symbol.name} - {symbol.description}")

# Disconnect from MT5
mt5.shutdown()
