import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dukascopy_fetcher import fetch_and_store_tick_data

# Path to your CSV file
csv_file = "last_tick_update.csv"  # No header row

# Target end date
end_date = datetime.strptime("2025-11-09", "%Y-%m-%d")

# Function to run the fetcher
def run_fetch(symbol, last_date_str):
    try:
        start_date = datetime.strptime(last_date_str, "%Y-%m-%d") + timedelta(days=1)
        if start_date >= end_date:
            print(f"⏩ Skipping {symbol}: start date {start_date.date()} is beyond end date.")
            return
        print(f"🚀 Fetching {symbol} from {start_date.date()} to {end_date.date()}")
        fetch_and_store_tick_data(start_date, end_date, symbol)
    except Exception as e:
        print(f"❌ Error fetching {symbol} from {last_date_str}: {e}")

# Parse CSV and collect instrument-date pairs
symbols_dates = []
with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) < 2:
            continue  # Skip incomplete rows
        symbol = row[0].strip()
        last_date = row[1].strip()
        if symbol and last_date:
            symbols_dates.append((symbol, last_date))

# Run all in parallel
with ThreadPoolExecutor(max_workers=32) as executor:
    for symbol, last_date in symbols_dates:
        executor.submit(run_fetch, symbol, last_date)