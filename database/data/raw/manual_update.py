# run_fetcher.py

import argparse
from datetime import datetime
from fetch_tick_data import fetch_and_store_tick_data

parser = argparse.ArgumentParser(description="Fetch tick data from Dukascopy")
parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format")
parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format")
parser.add_argument("--asset", required=True, help="Asset symbol (e.g., eurusd, xauusd)")

args = parser.parse_args()

start_date = datetime.strptime(args.start, "%Y-%m-%d")
end_date = datetime.strptime(args.end, "%Y-%m-%d")
asset = args.asset

fetch_and_store_tick_data(start_date, end_date, asset)