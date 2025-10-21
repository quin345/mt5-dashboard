import MetaTrader5 as mt5

# Initialize connection to MetaTrader 5
if not mt5.initialize():
    print("MT5 initialization failed:", mt5.last_error())
    quit()

# Retrieve all open positions
positions = mt5.positions_get()

if not positions:
    print("✅ No open positions to close.")
else:
    print(f"🔍 Found {len(positions)} open position(s). Attempting to close...")

    for pos in positions:
        ticket = pos.ticket
        symbol = pos.symbol
        volume = pos.volume
        position_type = pos.type  # 0 = BUY, 1 = SELL

        # Get current price for the symbol
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"⚠️ Failed to get tick data for {symbol}. Skipping position #{ticket}.")
            continue

        # Determine order type and price
        order_type = mt5.ORDER_TYPE_SELL if position_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if order_type == mt5.ORDER_TYPE_BUY else tick.ask

        # Create close request
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 0,
            "comment": "Auto-close all trades",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send the close request
        result = mt5.order_send(close_request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Failed to close position #{ticket} ({symbol}): {result.retcode}")
        else:
            print(f"✅ Successfully closed position #{ticket} ({symbol})")

# Shutdown MT5 connection
mt5.shutdown()
