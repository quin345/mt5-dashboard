import h5py
import csv
import calendar

# Path to your HDF5 file
hdf5_path = 'audusd_tick_data.h5'  # Change this to your actual filename
csv_path = 'missing_days_report.csv'
report_rows = []

with h5py.File(hdf5_path, 'r') as f:
    for symbol in f.keys():  # e.g., 'audusd', 'eurusd'
        for year_str in f[symbol].keys():
            if not year_str.startswith('y'):
                continue
            year = int(year_str[1:])
            for month_str in f[symbol][year_str].keys():
                if not month_str.startswith('m'):
                    continue
                month = int(month_str[1:])
                num_days = calendar.monthrange(year, month)[1]
                for day in range(1, num_days + 1):
                    day_str = f'd{str(day).zfill(2)}'
                    date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    day_path = f"{symbol}/{year_str}/{month_str}/{day_str}"
                    missing_group = ''
                    missing_table = ''
                    try:
                        group = f[day_path]
                        if 'table' not in group:
                            missing_table = date_str
                    except KeyError:
                        missing_group = date_str
                    if missing_group or missing_table:
                        report_rows.append([symbol, missing_group, missing_table])

# Write report to CSV
with open(csv_path, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Symbol', 'Missing Day Group (yyyy-mm-dd)', 'Missing Table (yyyy-mm-dd)'])
    writer.writerows(report_rows)

print(f"✅ Missing days report saved to: {csv_path}")
