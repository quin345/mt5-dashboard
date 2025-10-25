import sqlite3

# Paths to your databases
source_db = "market_data.db"
dest_db = "database.sqlite"

# Connect to both databases
src_conn = sqlite3.connect(source_db)
dest_conn = sqlite3.connect(dest_db)

src_cur = src_conn.cursor()
dest_cur = dest_conn.cursor()

# Get all column names from source table
src_cur.execute("PRAGMA table_info(daily_prices)")
columns = [row[1] for row in src_cur.fetchall()]
asset_columns = [col for col in columns if col.lower() != "timestamp"]

# Read all rows from source
src_cur.execute("SELECT * FROM daily_prices")
rows = src_cur.fetchall()

# Insert each asset's price into the normalized prices table
for row in rows:
    timestamp = row[0]
    for i, asset_id in enumerate(asset_columns, start=1):
        close = row[i]
        if close is not None:
            dest_cur.execute(
                "INSERT INTO prices (date, asset_id, close) VALUES (?, ?, ?)",
                (timestamp, asset_id, close)
            )

# Commit and close
dest_conn.commit()
src_conn.close()
dest_conn.close()

print("✅ Prices successfully migrated.")
