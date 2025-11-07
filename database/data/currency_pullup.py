import sqlite3
import pandas as pd

# Connect to your database
conn = sqlite3.connect("database.sqlite")

# Get all currency asset_ids
currency = pd.read_sql("SELECT asset_id FROM assets WHERE asset_class = 'Currency'", conn)
currency_ids = tuple(currency['asset_id'])

# Load prices for currency
query = f"""
SELECT date, asset_id, close
FROM prices
WHERE asset_id IN {currency_ids}
"""
df = pd.read_sql(query, conn)

# Pivot: rows = date, columns = asset_id, values = close
pivoted = df.pivot(index='date', columns='asset_id', values='close')

# Preview the result
print(pivoted.tail(10))
