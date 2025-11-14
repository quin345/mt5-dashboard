import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import pandas as pd

from fetch_tick_data import fetch_tick_data_for_day
from store_tick_data import store_tick_data

# Path to your CSV file
csv_file = "last_tick_update.csv"  # Assumes header row exists

# Target end date
end_date = datetime.strptime("2025-11-14", "%Y-%m-%d")
save_dir = "2015_tick_data"

# Function to run the fetcher
def run_fetch(symbol, last_date_str):
    try:
        start_date = datetime.strptime(last_date_str, "%Y-%m-%d") + timedelta(days=1)
        if start_date >= end_date:
            print(f"⏩ Skipping {symbol}: start date {start_date.date()} is beyond end date.")
            return

        print(f"🚀 Fetching {symbol} from {start_date.date()} to {end_date.date()}")

        while start_date < end_date:
            print(f"📅 Fetching data for {symbol} {start_date.strftime('%Y-%m-%d')}...")
            tick_data = fetch_tick_data_for_day(symbol, start_date)

            if tick_data:
                df = pd.DataFrame(tick_data)
                store_tick_data(df, symbol, save_dir)
                print(f"✅ Saved data for {symbol} {start_date.strftime('%Y-%m-%d')}.")
            else:
                print(f"⚠️ No valid data for {symbol} {start_date.strftime('%Y-%m-%d')}.")

            start_date += timedelta(days=1)

        print(f"🏁 Finished fetching {symbol} tick data.")

    except Exception as e:
        print(f"❌ Error fetching {symbol} from {last_date_str}: {e}")

# Parse CSV and collect instrument-date pairs
symbols_dates = []
with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    for row in reader:
        if len(row) < 2:
            continue
        symbol = row[0].strip()
        last_date = row[1].strip()
        if symbol and last_date:
            symbols_dates.append((symbol, last_date))

# Run all in parallel
with ThreadPoolExecutor(max_workers=32) as executor:
    for symbol, last_date in symbols_dates:
        executor.submit(run_fetch, symbol, last_date)