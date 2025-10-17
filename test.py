import MetaTrader5 as mt5
from collections import defaultdict

# Initialize MT5 connection
if not mt5.initialize():
    print("MT5 initialization failed:", mt5.last_error())
    quit()

# Get all open positions
positions = mt5.positions_get()
if positions is None or len(positions) == 0:
    print("No open positions or error occurred:", mt5.last_error())
    mt5.shutdown()
    quit()

# Aggregate exposure per symbol
exposure_by_symbol = defaultdict(float)
total_exposure = 0.0

for pos in positions:
    symbol = pos.symbol
    volume = pos.volume
    direction = pos.type  # 0 = BUY, 1 = SELL

    symbol_info = mt5.symbol_info(symbol)
    tick_info = mt5.symbol_info_tick(symbol)

    if symbol_info is None or tick_info is None:
        print(f"Missing data for {symbol}")
        continue

    contract_size = symbol_info.trade_contract_size
    price = tick_info.ask if direction == mt5.ORDER_TYPE_BUY else tick_info.bid
    exposure = volume * contract_size * price

    # Adjust for direction
    if direction == mt5.ORDER_TYPE_BUY:
        exposure_by_symbol[symbol] += exposure
    elif direction == mt5.ORDER_TYPE_SELL:
        exposure_by_symbol[symbol] -= exposure

    total_exposure += abs(exposure)

# Display exposure and weights
print("Exposure and Weights by Symbol:")
print("-" * 50)
for symbol, exposure in exposure_by_symbol.items():
    weight = (abs(exposure) / total_exposure) * 100 if total_exposure != 0 else 0
    print(f"{symbol}: {exposure:.2f} USD ({weight:.2f}%)")

print("-" * 50)
print(f"Total Gross Exposure: {total_exposure:.2f} USD")

mt5.shutdown()
