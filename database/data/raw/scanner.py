import h5py
from datetime import datetime
import os
import csv
import calendar

# === Use current working directory ===
folder_path = "\tick_data"  # Adjust if needed

# === Output CSV paths ===
last_update_csv = os.path.join(folder_path, "last_tick_update.csv")
missing_group_csv = os.path.join(folder_path, "missing_day_group.csv")
missing_table_csv = os.path.join(folder_path, "missing_table.csv")

def is_dataset_good(dset):
    try:
        _ = dset[...]  # attempt to read all data
        return True
    except Exception:
        return False

def scan_hdf5(file_path):
    """
    Scan an HDF5 file and return:
    - last good date per instrument
    - list of missing day groups
    - list of missing tables
    """
    last_updates = []
    missing_groups = []
    missing_tables = []

    with h5py.File(file_path, "r") as f:
        for instrument in f.keys():
            last_good_date = None

            for year_key in sorted(f[instrument].keys(), key=lambda x: int(x[1:])):
                year_num = int(year_key[1:])
                year_group = f[instrument][year_key]

                for month_key in sorted(year_group.keys(), key=lambda x: int(x[1:])):
                    month_num = int(month_key[1:])
                    month_group = year_group[month_key]
                    num_days = calendar.monthrange(year_num, month_num)[1]

                    for day_num in range(1, num_days + 1):
                        day_key = f'd{str(day_num).zfill(2)}'
                        date_str = f"{year_num}-{str(month_num).zfill(2)}-{str(day_num).zfill(2)}"
                        try:
                            day_group = month_group[day_key]
                            if "table" in day_group:
                                dataset = day_group["table"]
                                if is_dataset_good(dataset):
                                    last_good_date = date_str
                                else:
                                    missing_tables.append([instrument, date_str])
                                    return last_updates, missing_groups, missing_tables
                            else:
                                missing_tables.append([instrument, date_str])
                                return last_updates, missing_groups, missing_tables
                        except KeyError:
                            missing_groups.append([instrument, date_str])
                            return last_updates, missing_groups, missing_tables

            if last_good_date:
                last_updates.append([instrument, last_good_date])

    return last_updates, missing_groups, missing_tables

# === Prepare CSV writers ===
with open(last_update_csv, "w", newline="", encoding="utf-8") as last_file, \
     open(missing_group_csv, "w", newline="", encoding="utf-8") as group_file, \
     open(missing_table_csv, "w", newline="", encoding="utf-8") as table_file:

    last_writer = csv.writer(last_file)
    group_writer = csv.writer(group_file)
    table_writer = csv.writer(table_file)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".h5"):
            file_path = os.path.join(folder_path, filename)
            try:
                last_rows, group_rows, table_rows = scan_hdf5(file_path)
                last_writer.writerows(last_rows)
                group_writer.writerows(group_rows)
                table_writer.writerows(table_rows)
            except Exception as e:
                print(f"Error scanning {filename}: {e}")

print("✅ Scan completed.")
print(f"→ Last tick updates saved to: {last_update_csv}")
print(f"→ Missing day groups saved to: {missing_group_csv}")
print(f"→ Missing tables saved to: {missing_table_csv}")
