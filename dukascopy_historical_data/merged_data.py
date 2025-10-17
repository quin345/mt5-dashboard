import os
import glob
import pandas as pd
import sqlite3

# ---------- Settings ----------
csv_folder = os.getcwd()  # or specify a path
db_file = os.path.join(csv_folder, 'market_data.db')
table_name = 'daily_prices'

# ---------- Find all CSV files ----------
csv_files = glob.glob(os.path.join(csv_folder, '*_daily_close.csv'))

# ---------- Merge CSVs ----------
merged_df = None

for file in csv_files:
    symbol = os.path.basename(file).replace('_daily_close.csv', '').lower()
    df = pd.read_csv(file)

    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
    df = df[['timestamp', 'close']].rename(columns={'close': symbol})

    if merged_df is None:
        merged_df = df
    else:
        merged_df = pd.merge(merged_df, df, on='timestamp', how='outer')

# ---------- Store in SQLite ----------
conn = sqlite3.connect(db_file)
merged_df.to_sql(table_name, conn, if_exists='replace', index=False)
conn.close()

print(f"\n✅ Stored merged data in {db_file} under table '{table_name}'")
