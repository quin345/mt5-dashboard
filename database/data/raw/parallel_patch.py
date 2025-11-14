import csv, ast, os
from collections import defaultdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from fetch_tick_data import fetch_tick_data_for_day


# === Step 1: Parse CSV ===
csv_file = "missing_day_group.csv"
instrument_dates = defaultdict(list)

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # Skip header
    for row in reader:
        if len(row) < 2:
            continue
        instrument = row[0].strip()
        try:
            date_list = ast.literal_eval(row[1])
            for date_str in date_list:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    instrument_dates[instrument].append(date)
                except ValueError:
                    print(f"⚠️ Invalid date format: {date_str}")
        except Exception as e:
            print(f"⚠️ Failed to parse date list for {instrument}: {e}")

# === Step 2: Flatten tasks ===
all_tasks = [(instr, date) for instr, dates in instrument_dates.items() for date in dates]

# === Step 3: Split into 32 chunks ===
def chunkify(lst, n):
    avg = len(lst) // n
    chunks = [lst[i * avg:(i + 1) * avg] for i in range(n)]
    remainder = lst[n * avg:]
    for i, item in enumerate(remainder):
        chunks[i % n].append(item)
    return chunks

task_chunks = chunkify(all_tasks, 32)

# === Step 4: Worker function ===
def worker(worker_id, tasks):
    temp_file = f"temp_worker_{worker_id}.h5"
    for instrument, date in tasks:
        try:
            print(f"🧵 Worker {worker_id}: {instrument} {date.date()}")
            data = fetch_tick_data_for_day(instrument, date)
            
            if data:
                df = pd.DataFrame(data)
                ts = pd.to_datetime(df['timestamp'], unit='ms')
                df['year'] = ts.dt.year
                df['month'] = ts.dt.month
                df['day'] = ts.dt.day

                os.makedirs(".", exist_ok=True)

                with pd.HDFStore(temp_file, mode='a') as store:
                    for (y, m, d), group in df.groupby(['year', 'month', 'day']):
                        key = f"/{instrument}/y{y}/m{m:02}/d{d:02}"
                        store.put(key, group.drop(columns=['year', 'month', 'day']), format='table', data_columns=True) 
                print(f"✅ Worker {worker_id} saved {instrument} {date.date()}")
            print(f"⚠️ Worker {worker_id} no data for {instrument} {date.date()}")
        except Exception as e:
            print(f"❌ Worker {worker_id} error on {instrument} {date.date()}: {e}")

# === Step 5: Run workers in parallel ===
with ThreadPoolExecutor(max_workers=28) as executor:
    for i, chunk in enumerate(task_chunks):
        executor.submit(worker, i, chunk)

# === Step 6: Merge temp files (robust version) ===
def merge_hdf5_files(temp_files, final_file):
    with pd.HDFStore(final_file, mode='a') as final_store:
        for temp in temp_files:
            if not os.path.exists(temp):
                print(f"⚠️ Skipping missing file: {temp}")
                continue
            try:
                with pd.HDFStore(temp, mode='r') as temp_store:
                    keys = temp_store.keys()
                    if not keys:
                        print(f"⚠️ Skipping empty file: {temp}")
                        continue
                    for key in keys:
                        df = temp_store[key]
                        final_store.put(key, df, format='table', data_columns=True)
            except Exception as e:
                print(f"❌ Error reading {temp}: {e}")
            finally:
                try:
                    os.remove(temp)
                    print(f"🗑️ Deleted temp file: {temp}")
                except Exception as e:
                    print(f"⚠️ Could not delete {temp}: {e}")

temp_files = [f"temp_worker_{i}.h5" for i in range(32)]
merge_hdf5_files(temp_files, "final_tick_data.h5")

# === Step 7: Decompose final file into per-instrument files ===
def decompose_by_instrument(final_file, output_dir="split_by_instrument"):
    os.makedirs(output_dir, exist_ok=True)
    with pd.HDFStore(final_file, mode='r') as store:
        keys = store.keys()
        instrument_groups = defaultdict(list)
        for key in keys:
            instrument = key.strip("/").split("/")[0]
            instrument_groups[instrument].append(key)

        for instrument, group_keys in instrument_groups.items():
            out_path = os.path.join(output_dir, f"{instrument}_tick_data.h5")
            with pd.HDFStore(out_path, mode='w') as out_store:
                for key in group_keys:
                    df = store[key]
                    out_store.put(key, df, format='table', data_columns=True)

decompose_by_instrument("final_tick_data.h5")
print("✅ All tasks complete. Data split by instrument.")


# MERGE TO RAW FILES


def merge_instrument_file(instrument, fetched_dir="split_by_instrument", raw_dir="./2015_tick_data"):
    fetched_path = os.path.join(fetched_dir, f"{instrument}_tick_data.h5")
    raw_path = os.path.join(raw_dir, f"{instrument}_tick_data.h5")

    if not os.path.exists(fetched_path):
        print(f"⚠️ Fetched file missing: {instrument}")
        return
    if not os.path.exists(raw_path):
        print(f"⚠️ Raw file missing: {instrument}")
        return

    with pd.HDFStore(raw_path, mode='a') as raw_store, pd.HDFStore(fetched_path, mode='r') as fetched_store:
        for key in fetched_store.keys():
            if key in raw_store:
                print(f"🔁 Skipping duplicate key: {key} in {instrument}")
                continue
            df = fetched_store[key]
            raw_store.put(key, df, format='table', data_columns=True)

    print(f"✅ Merged fetched → raw: {instrument}")


fetched_dir = "split_by_instrument"     # Correct folder for fetched files
raw_dir = "./2015_tick_data"            # Correct folder for raw files

# Get list of instruments based on fetched files
instruments = [
    filename.replace("_tick_data.h5", "")
    for filename in os.listdir(fetched_dir)
    if filename.endswith("_tick_data.h5")
]

# Run merge in parallel
with ThreadPoolExecutor(max_workers=28) as executor:
    for instrument in instruments:
        executor.submit(merge_instrument_file, instrument, fetched_dir, raw_dir)
