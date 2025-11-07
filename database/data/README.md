Currency pairs are normalized to USD/unit currency

needed to convert non USD fx pairs to USD
need to convert non USD equities to USD



UPDATE assets SET currency = 'USD' WHERE asset_id IN (
  
  ''usdcad', 'usdchf',
  'usdcnh', 'usddkk', 'usdhkd', 'usdhuf', 'usdjpy', 'usdmxn','usdnok',
  'usdsek', 'usdsgd', 'usdzar'
);