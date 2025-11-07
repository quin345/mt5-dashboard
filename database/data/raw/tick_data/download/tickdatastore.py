import subprocess
import json
import pandas as pd
import warnings
from datetime import datetime, timedelta
from tables import NaturalNameWarning
import argparse

# Suppress HDF5 naming warnings
warnings.filterwarnings("ignore", category=NaturalNameWarning)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Fetch tick data from Dukascopy")
parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format")
parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format")
parser.add_argument("--asset", required=True, help="Asset symbol (e.g., eurusd, xauusd)")

args = parser.parse_args()

# Convert to datetime
start_date = datetime.strptime(args.start, "%Y-%m-%d")
end_date = datetime.strptime(args.end, "%Y-%m-%d")
asset = args.asset

while start_date < end_date:
    next_date = start_date + timedelta(days=1)

    # Format dates for JavaScript
    from_str = start_date.strftime('%Y-%m-%d')
    to_str = next_date.strftime('%Y-%m-%d')
    print(f"📅 Fetching data for {from_str}...")

    # Run JS script with dynamic dates
    js_code = f"""
    const {{ getHistoricalRates }} = require('dukascopy-node');
    (async () => {{
      const fromDate = new Date(Date.UTC({start_date.year}, {start_date.month - 1}, {start_date.day}, 0, 0, 0));
      const toDate = new Date(Date.UTC({next_date.year}, {next_date.month - 1}, {next_date.day}, 0, 0, 0));
      try {{
        const data = await getHistoricalRates({{
          instrument: '{asset}',
          dates: {{ from: fromDate, to: toDate }},
          timeframe: 'tick',
          format: 'json',
          batchSize: 10,
          pauseBetweenBatchesMs: 500
        }});
        console.log(JSON.stringify(data));
      }} catch (error) {{
        console.error("Error:", error);
        process.exit(1);
      }}
    }})();
    """

    try:
        result = subprocess.run(['node', '-e', js_code], capture_output=True, text=True, timeout=60)
        tick_data = json.loads(result.stdout)

        if not tick_data:
            print(f"⚠️ No data for {from_str}. Skipping.")
        else:
            df = pd.DataFrame(tick_data)
            ts = pd.to_datetime(df['timestamp'], unit='ms')
            df['year'] = ts.dt.year
            df['month'] = ts.dt.month
            df['day'] = ts.dt.day

            with pd.HDFStore(f"{asset}_tick_data.h5", mode='a') as store:
                for (y, m, d), group in df.groupby(['year', 'month', 'day']):
                    key = f"/{asset}/y{y}/m{m:02}/d{d:02}"
                    store.put(key, group.drop(columns=['year', 'month', 'day']), format='table', data_columns=True)

            print(f"✅ Saved data for {from_str}.")

    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        print(f"❌ Error processing {from_str}: {e}")

    start_date = next_date

print(f"🎉 Finished fetching {asset} tick data.")