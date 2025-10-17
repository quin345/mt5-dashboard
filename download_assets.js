const { getHistoricalRates } = require('dukascopy-node');
const fs = require('fs');
const path = require('path');

// List of instruments to download
const instruments = ['btcusd', 'ethusd']; // Add more as needed

// Date range: from Jan 1, 2020 to today
const fromDate = new Date('2020-01-01');
const toDate = new Date(); // current date

// Timeframe: daily candles
const timeframe = 'd1';

(async () => {
  for (const instrument of instruments) {
    try {
      const data = await getHistoricalRates({
        instrument,
        dates: { from: fromDate, to: toDate },
        timeframe,
        format: 'json',
        batchSize: 15, // optional: tweak for large downloads
        pauseBetweenBatchesMs: 1000
      });

      // Extract only timestamp and close price
      const csvHeader = 'timestamp,close\n';
      const csvRows = data.map(row =>
        `${row.timestamp},${row.close}`
      );
      const csvContent = csvHeader + csvRows.join('\n');

      // Save to CSV file
      const filePath = path.join(__dirname, `${instrument}_daily_close.csv`);
      fs.writeFileSync(filePath, csvContent);
      console.log(`Saved ${instrument}_daily_close.csv`);
    } catch (error) {
      console.error(`Error fetching ${instrument}:`, error);
    }
  }
})();
