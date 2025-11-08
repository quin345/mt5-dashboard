import csv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from dukascopy_fetcher import fetch_and_store_tick_data

# === Path to your CSV file ===
csv_file = "missing_day_group.csv"

# === Parse CSV and group dates by instrument ===
instrument_dates = defaultdict(list)

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    for row in reader:
        if len(row) < 2:
            continue
        instrument = row[0].strip()
        date_str = row[1].strip()
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            instrument_dates[instrument].append(date)
        except ValueError:
            print(f"⚠️ Invalid date format: {date_str}")

# === Function to process one instrument's dates ===
def process_instrument(instrument, dates):
    print(f"🚀 Starting fetch for {instrument} with {len(dates)} dates")
    for date in sorted(dates):
        try:
            fetch_and_store_tick_data(date, date + timedelta(days=1), instrument)
        except Exception as e:
            print(f"❌ Error fetching {instrument} on {date.date()}: {e}")
    print(f"✅ Finished {instrument}")

# === Run each instrument group in parallel ===
with ThreadPoolExecutor(max_workers=32) as executor:
    for instrument, dates in instrument_dates.items():
        executor.submit(process_instrument, instrument, dates)