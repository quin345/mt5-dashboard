import os
import pandas as pd
import warnings
from tables import NaturalNameWarning

warnings.filterwarnings("ignore", category=NaturalNameWarning)

def store_tick_data(df: pd.DataFrame, asset: str, save_dir: str = "2015_tick_data"):
    if df.empty:
        print(f"⚠️ No data to store for {asset}")
        return

    ts = pd.to_datetime(df['timestamp'], unit='ms')
    df['year'] = ts.dt.year
    df['month'] = ts.dt.month
    df['day'] = ts.dt.day

    hdf5_path = os.path.join(save_dir, f"{asset}_tick_data.h5")
    os.makedirs(save_dir, exist_ok=True)

    with pd.HDFStore(hdf5_path, mode='a') as store:
        for (y, m, d), group in df.groupby(['year', 'month', 'day']):
            key = f"/{asset}/y{y}/m{m:02}/d{d:02}"
            if key in store:
                existing = store[key]
                combined = pd.concat([existing, group.drop(columns=['year', 'month', 'day'])])
                store.put(key, combined, format='table', data_columns=True)
            else:
                store.put(key, group.drop(columns=['year', 'month', 'day']), format='table', data_columns=True)