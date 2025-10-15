"""
io_utils.py
-----------
Handles Excel output and formatted results for portfolio data.
"""

import pandas as pd
import logging

def save_results(filename, price_panel, returns, mu, cov, results):
    """Save all outputs into Excel."""
    with pd.ExcelWriter(filename) as writer:
        price_panel.to_excel(writer, sheet_name='USD_Prices')
        returns.to_excel(writer, sheet_name='Log_Returns')
        mu.to_frame('mu_annual').to_excel(writer, sheet_name='Mu_Annual')
        cov.to_excel(writer, sheet_name='Cov_Annual')
        results.to_excel(writer, sheet_name='MaxSharpe_Portfolio')
    logging.info("Results saved to %s", filename)
