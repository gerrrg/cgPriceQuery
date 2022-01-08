# cgPriceQuery
cgPriceQuery is an abstraction layer for calling the CoinGecko Price Query API. Since the densest data from CoinGecko is typically returned hourly, this package interpolates prices to each block time.

## Query types
* `queryPricesInDuration`: Get price data at each block time from time `t_0` to `t_1`
* `queryPriceAtTime`: Get price data at time `t` 
* `queryPriceCurrent`: Get the current price

## Networks
Supported networks are currently:
* ethereum
* polygon
* arbitrum
* fantom

Additional networks are pretty trivial to add as long as they have a subgraph for block times and CoinGecko price feeds.

# Sample
For a sample, see `samples/sample.py`
