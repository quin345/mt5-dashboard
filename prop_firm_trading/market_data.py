import pandas as pd, numpy as np, yfinance as yf, warnings
warnings.filterwarnings('ignore')

tickers = ['EURUSD=X', '^GSPC', 'GC=F']
data = yf.download(tickers, start='2015-01-01', end='2025-11-03')

# Use 'Adj Close' if available, otherwise fallback to 'Close'
if 'Adj Close' in data.columns:
    prices = data['Adj Close']
else:
    prices = data['Close']

prices.columns = ['EURUSD', 'SPX', 'GOLD']
rets = np.log(prices).diff().dropna()
print(rets.tail(3))