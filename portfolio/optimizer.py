"""
optimizer.py
-------------
Optimization functions for portfolio construction.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging

def max_sharpe_portfolio(mu, cov, risk_free, allow_shorts=False):
    """Solve for weights maximizing Sharpe ratio."""
    mu_arr, cov_arr = np.asarray(mu), np.asarray(cov)
    n = len(mu)
    rf = risk_free

    def neg_sharpe(w):
        port_ret = np.dot(w, mu_arr)
        port_vol = np.sqrt(max(1e-12, np.dot(w, np.dot(cov_arr, w))))
        return -(port_ret - rf) / port_vol

    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1},)
    bnds = [(-1, 1) if allow_shorts else (0, 1)] * n
    x0 = np.ones(n) / n

    opt = minimize(neg_sharpe, x0=x0, bounds=bnds, constraints=cons, method='SLSQP')
    if not opt.success:
        logging.warning("Optimization warning: %s", opt.message)

    w = opt.x
    port_ret, port_vol = np.dot(w, mu_arr), np.sqrt(np.dot(w, np.dot(cov_arr, w)))
    sharpe = (port_ret - rf) / port_vol
    return pd.Series(w, index=mu.index), port_ret, port_vol, sharpe
