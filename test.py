import MetaTrader5 as mt5
from collections import defaultdict
import csv

# 🔧 Initialize MT5 connection
def initialize_mt5():
    if not mt5.initialize():
        print("MT5 initialization failed:", mt5.last_error())
        return False
    return True

# 📥 Fetch open positions
def fetch_positions():
    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        print("No open positions or error occurred:", mt5.last_error())
        return None
    return positions

# 💱 Get conversion rate to USD
def get_conversion_rate(symbol, currency):
    if currency == "USD":
        return 1.0

    if symbol.startswith("USD"):
        tick = mt5.symbol_info_tick(symbol)
        return 1 / tick.ask if tick else 0.0

    if currency == "ZAR":
        tick = mt5.symbol_info_tick("USDZAR")
        return 1 / tick.ask if tick else 0.0
    
    if currency == "EUR":
        tick = mt5.symbol_info_tick("EURUSD")
        return tick.ask if tick else 0.0

    conversion_symbol = f"USD{currency}"
    tick = mt5.symbol_info_tick(conversion_symbol)
    return 1 / tick.ask if tick else 0.0

# 📊 Process and aggregate position data
def process_positions(positions):
    data = defaultdict(lambda: {
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

    total_exposure = 0.0

    for pos in positions:
        symbol = pos.symbol
        lot_size = pos.volume
        direction = pos.type

        symbol_info = mt5.symbol_info(symbol)
        tick_info = mt5.symbol_info_tick(symbol)

        if symbol_info is None or tick_info is None:
            print(f"Missing data for {symbol}")
            continue

        contract_size = symbol_info.trade_contract_size
        profit_currency = symbol_info.currency_profit
        price = tick_info.ask if direction == mt5.ORDER_TYPE_BUY else tick_info.bid
        exposure = lot_size * contract_size * price
        total_volume = contract_size * lot_size

        conversion_rate = get_conversion_rate(symbol, profit_currency)
        gross_usd = abs(exposure) * conversion_rate

        stats = data[symbol]
        stats["exposure"] += exposure if direction == mt5.ORDER_TYPE_BUY else -exposure
        stats["volume"] += total_volume
        stats["lot"] += lot_size
        stats["contract_size"] = contract_size
        stats["price"] = price
        stats["currency"] = profit_currency
        stats["vwap_accum"] += pos.price_open * total_volume
        stats["conversion_rate"] = conversion_rate
        stats["gross_usd"] += gross_usd

        total_exposure += abs(exposure)

    return data, total_exposure

# 📤 Display and export to CSV
def display_and_export(data, total_exposure, filename="positions_summary.csv"):
    headers = [
        "Symbol", "Currency", "Exposure", "Total Volume", "Lot Size",
        "Contract Size", "Last Price", "VWAP Price", "Weight (%)", "Gross Exposure (USD)"
    ]
    print("\t".join(headers))

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for symbol, stats in data.items():
            exposure = stats["exposure"]
            volume = stats["volume"]
            lot = stats["lot"]
            contract_size = stats["contract_size"]
            price = stats["price"]
            currency = stats["currency"]
            vwap_price = stats["vwap_accum"] / volume if volume != 0 else 0.0
            weight = (abs(exposure) / total_exposure) * 100 if total_exposure != 0 else 0.0
            gross_usd = stats["gross_usd"]

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
            print("\t".join(row))
            writer.writerow(row)

# 🚀 Main execution
def main():
    if not initialize_mt5():
        return

    positions = fetch_positions()
    if positions is None:
        mt5.shutdown()
        return

    data, total_exposure = process_positions(positions)
    display_and_export(data, total_exposure)

    mt5.shutdown()

if __name__ == "__main__":
    main()
