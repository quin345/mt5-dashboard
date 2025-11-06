import os
import glob

# Set the target folder
folder_path = 'C:/Users/jessi/OneDrive/Projects/portfolio_management/database/data/raw/tick_data/download'

# Find all .json files in the folder
json_files = glob.glob(os.path.join(folder_path, '*.json'))

# Delete each file
for file_path in json_files:
    try:
        os.remove(file_path)
        print(f"Deleted: {file_path}")
    except Exception as e:
        print(f"Error deleting {file_path}: {e}")
