"""
optimizer.py
-------------
Efficient and clean portfolio optimization + visualization utilities.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib
import matplotlib.pyplot as plt
import logging
import os

# -------------------------------------------------------------------------
# Backend setup: auto-detect GUI availability
# -------------------------------------------------------------------------
try:
    # Try GUI backend for interactive environments
    matplotlib.use("QtAgg")
except Exception:
    # Fallback to non-GUI backend
    matplotlib.use("Agg")


# -------------------------------------------------------------------------
# 🔧 Helper: Portfolio statistics
# -------------------------------------------------------------------------
def portfolio_stats(weights, mu, cov, risk_free):
    """Compute return, volatility, and Sharpe ratio."""
    port_ret = np.dot(weights, mu)
    port_vol = np.sqrt(np.dot(weights, np.dot(cov, weights)))
    sharpe = (port_ret - risk_free) / port_vol
    return port_ret, port_vol, sharpe


# -------------------------------------------------------------------------
# 1️⃣ Max Sharpe Portfolio
# -------------------------------------------------------------------------
def max_sharpe_portfolio(mu, cov, risk_free=0.02, allow_shorts=False):
    """Optimize portfolio for maximum Sharpe ratio."""
    mu_arr, cov_arr = np.asarray(mu), np.asarray(cov)
    n = len(mu_arr)

    def neg_sharpe(w):
        ret, vol, sharpe = portfolio_stats(w, mu_arr, cov_arr, risk_free)
        return -sharpe

    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1},)
    bounds = [(-1, 1) if allow_shorts else (0, 1)] * n
    x0 = np.ones(n) / n

    opt = minimize(neg_sharpe, x0, bounds=bounds, constraints=cons, method='SLSQP')
    if not opt.success:
        logging.warning("Optimization issue: %s", opt.message)

    w = opt.x
    port_ret, port_vol, sharpe = portfolio_stats(w, mu_arr, cov_arr, risk_free)
    return pd.Series(w, index=mu.index), port_ret, port_vol, sharpe


# -------------------------------------------------------------------------
# 2️⃣ Efficient Frontier Computation
# -------------------------------------------------------------------------
def compute_efficient_frontier(mu, cov, risk_free=0.02, allow_shorts=False, num_points=100):
    """Compute efficient frontier + VaR / CVaR under normal assumptions."""
    mu_arr, cov_arr = np.asarray(mu), np.asarray(cov)
    n = len(mu_arr)
    target_returns = np.linspace(mu_arr.min(), mu_arr.max(), num_points)
    results = []

    bounds = [(-1, 1) if allow_shorts else (0, 1)] * n
    x0 = np.ones(n) / n

    for target_ret in target_returns:
        cons = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: np.dot(w, mu_arr) - target_ret},
        )

        opt = minimize(
            lambda w: np.sqrt(np.dot(w, np.dot(cov_arr, w))),
            x0, bounds=bounds, constraints=cons, method='SLSQP'
        )
        if not opt.success:
            continue

        w = opt.x
        port_ret, port_vol, sharpe = portfolio_stats(w, mu_arr, cov_arr, risk_free)

        # VaR and CVaR (95% confidence, assuming normality)
        z = 1.65
        VaR = port_ret - z * port_vol
        CVaR = port_ret - (port_vol * (np.exp(-z**2 / 2) / (np.sqrt(2 * np.pi) * 0.05)))

        results.append((port_ret, port_vol, sharpe, VaR, CVaR))

    return pd.DataFrame(results, columns=["Return", "Volatility", "Sharpe", "VaR", "CVaR"])


# -------------------------------------------------------------------------
# 3️⃣ Plot Efficient Frontier
# -------------------------------------------------------------------------
def plot_efficient_frontier(mu, cov, risk_free=0.02, allow_shorts=False, num_points=100, save_path="efficient_frontier.png"):
    """Plot efficient frontier, CML, and max Sharpe portfolio."""
    logging.info("Computing efficient frontier...")
    df = compute_efficient_frontier(mu, cov, risk_free, allow_shorts, num_points)
    if df.empty:
        logging.error("No valid optimization points found. Frontier is empty.")
        return None

    # Max Sharpe portfolio + CML
    _, ms_ret, ms_vol, ms_sharpe = max_sharpe_portfolio(mu, cov, risk_free, allow_shorts)
    cml_x = np.linspace(0, df["Volatility"].max(), 100)
    cml_y = risk_free + ms_sharpe * cml_x

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["Volatility"], df["Return"], label="Efficient Frontier", lw=2)
    ax.plot(cml_x, cml_y, '--', label="Capital Market Line (CML)", color="orange")
    ax.scatter(ms_vol, ms_ret, c='red', s=80, label="Max Sharpe Portfolio")

    ax.set(title="Efficient Frontier with Sharpe Ratio, VaR & CVaR",
           xlabel="Volatility (σ)",
           ylabel="Expected Return (μ)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()

    # Save before showing
    fig.savefig(save_path, dpi=300)
    logging.info(f"Efficient frontier plot saved as '{os.path.abspath(save_path)}'")

    try:
        plt.show(block=True)
    except Exception as e:
        logging.warning("Could not display plot window: %s", e)

    plt.close(fig)

    # --- Summary ---
    logging.info(f"Max Sharpe: Sharpe={ms_sharpe:.3f} | Return={ms_ret:.3%} | Vol={ms_vol:.3%}")
    logging.info(f"VaR(95%%): {df['VaR'].iloc[-1]:.3f} | CVaR(95%%): {df['CVaR'].iloc[-1]:.3f}")

    return df
