"""
portfolio_math.py
-----------------
Computes log returns, annualized mean returns, and covariance matrices.
Ensures consistent scaling for use in portfolio optimization.
"""

import numpy as np
import pandas as pd

def compute_returns_and_stats(price_panel, freq_per_year=252):
    """
    Compute log returns, mean, and covariance (annualized).

    Parameters
    ----------
    price_panel : pd.DataFrame
        Historical price data (columns = assets, index = dates).
    freq_per_year : int, optional
        Number of periods per year (252 for daily, 52 for weekly).

    Returns
    -------
    ret : pd.DataFrame
        Log returns (daily).
    mu_annual : pd.Series
        Annualized mean returns.
    cov_annual : pd.DataFrame
        Annualized covariance matrix.
    """
    # Compute log returns
    ret = np.log(price_panel).diff().dropna()

    # Daily statistics
    mu_daily = ret.mean()
    cov_daily = ret.cov()

    # Annualized statistics (multiply mean by freq, covariance by freq)
    mu_annual = mu_daily * freq_per_year
    cov_annual = cov_daily * freq_per_year

    return ret, mu_annual, cov_annual
