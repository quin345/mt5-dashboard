"""
portfolio_math.py
-----------------
Computes log returns, annualized means, and covariance matrices.
"""

import numpy as np
import pandas as pd

def compute_returns_and_stats(price_panel, freq_per_year=252):
    """Compute log returns, mean, and covariance (annualized)."""
    ret = np.log(price_panel).diff().dropna()
    mu_daily, cov_daily = ret.mean(), ret.cov()
    return ret, mu_daily * freq_per_year, cov_daily * freq_per_year
