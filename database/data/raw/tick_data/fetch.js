const { getHistoricalRates } = require('dukascopy-node');
const fs = require('fs');
const path = require('path');

// Define asset groups
const asian = ['audusd', 'nzdusd', 'usdcnh', 'usdsgd', 'usdjpy', 'jpnidxjpy', 'ausidxaud', 'hkgidxhkd'];
const london = ['usdjpy', 'eurusd', 'gbpusd', 'usdchf', 'usdsek', 'audusd', 'gbridxgbp', 'deuidxeur', 'fraidxeur', 'eusidxeur'];
const newyork = ['eurusd', 'gbpusd', 'usdcad', 'usdzar', 'usdmxn', 'usa500idxusd', 'usa30idxusd', 'usatechidxusd', 'ussc2000idxusd', 'volidxusd'];

// Combine and deduplicate
const assets = [...new Set([...asian, ...london, ...newyork])];

// Time range: past 24 hours
const fromDate = new Date(Date.UTC(2025, 10, 5, 14, 0, 0)); // Nov 5, 2025, 14:00 UTC
const toDate = new Date(Date.UTC(2025, 10, 5, 15, 0, 0));   // Nov 5, 2025, 15:00 UTC

(async () => {
  for (const instrument of assets) {
    try {
      const data = await getHistoricalRates({
        instrument,
        dates: { from: fromDate, to: toDate },
        timeframe: 'tick',
        format: 'json',
        batchSize: 10,
        pauseBetweenBatchesMs: 500
      });

      // Save tick data to file
      const filePath = path.join(__dirname, `${instrument}_tick.json`);
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
      console.log(`Saved ${instrument}_tick.json`);
    } catch (error) {
      console.error(`Error fetching ${instrument}:`, error);
    }
  }
})();
