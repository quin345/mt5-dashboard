# factor_pipeline.py
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from scipy.optimize import minimize

# 1. DATA -----------------------------------------------------------------
tickers = ['AUDUSD=X','EURUSD=X','GBPUSD=X','NZDUSD=X','USDCAD=X','USDCHF=X','USDJPY=X',
           'XAUUSD=X','XAGUSD=X','UKOUSD=X','USOUSD=X',
           '^AORD','^STOXX50E','^FCHI','^GDAXI','^HSI','^N225','^NDX','^AEX','^GSPC','^SSMI','^FTSE','^RUT','^DJI']
factors = ['^GSPC','DX-Y.NYB','^VIX','^TNX']          # market, USD, vol, rates
data = yf.download(tickers + factors, period='2y')['Close'].pct_change().dropna()

# 2. TIME-SERIES REGRESSIONS → B matrix -----------------------------------
B = pd.DataFrame(index=tickers, columns=[f'beta_{f}' for f in factors])
alpha = pd.Series(index=tickers)

for asset in tickers:
    df = data[[asset] + factors].dropna()
    formula = f"{asset} ~ {' + '.join(factors)}"
    res = smf.ols(formula, df).fit()
    alpha[asset] = res.params['Intercept']
    B.loc[asset] = res.params[1:].values

B = B.astype(float)
alpha = alpha.astype(float)

# 3. FACTOR FORECASTS (next 12m) -------------------------------------------
E_f = pd.Series({
    '^GSPC': 0.11,      # 11 % equity premium
    'DX-Y.NYB': -0.06,  # USD weakens 6 %
    '^VIX': 15,         # level
    '^TNX': 4.25        # level
})
# convert levels to daily returns where needed
E_f['^GSPC'] = (1 + E_f['^GSPC'])**(1/252) - 1
E_f['DX-Y.NYB'] = (1 + E_f['DX-Y.NYB'])**(1/252) - 1

# 4. EXPECTED RETURNS ------------------------------------------------------
mu = alpha + B @ E_f.values
mu_annual = (1 + mu)**252 - 1

# 5. COVARIANCE -----------------------------------------------------------
Omega_f = data[factors].cov() * 252
Psi = np.diag(data[tickers].var() * 252) - np.diag((B @ Omega_f @ B.T).values)
Sigma = B @ Omega_f @ B.T + pd.DataFrame(Psi, index=tickers, columns=tickers)

# 6. BLACK-LITTERMAN (one view: USD weakens 6 %) -------------------------
P = np.zeros((1, len(factors))); P[0,1] = 1          # view on USD factor
Q = np.array([[-0.06]])                             # 6 % weakening
tau = 0.05
Omega_view = np.array([[0.01**2]])                   # confidence

# posterior
invSigma = np.linalg.inv(Sigma.values)
post = np.linalg.inv( (tau*invSigma) + P.T @ np.linalg.inv(Omega_view) @ P ) @ \
       ( (tau*invSigma) @ mu_annual.values + P.T @ np.linalg.inv(Omega_view) @ Q )
mu_BL = pd.Series(post.flatten(), index=tickers)

# 7. RISK-PARITY WEIGHTS (daily vol ≤4 %) --------------------------------
def portfolio_vol(w): 
    return np.sqrt(w @ Sigma.values @ w) * np.sqrt(252) / np.sqrt(252)  # daily
cons = [{'type':'eq', 'fun':lambda w: w.sum()-1},
        {'type':'ineq','fun':lambda w: 0.04 - portfolio_vol(w)}]
bnds = [(0,0.4) for _ in tickers]
res = minimize(lambda w: -w @ mu_BL.values, 
               x0=np.ones(len(tickers))/len(tickers),
               bounds=bnds, constraints=cons, method='SLSQP')
weights = pd.Series(res.x, index=tickers)

print("=== PORTFOLIO ===")
print(f"Expected annual return : {weights @ mu_BL*100:5.2f}%")
print(f"Daily volatility       : {portfolio_vol(weights)*100:5.2f}%")
print(weights.round(3))