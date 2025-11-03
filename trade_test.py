import MetaTrader5 as mt5

# Connect to MetaTrader 5
if not mt5.initialize():
    print("Initialization failed:", mt5.last_error())
    quit()

# Define symbol weights
weights = {
    "EURUSD": 0.30,
    "USDJPY": 0.20,
    "CADJPY": 0.20,
    "USDCHF": 0.30
}

# Get account info
account_info = mt5.account_info()
if account_info is None:
    print("Failed to get account info")
    mt5.shutdown()
    quit()

balance = account_info.balance
risk_per_trade = 0.0001  # 1% risk per trade (adjust as needed)
total_exposure = balance * risk_per_trade

# Function to send market order
def send_order(symbol, lot):
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        "deviation": 10,
        "magic": 123456,
        "comment": "Weighted exposure trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order for {symbol} failed: {result.retcode}")
    else:
        print(f"Order for {symbol} placed successfully")

# Place trades based on weights
for symbol, weight in weights.items():
    if not mt5.symbol_select(symbol, True):
        print(f"Symbol {symbol} not available")
        continue

    price = mt5.symbol_info_tick(symbol).ask
    lot_size = (total_exposure * weight) / price
    lot_size = round(lot_size, 2)  # Round to 2 decimal places

    send_order(symbol, lot_size)

mt5.shutdown()
