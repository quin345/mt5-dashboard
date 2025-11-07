asian = ['audusd', 'nzdusd', 'usdcnh', 'usdsgd', 'usdjpy', 
         'jpnidxjpy', 'ausidxaud', 'hkgidxhkd',]
london = ['usdjpy', 'eurusd', 'gbpusd', 'usdchf', 'usdsek', 'audusd',
          'gbridxgbp', 'deuidxeur', 'fraidxeur', 'eusidxeur']
newyork = ['eurusd', 'gbpusd', 'usdcad', 'usdzar', 'usdmxn', 'usdbrl',
           'usa500idxusd', 'usa30idxusd', 'usatechidxusd', 'ussc2000idxusd', 'volidxusd']

assets = list(set(asian + london + newyork))

print(assets)


