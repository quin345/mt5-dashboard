import os
import pandas as pd
import warnings
from tables import NaturalNameWarning

warnings.filterwarnings("ignore", category=NaturalNameWarning)

def store_tick_data(df: pd.DataFrame, asset: str, save_dir: str):
    ts = pd.to_datetime(df['timestamp'], unit='ms')
    df['year'] = ts.dt.year
    df['month'] = ts.dt.month
    df['day'] = ts.dt.day

    hdf5_path = os.path.join(save_dir, f"{asset}_tick_data.h5")
    os.makedirs(save_dir, exist_ok=True)

    with pd.HDFStore(hdf5_path, mode='a') as store:
        for (y, m, d), group in df.groupby(['year', 'month', 'day']):
            key = f"/{asset}/y{y}/m{m:02}/d{d:02}"
            store.put(key, group.drop(columns=['year', 'month', 'day']), format='table', data_columns=True)