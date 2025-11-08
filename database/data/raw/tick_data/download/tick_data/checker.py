import h5py
from datetime import datetime
import os
import csv

# === Folder containing your .h5 files ===
folder_path = r"C:\Users\jessi\Projects\portfolio_management\database\data\raw\tick_data\download\tick_data"

# === Output CSV path ===
output_csv = os.path.join(folder_path, "hdf5_scan_report.csv")

def is_dataset_good(dset):
    try:
        _ = dset[...]  # attempt to read all data
        return True
    except:
        return False

def scan_hdf5(file_path):
    """
    Scan an HDF5 file and return a dictionary per instrument:
    {instrument_name: (last_good_date, [corrupted_days])}
    """
    instrument_report = {}

    with h5py.File(file_path, "r") as f:
        for instrument in f.keys():
            instrument_group = f[instrument]
            corrupted_days = []
            last_good_date = None

            for year_key in sorted(instrument_group.keys(), key=lambda x: int(x[1:])):
                year_group = instrument_group[year_key]
                year_num = int(year_key[1:])
                
                for month_key in sorted(year_group.keys(), key=lambda x: int(x[1:])):
                    month_group = year_group[month_key]
                    month_num = int(month_key[1:])
                    
                    for day_key in sorted(month_group.keys(), key=lambda x: int(x[1:])):
                        day_group = month_group[day_key]
                        day_num = int(day_key[1:])
                        
                        if "table" in day_group:
                            dataset = day_group["table"]
                            if is_dataset_good(dataset):
                                last_good_date = datetime(year_num, month_num, day_num)
                            else:
                                corrupted_days.append(datetime(year_num, month_num, day_num))
                        else:
                            corrupted_days.append(datetime(year_num, month_num, day_num))
            
            instrument_report[instrument] = (last_good_date, corrupted_days)
    
    return instrument_report

# === Prepare CSV file ===
with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["file_name", "instrument", "last_good_date", "corrupted_days"])

    # Loop through all .h5 files
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".h5"):
            file_path = os.path.join(folder_path, filename)
            try:
                report = scan_hdf5(file_path)
                for instrument, (last_good, corrupted) in report.items():
                    last_good_str = last_good.strftime("%Y-%m-%d") if last_good else ""
                    corrupted_str = ";".join([d.strftime("%Y-%m-%d") for d in corrupted]) if corrupted else ""
                    writer.writerow([filename, instrument, last_good_str, corrupted_str])
            except Exception as e:
                writer.writerow([filename, "ERROR", "", str(e)])

print(f"Scan completed. Results saved to {output_csv}")
