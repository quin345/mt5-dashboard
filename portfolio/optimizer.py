"""
optimizer.py
-------------
Efficient and clean portfolio optimization + visualization utilities.
Consistent with annualized statistics from portfolio_math.py.
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
    matplotlib.use("QtAgg")
except Exception:
    matplotlib.use("Agg")


# -------------------------------------------------------------------------
# 🔧 Helper: Portfolio statistics
# -------------------------------------------------------------------------
def portfolio_stats(weights, mu, cov, risk_free):
    """
    Compute portfolio return, volatility, and Sharpe ratio.

    All inputs are assumed to be ANNUALIZED (consistent units).
    """
    weights = np.asarray(weights)
    mu = np.asarray(mu)
    cov = np.asarray(cov)

    port_ret = np.dot(weights, mu)
    port_vol = np.sqrt(np.dot(weights, np.dot(cov, weights)))
    sharpe = (port_ret - risk_free) / port_vol
    return port_ret, port_vol, sharpe


# -------------------------------------------------------------------------
# 1️⃣ Max Sharpe Portfolio
# -------------------------------------------------------------------------
def max_sharpe_portfolio(mu, cov, risk_free=0.02, allow_shorts=False):
    """Optimize portfolio for maximum Sharpe ratio."""
    mu_arr = np.asarray(mu)
    cov_arr = np.asarray(cov)
    n = len(mu_arr)

    def neg_sharpe(w):
        return -portfolio_stats(w, mu_arr, cov_arr, risk_free)[2]

    bounds = [(-1, 1) if allow_shorts else (0, 1)] * n
    cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1},)
    x0 = np.ones(n) / n

    opt = minimize(neg_sharpe, x0, bounds=bounds, constraints=cons, method='SLSQP')
    if not opt.success:
        logging.warning("Optimization issue: %s", opt.message)

    w = opt.x
    port_ret, port_vol, sharpe = portfolio_stats(w, mu_arr, cov_arr, risk_free)
    return pd.Series(w, index=mu.index), port_ret, port_vol, sharpe


# -------------------------------------------------------------------------
# 2️⃣ Efficient Frontier
# -------------------------------------------------------------------------
def compute_efficient_frontier(mu, cov, risk_free=0.02, allow_shorts=False, num_points=100):
    """
    Compute efficient frontier + VaR/CVaR (normal assumption).

    Returns a DataFrame with annualized portfolio metrics.
    VaR and CVaR are expressed as *negative losses* (e.g., -0.20 = -20% loss).
    """
    mu_arr = np.asarray(mu)
    cov_arr = np.asarray(cov)
    n = len(mu_arr)
    target_returns = np.linspace(mu_arr.min(), mu_arr.max(), num_points)
    results = []

    bounds = [(-1, 1) if allow_shorts else (0, 1)] * n
    x0 = np.ones(n) / n
    z = 1.65  # 95% confidence level

    for target_ret in target_returns:
        cons = (
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: np.dot(w, mu_arr) - target_ret},
        )
        opt = minimize(lambda w: np.sqrt(np.dot(w, np.dot(cov_arr, w))),
                       x0, bounds=bounds, constraints=cons, method='SLSQP')
        if not opt.success:
            continue

        w = opt.x
        port_ret, port_vol, sharpe = portfolio_stats(w, mu_arr, cov_arr, risk_free)

        # ✅ VaR & CVaR as LOSS values (negative convention)
        VaR = -(z * port_vol - port_ret)
        CVaR = -((port_vol * (np.exp(-z**2 / 2) /
                              (np.sqrt(2 * np.pi) * 0.05))) - port_ret)

        results.append((port_ret, port_vol, sharpe, VaR, CVaR))

    return pd.DataFrame(results, columns=["Return", "Volatility", "Sharpe", "VaR", "CVaR"])


# -------------------------------------------------------------------------
# 3️⃣ Plot Efficient Frontier with Metrics
# -------------------------------------------------------------------------
def plot_efficient_frontier(mu, cov, risk_free=0.02, allow_shorts=False,
                            num_points=100, save_path="efficient_frontier.png"):
    """Plot efficient frontier, CML, max Sharpe portfolio, and key metrics."""
    df = compute_efficient_frontier(mu, cov, risk_free, allow_shorts, num_points)
    if df.empty:
        logging.error("No valid optimization points found.")
        return None

    # Max Sharpe Portfolio
    _, ms_ret, ms_vol, ms_sharpe = max_sharpe_portfolio(mu, cov, risk_free, allow_shorts)
    z = 1.65
    ms_VaR = -(z * ms_vol - ms_ret)
    ms_CVaR = -((ms_vol * (np.exp(-z**2 / 2) / (np.sqrt(2 * np.pi) * 0.05))) - ms_ret)

    # Capital Market Line
    cml_x = np.linspace(0, df["Volatility"].max(), 100)
    cml_y = risk_free + ms_sharpe * cml_x

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["Volatility"], df["Return"], lw=2, label="Efficient Frontier")
    ax.plot(cml_x, cml_y, '--', color="orange", label="CML")
    ax.scatter(ms_vol, ms_ret, color='red', s=80, label="Max Sharpe Portfolio")

    # ✅ Annotate metrics for Max Sharpe (losses shown as negatives)
    metrics_text = (f"Sharpe={ms_sharpe:.3f}\n"
                    f"Return={ms_ret:.3%}\n"
                    f"Vol={ms_vol:.3%}\n"
                    f"VaR(95%)={-abs(ms_VaR):.3%}\n"
                    f"CVaR(95%)={-abs(ms_CVaR):.3%}")
    ax.annotate(metrics_text, xy=(ms_vol, ms_ret),
                xytext=(ms_vol + 0.02, ms_ret - 0.02),
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.3),
                arrowprops=dict(arrowstyle="->", color="black"))

    ax.set(title="Efficient Frontier with Metrics",
           xlabel="Volatility (σ)",
           ylabel="Expected Return (μ)")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()

    # ✅ Save and log clean metrics
    fig.savefig(save_path, dpi=300)
    logging.info(f"Plot saved: {os.path.abspath(save_path)}")
    logging.info(
        f"Max Sharpe Metrics: Sharpe={ms_sharpe:.3f} | "
        f"Return={ms_ret:.3%} | Vol={ms_vol:.3%} | "
        f"VaR(95%) Loss={-abs(ms_VaR):.3%} | CVaR(95%) Loss={-abs(ms_CVaR):.3%}"
    )

    try:
        plt.show(block=True)
    except Exception as e:
        logging.warning("Plot display failed: %s", e)
    plt.close(fig)

    return df
