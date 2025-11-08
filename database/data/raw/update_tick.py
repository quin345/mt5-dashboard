import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Path to your CSV file
csv_file = "hdf5_scan_report.csv"  # No header row

# Target end date
end_date = "2017-01-01"

# Function to run the command
def run_command(symbol, start_date):
    start_plus_one = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    cmd = [
        "python", "tickdatastore.py",
        "--start", start_plus_one,
        "--end", end_date,
        "--asset", symbol
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

# Parse CSV and collect instrument-date pairs
symbols_dates = {}
with open(csv_file, newline='') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) < 2:
            continue  # Skip incomplete rows
        symbol = row[0].strip()
        last_date = row[1].strip()
        if last_date:
            symbols_dates[symbol] = last_date

# Run all in parallel
with ThreadPoolExecutor(max_workers=32) as executor:
    for symbol, start_date in symbols_dates.items():
        executor.submit(run_command, symbol, start_date)
