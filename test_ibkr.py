from ib_insync import *
import pandas as pd

# Connect to IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Fetch portfolio
portfolio = ib.portfolio()

# Convert to DataFrame
data = [{
    'Symbol': p.contract.symbol,
    'Currency': p.contract.currency,
    'Position': p.position,
    'Avg Cost': p.averageCost,
    'Market Price': p.marketPrice,
    'Unrealized PnL': p.unrealizedPNL,
    'Realized PnL': p.realizedPNL
} for p in portfolio]

df = pd.DataFrame(data)

# Display the table
print(df)

# Disconnect
ib.disconnect()
