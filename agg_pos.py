import MetaTrader5 as mt5
from collections import defaultdict
import csv

def initialize_mt5():
    if not mt5.initialize():
        print("MT5 initialization failed:", mt5.last_error())
        return False
    return True

def fetch_positions():
    positions = mt5.positions_get()
    if not positions:
        print("No open positions or error occurred:", mt5.last_error())
        return None
    return positions

def get_conversion_rate(symbol, currency):
    if currency == "USD":
        return 1.0

    conversion_map = {
        "ZAR": "USDZAR",
        "EUR": "EURUSD"
    }

    conversion_symbol = conversion_map.get(currency, f"USD{currency}")
    tick = mt5.symbol_info_tick(conversion_symbol)

    if not tick:
        return 0.0

    return tick.ask if currency == "EUR" else 1 / tick.ask

def process_positions(positions):
    summary = defaultdict(lambda: {
        "exposure": 0.0,
        "volume": 0.0,
        "lot": 0.0,
        "contract_size": 0.0,
        "price": 0.0,
        "currency": "",
        "vwap_accum": 0.0,
        "conversion_rate": 1.0,
        "gross_usd": 0.0
    })

    total_gross_usd = 0.0

    for pos in positions:
        symbol = pos.symbol
        lot_size = pos.volume
        direction = pos.type

        symbol_info = mt5.symbol_info(symbol)
        tick_info = mt5.symbol_info_tick(symbol)

        if not symbol_info or not tick_info:
            print(f"Missing data for {symbol}")
            continue

        contract_size = symbol_info.trade_contract_size
        profit_currency = symbol_info.currency_profit
        price = tick_info.ask if direction == mt5.ORDER_TYPE_BUY else tick_info.bid
        exposure = lot_size * contract_size * price
        volume = contract_size * lot_size

        conversion_rate = get_conversion_rate(symbol, profit_currency)
        gross_usd = abs(exposure) * conversion_rate

        stats = summary[symbol]
        stats["exposure"] += exposure if direction == mt5.ORDER_TYPE_BUY else -exposure
        stats["volume"] += volume
        stats["lot"] += lot_size
        stats["contract_size"] = contract_size
        stats["price"] = price
        stats["currency"] = profit_currency
        stats["vwap_accum"] += pos.price_open * volume
        stats["conversion_rate"] = conversion_rate
        stats["gross_usd"] += gross_usd

        total_gross_usd += gross_usd

    return summary, total_gross_usd

def display_and_export(summary, total_gross_usd, filename="positions_summary.csv"):
    headers = [
        "Symbol", "Currency", "Exposure", "Total Volume", "Lot Size",
        "Contract Size", "Last Price", "VWAP Price", "Weight (%)", "Gross Exposure (USD)"
    ]

    # Define column widths
    col_widths = [12, 10, 15, 14, 10, 14, 12, 12, 12, 20]

    # Format header
    header_row = "".join(f"{h:<{w}}" for h, w in zip(headers, col_widths))
    print(header_row)

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for symbol, stats in summary.items():
            exposure = stats["exposure"]
            volume = stats["volume"]
            lot = stats["lot"]
            contract_size = stats["contract_size"]
            price = stats["price"]
            currency = stats["currency"]
            vwap_price = stats["vwap_accum"] / volume if volume else 0.0
            gross_usd = stats["gross_usd"]
            weight = (gross_usd / total_gross_usd) * 100 if total_gross_usd else 0.0

            row = [
                symbol,
                currency,
                f"{exposure:,.2f}",
                f"{volume:.0f}",
                f"{lot:.2f}",
                f"{contract_size:.0f}",
                f"{price:,.2f}",
                f"{vwap_price:,.2f}",
                f"{weight:.2f}",
                f"{gross_usd:,.2f}"
            ]

            # Print aligned row
            print("".join(f"{val:<{w}}" for val, w in zip(row, col_widths)))
            writer.writerow(row)

def main():
    if not initialize_mt5():
        return

    positions = fetch_positions()
    if positions is None:
        mt5.shutdown()
        return

    summary, total_gross_usd = process_positions(positions)
    display_and_export(summary, total_gross_usd)

    mt5.shutdown()

if __name__ == "__main__":
    main()
