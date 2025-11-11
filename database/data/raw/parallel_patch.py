import csv, ast, os
from collections import defaultdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from fetch_tick_data import fetch_tick_data_for_day
from store_tick_data import store_tick_data

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
                store_tick_data(df, instrument, ".", hdf5_filename=temp_file)
        except Exception as e:
            print(f"❌ Worker {worker_id} error on {instrument} {date.date()}: {e}")

# === Step 5: Run workers in parallel ===
with ThreadPoolExecutor(max_workers=32) as executor:
    for i, chunk in enumerate(task_chunks):
        executor.submit(worker, i, chunk)

# === Step 6: Merge temp files ===
def merge_hdf5_files(temp_files, final_file):
    with pd.HDFStore(final_file, mode='a') as final_store:
        for temp in temp_files:
            with pd.HDFStore(temp, mode='r') as temp_store:
                for key in temp_store.keys():
                    df = temp_store[key]
                    final_store.put(key, df, format='table', data_columns=True)
            os.remove(temp)

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