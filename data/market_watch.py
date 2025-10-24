# save as mt5_market_watch_summary.py
import MetaTrader5 as mt5
import pandas as pd
import os
import textwrap

# ---------- Connect to MetaTrader5 ----------
if not mt5.initialize():
    raise RuntimeError("Failed to initialize MT5 connection")

# ---------- Fetch visible symbols from Market Watch ----------
symbols = mt5.symbols_get()
if not symbols:
    print("No symbols found.")
    mt5.shutdown()
    exit()

# Filter only visible symbols
visible_symbols = [s for s in symbols if s.visible]

# ---------- Build DataFrame ----------
df = pd.DataFrame([{
    "symbol": s.name,
    "description": s.description,
    "path": s.path,
    "spread": s.spread,
    "digits": s.digits,
    "trade_mode": s.trade_mode,
    "select": s.select,
    "visible": s.visible
} for s in visible_symbols])

# ---------- Output ----------
print(df.to_string(index=False))

# ---------- Save to CSV ----------
output_file = os.path.join(os.getcwd(), "market_watch_symbols.csv")
df.to_csv(output_file, index=False)

# ---------- Format JS-style instrument list ----------
instruments_list = [f"'{s.name.lower()}'" for s in visible_symbols]

# Break into lines of 4 instruments each
chunked_lines = textwrap.wrap(', '.join(instruments_list), width=80)

# Build the footer block
footer_lines = ['const instruments = [']
footer_lines += [f'  {line},' for line in chunked_lines[:-1]]
footer_lines += [f'  {chunked_lines[-1]}']
footer_lines += ['];\n']

# ---------- Append to CSV ----------
with open(output_file, "a", encoding="utf-8") as f:
    f.write('\n' + '\n'.join(footer_lines))

print(f"\nCSV file saved to: {output_file}")

# ---------- Clean up ----------
mt5.shutdown()
