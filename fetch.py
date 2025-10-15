import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

LOOKBACK_DAYS = 60
TIMEFRAME = mt5.TIMEFRAME_D1

if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

symbols = [s.name for s in mt5.symbols_get() if s.visible]
print(f"Found {len(symbols)} visible symbols.")

data = {}
for sym in symbols:
    mt5.symbol_select(sym, True)  # ensure symbol is selected and history loads
    rates = mt5.copy_rates_from_pos(sym, TIMEFRAME, 0, LOOKBACK_DAYS)
    if rates is None or len(rates) == 0:
        print(f"No data for {sym}")
        continue

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    data[sym] = df[['time', 'close']].set_index('time')

if data:
    closes = pd.concat(data, axis=1)
    closes.columns = closes.columns.droplevel(1)
    print("\nSample of daily close prices:")
    print(closes.tail())
else:
    print("No data fetched.")

mt5.shutdown()
