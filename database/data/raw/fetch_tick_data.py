import subprocess
import json
from datetime import datetime, timedelta

def fetch_tick_data_for_day(asset: str, date: datetime) -> list:
    next_date = date + timedelta(days=1)

    js_code = f"""
    const {{ getHistoricalRates }} = require('dukascopy-node');
    (async () => {{
      const fromDate = new Date(Date.UTC({date.year}, {date.month - 1}, {date.day}, 0, 0, 0));
      const toDate = new Date(Date.UTC({next_date.year}, {next_date.month - 1}, {next_date.day}, 0, 0, 0));
      try {{
        const data = await getHistoricalRates({{
          instrument: '{asset}',
          dates: {{ from: fromDate, to: toDate }},
          timeframe: 'tick',
          format: 'json',
          batchSize: 10,
          pauseBetweenBatchesMs: 500
        }});
        console.log(JSON.stringify(data));
      }} catch (error) {{
        console.error("Error:", error.message);
        process.exit(1);
      }}
    }})();"""

    try:
        result = subprocess.run(
            ['node', '-e', js_code],
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            print(f"❌ Node.js error on {date.strftime('%Y-%m-%d')}: {result.stderr.strip()}")
            return []

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout fetching data for {date.strftime('%Y-%m-%d')}")
        return []

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error on {date.strftime('%Y-%m-%d')}: {e}")
        return []