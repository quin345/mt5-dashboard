import pandas as pd

# Load JSON file containing a list of time series data
df = pd.read_json("xauusd_tick.json")


# Reorder columns for readability
df = df[['timestamp', 'askPrice', 'bidPrice', 'askVolume', 'bidVolume']]

# Display head and tail
print("Head:\n", df.head())
print("\nTail:\n", df.tail())
