from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

# Use SMART routing to avoid ARCA restrictions
contract = Stock('GLD', 'SMART', 'USD')
order = MarketOrder('BUY', 5)

trade = ib.placeOrder(contract, order)
ib.sleep(2)
print(f"Order status: {trade.orderStatus.status}")

ib.disconnect()
