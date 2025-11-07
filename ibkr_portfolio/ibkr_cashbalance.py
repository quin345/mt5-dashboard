from ib_insync import *
import pandas as pd

# Connect to IBKR
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

# Fetch account values
account_values = ib.accountValues()

# Filter for cash balances
cash_balances = [
    {'Account': v.account, 'Currency': v.currency, 'Cash Balance': round(float(v.value), 2)}
    for v in account_values if v.tag == 'CashBalance'
]

# Create DataFrame
df = pd.DataFrame(cash_balances)

# Display
print(df)

ib.disconnect()
