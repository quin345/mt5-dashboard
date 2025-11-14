import h5py
from datetime import datetime
import os
import csv
import calendar
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

# === Argument parser ===
def parse_args():
    parser = argparse.ArgumentParser(description="Scan HDF5 tick data for integrity.")
    parser.add_argument("--start-date", type=str, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", type=str, help="End date in YYYY-MM-DD format")
    args = parser.parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    end = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None
    return start, end

# === Dataset validation ===
def is_dataset_good(dset):
    try:
        _ = dset[...]
        return True
    except Exception:
        return False

# === Date generator excluding Saturdays ===
def valid_dates(year, month):
    num_days = calendar.monthrange(year, month)[1]
    for day in range(1, num_days + 1):
        date_obj = datetime(year, month, day)
        if date_obj.weekday() == 5:  # Saturday
            continue
        yield date_obj

# === HDF5 scanner ===
def scan_hdf5(file_path, start_date=None, end_date=None):
    last_updates = []
    missing_groups = []
    missing_tables = []

    with h5py.File(file_path, "r") as f:
        for instrument in f.keys():
            last_good_date = None

            for year_key in sorted(f[instrument].keys(), key=lambda x: int(x[1:])):
                year = int(year_key[1:])
                year_group = f[instrument][year_key]

                for month_key in sorted(year_group.keys(), key=lambda x: int(x[1:])):
                    month = int(month_key[1:])
                    month_group = year_group[month_key]

                    for date_obj in valid_dates(year, month):
                        date_str = date_obj.strftime("%Y-%m-%d")
                        day_key = f'd{str(date_obj.day).zfill(2)}'

                        try:
                            day_group = month_group[day_key]
                            if "table" in day_group and is_dataset_good(day_group["table"]):
                                last_good_date = date_str
                            else:
                                if (not start_date or date_obj >= start_date) and (not end_date or date_obj <= end_date):
                                    missing_tables.append([instrument, date_str])
                        except KeyError:
                            if (not start_date or date_obj >= start_date) and (not end_date or date_obj <= end_date):
                                missing_groups.append([instrument, date_str])

            if last_good_date:
                last_updates.append([instrument, last_good_date])

    return last_updates, missing_groups, missing_tables

# === CSV writers ===
def write_csv(filename, header, rows):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def write_grouped_csv(filename, grouped_data):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Instrument", "Missing Day Groups"])
        for instrument, dates in grouped_data.items():
            writer.writerow([instrument, dates])

def write_missing_day_summary(filename, grouped_data):
    total_missing = 0
    rows = []
    for instrument, dates in grouped_data.items():
        count = len(dates)
        total_missing += count
        rows.append([instrument, count])
    rows.append(["TOTAL", total_missing])
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Instrument", "Missing Day Count"])
        writer.writerows(rows)

# === Group missing day groups by instrument ===
def group_missing_days(missing_groups):
    grouped = defaultdict(list)
    for instrument, date_str in missing_groups:
        grouped[instrument].append(date_str)
    return grouped

# === Worker wrapper ===
def process_file(args):
    filename, folder_path, start_date, end_date = args
    file_path = os.path.join(folder_path, filename)
    try:
        print(f"🔍 Scanning {filename}...")
        last_rows, group_rows, table_rows = scan_hdf5(file_path, start_date, end_date)
        print(f"✅ {filename}: {len(last_rows)} updates, {len(group_rows)} missing groups, {len(table_rows)} missing tables")
        return last_rows, group_rows, table_rows
    except Exception as e:
        print(f"❌ Error scanning {filename}: {e}")
        return [], [], []

# === Main execution ===
def main():
    start_date, end_date = parse_args()

    folder_path = "2015_tick_data"
    last_update_csv = "last_tick_update.csv"
    missing_group_csv = "missing_day_group.csv"
    missing_table_csv = "missing_table.csv"
    missing_day_summary_csv = "missing_day_summary.csv"

    h5_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".h5")]
    print(f"📁 Found {len(h5_files)} HDF5 files in {folder_path}")

    all_last_updates = []
    all_missing_groups = []
    all_missing_tables = []

    with ProcessPoolExecutor(max_workers=28) as executor:
        tasks = [(f, folder_path, start_date, end_date) for f in h5_files]
        futures = [executor.submit(process_file, task) for task in tasks]

        for future in as_completed(futures):
            last_rows, group_rows, table_rows = future.result()
            all_last_updates.extend(last_rows)
            all_missing_groups.extend(group_rows)
            all_missing_tables.extend(table_rows)

    write_csv(last_update_csv, ["Instrument", "Last Good Date"], all_last_updates)
    grouped_missing = group_missing_days(all_missing_groups)
    write_grouped_csv(missing_group_csv, grouped_missing)
    write_missing_day_summary(missing_day_summary_csv, grouped_missing)
    write_csv(missing_table_csv, ["Instrument", "Missing Table Dataset"], all_missing_tables)

    print("🏁 Scan completed.")
    print(f"→ Last tick updates saved to: {last_update_csv}")
    print(f"→ Missing day groups saved to: {missing_group_csv}")
    print(f"→ Missing day summary saved to: {missing_day_summary_csv}")
    print(f"→ Missing tables saved to: {missing_table_csv}")

if __name__ == "__main__":
    main()