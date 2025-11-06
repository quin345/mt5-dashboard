import pandas as pd

# Load JSON file containing a list of time series data
df = pd.read_json("usdchf_tick.json")

# Convert timestamp from milliseconds to datetime
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

# Reorder columns for readability
df = df[['datetime', 'timestamp', 'askPrice', 'bidPrice', 'askVolume', 'bidVolume']]

# Display head and tail
print("Head:\n", df.head())
print("\nTail:\n", df.tail())
