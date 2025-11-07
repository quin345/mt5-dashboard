from ib_insync import *
import pandas as pd

# Connect to IB Gateway or TWS
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)  # Adjust port if needed

# Fetch portfolio
portfolio = ib.portfolio()

# Convert to DataFrame
data = [{
    'Symbol': p.contract.symbol,
    'Security Type': getattr(p.contract, 'secType', 'Unknown'),
    'Currency': p.contract.currency,
    'Position': p.position,
    'Avg Cost': p.averageCost,
    'Market Price': p.marketPrice,
    'Unrealized PnL': p.unrealizedPNL,
    'Realized PnL': p.realizedPNL
} for p in portfolio]

df = pd.DataFrame(data)

# Check if portfolio is empty
if df.empty:
    print("Portfolio is empty or not loaded.")
else:
    # Group by Security Type and display each group
    grouped = df.groupby('Security Type')
    for sec_type, group in grouped:
        print(f"\nSecurity Type: {sec_type}")
        print(group)

# Disconnect
ib.disconnect()
