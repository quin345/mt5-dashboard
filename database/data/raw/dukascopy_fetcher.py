import os
import subprocess
import json
import pandas as pd
import warnings
from datetime import datetime, timedelta
from tables import NaturalNameWarning

# Suppress HDF5 naming warnings
warnings.filterwarnings("ignore", category=NaturalNameWarning)

save_dir = "2015_tick_data"
os.makedirs(save_dir, exist_ok=True)

def fetch_and_store_tick_data(start_date: datetime, end_date: datetime, asset: str):
    exempted_days = []

    while start_date < end_date:
        next_date = start_date + timedelta(days=1)
        from_str = start_date.strftime('%Y-%m-%d')
        print(f"📅 Fetching data for {asset} {from_str}...")

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
            console.error("Error:", error.message);
            process.exit(1);
          }}
        }})();"""

        try:
            result = subprocess.run(
                ['node', '-e', js_code],
                capture_output=True,
                text=True,
                timeout=90
            )

            if result.returncode != 0:
                print(f"❌ Node.js error on {from_str}: {result.stderr.strip()}")
                exempted_days.append({'date': from_str, 'asset': asset})
            else:
                try:
                    tick_data = json.loads(result.stdout)
                    if not tick_data or not isinstance(tick_data, list):
                        print(f"⚠️ No valid data for {asset} {from_str}.")
                        exempted_days.append({'date': from_str, 'asset': asset})
                    else:
                        df = pd.DataFrame(tick_data)
                        ts = pd.to_datetime(df['timestamp'], unit='ms')
                        df['year'] = ts.dt.year
                        df['month'] = ts.dt.month
                        df['day'] = ts.dt.day

                        hdf5_path = os.path.join(save_dir, f"{asset}_tick_data.h5")
                        with pd.HDFStore(hdf5_path, mode='a') as store:
                            for (y, m, d), group in df.groupby(['year', 'month', 'day']):
                                key = f"/{asset}/y{y}/m{m:02}/d{d:02}"
                                store.put(key, group.drop(columns=['year', 'month', 'day']), format='table', data_columns=True)

                        print(f"✅ Saved data for {asset} {from_str}.")

                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error on {from_str}: {e}")


        except subprocess.TimeoutExpired:
            print(f"⏱️ Timeout fetching data for {from_str}")


        start_date = next_date

    print(f"🏁 Finished fetching {asset} tick data.")

    # Save exempted days to CSV
    if exempted_days:
        new_df = pd.DataFrame(exempted_days)
        csv_path = 'exempted_days.csv'

        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df.drop_duplicates(subset=['asset', 'date'], inplace=True)
        else:
            combined_df = new_df

        combined_df.to_csv(csv_path, index=False)
        print(f"📄 Updated {csv_path} with {len(new_df)} new entries.")