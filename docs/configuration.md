# Passivbot Parameters Explanation

Here follows an overview of the parameters found in `config/template.json`

## Backtest Settings
- `base_dir`: location to save backtest results
- `end_date`: end date of backtest, e.g. 2024-06-23. Set to 'now' to use today's date as end date
- `exchange`: exchange from which to fetch 1m ohlcv data. Default is Binance
- `start_date`: start date of backtest
- `starting_balance`: starting balance in USD at beginning of backtest
- `symbols`: coins to backtest. If left empty, will use all exchange's coins.

## Bot Settings
### General Parameters for Long and Short
- `ema_span_0`, `ema_span_1`: 
	- spans are given in minutes
	- `next_EMA = prev_EMA * (1 - alpha) + new_val * alpha`
	- where `alpha = 2 / (span + 1)`
	- one more EMA span is added in between span_0 and span_1:
	- `EMA_spans = [ema_span_0, (ema_span_0 * ema_span_1)**0.5, ema_span_1]`
	- these three EMAs are used to make an upper and a lower EMA band:
	- `ema_band_lower = min(emas)`
	- `ema_band_upper = max(emas)`
	- which are used for initial entries and auto unstuck closes
- `n_positions`: max number of positions to open. Set to zero to disable long/short
- `total_wallet_exposure_limit`: maximum exposure allowed.
	- E.g. total_wallet_exposure_limit = 0.75 means 75% of (unleveraged) wallet balance is used.
	- E.g. total_wallet_exposure_limit = 1.6 means 160% of (unleveraged) wallet balance is used.
	- Each position is given equal share of total exposure limit, i.e. `wallet_exposure_limit = total_wallet_exposure_limit / n_positions`.
	- See more: docs/risk_management.md

### Grid Entry Parameters
Passivbot may be configured to make a grid of entry orders, the prices and quantities of which are determined by the following parameters:
- `entry_grid_double_down_factor`:
	- quantity of next grid entry is position size times double down factor. E.g. if position size is 1.4 and double_down_factor is 0.9, then next entry quantity is `1.4 * 0.9 == 1.26`.
	- also applies to trailing entries.
- `entry_grid_spacing_pct`, `entry_grid_spacing_weight`: 
	- grid re-entry prices are determined as follows:
	- `next_reentry_price_long = pos_price * (1 - entry_grid_spacing_pct * modifier)`  
	- `next_reentry_price_short = pos_price * (1 + entry_grid_spacing_pct * modifier)`  
	- where `modifier = (1 + ratio * entry_grid_spacing_weight)`  
	- and where `ratio = wallet_exposure / wallet_exposure_limit`  
- `entry_initial_ema_dist`: 
	- offset from lower/upper ema band.  
	- long_initial_entry/short_unstuck_close prices are lower ema band minus offset  
	- short_initial_entry/long_unstuck_close prices are upper ema band plus offset  
	- See ema_span_0/ema_span_1
- `entry_initial_qty_pct`: 
	- `initial_entry_cost = balance * wallet_exposure_limit * initial_qty_pct`

### Trailing Parameters

The same logic applies to both trailing entries and trailing closes.
- `trailing_grid_ratio`: 
	- set trailing and grid allocations.
	- if `trailing_grid_ratio==0.0`, grid orders only.
	- if `trailing_grid_ratio==1.0 or trailing_grid_ratio==-1.0`, trailing orders only.
	- if `trailing_grid_ratio>0.0`, trailing orders first, then grid orders.
	- if `trailing_grid_ratio<0.0`, grid orders first, then trailing orders.
	- e.g. `trailing_grid_ratio = 0.3`: trailing orders until position is 30% full, then grid orders for the rest.
	- e.g. `trailing_grid_ratio = -0.9`: grid orders until position is (1 - 0.9) == 10% full, then trailing orders for the rest.
	- e.g. `trailing_grid_ratio = -0.12`: grid orders until position is (1 - 0.12) == 88% full, then trailing orders for the rest.
- `trailing_retracement_pct`, `trailing_threshold_pct`: 
	- there are two conditions to trigger a trailing order: 1) threshold and 2) retracement.
	- if `trailing_threshold_pct <= 0.0`, threshold condition is always triggered.
	- otherwise, the logic is as follows, considering long positions:
	- `if highest price since position open > position price * (1 + trailing_threshold_pct)`: 1st condition is met
	- and `if lowest price since highest price < highest price since position open * (1 - trailing_retracement_pct)`: 2nd condition is met. Make order.

### Grid Close Parameters
- `close_grid_markup_range`, `close_grid_min_markup`, `close_grid_qty_pct`: 
	- Take Profit (TP) prices are spread out from
		- `pos_price * (1 + min_markup)` to `pos_price * (1 + min_markup + markup_range)` for long
		- `pos_price * (1 - min_markup)` to `pos_price * (1 - min_markup - markup_range)` for short
		- e.g. if `long_pos_price==100`, `min_markup=0.01`, `markup_range=0.02` and `close_grid_qty_pct=0.2`, there is at most `1 / 0.2 == 5` TP orders, and TP prices are `[101, 101.5, 102, 102.5, 103]`.
		- qty per order is `full pos size * close_grid_qty_pct`
		- note that full pos size is when position is maxed out. If position is less than full, fewer than `1 / close_grid_qty_pct` may be created.
		- the TP grid is built from the top down:
			- first TP at 103 up to 20% of full pos size,
			- next TP at 102.5 from 20% to 40% of full pos size,
			- next TP at 102.0 from 40% to 60% of full pos size,
			- etc.
		- e.g. if `full_pos_size=100` and `long_pos_size==55`, then TP orders are `[15@102.0, 20@102.5, 20@103.0]`.
		- if position is greater than full pos size, the leftovers are added to the lowest TP order.
			- e.g. if `long_pos_size==130`, then TP orders are `[50@101.0, 20@101.5, 20@102.0, 20@102.5, 20@103.0]`

### Trailing Close Parameters

- `close_trailing_grid_ratio`: see Trailing Parameters above
- `close_trailing_qty_pct`: close qty is `full pos size * close_trailing_qty_pct`
- `close_trailing_retracement_pct`: see Trailing Parameters above
- `close_trailing_threshold_pct`: see Trailing Parameters above

### Unstuck Parameters

If a position is stuck, bot will use profits made on other positions to realize losses for the stuck position. If multiple positions are stuck, the stuck position whose price action distance is the lowest is selected for unstucking. 

- `unstuck_close_pct`:
	- percentage of `full pos size * wallet_exposure_limit` to close for each unstucking order
- `unstuck_ema_dist`:
	- distance from EMA band to place unstucking order:
	- `long_unstuck_close_price = upper_EMA_band * (1 + unstuck_ema_dist)`
	- `short_unstuck_close_price = lower_EMA_band * (1 - unstuck_ema_dist)`
- `unstuck_loss_allowance_pct`: 
	- weighted percentage below past peak balance to allow losses.
	- `loss_allowance = past_peak_balance * (1 - unstuck_loss_allowance_pct * total_wallet_exposure_limit)`
	- e.g. if past peak balance was $10,000, `unstuck_loss_allowance_pct = 0.02` and `total_wallet_exposure_limit = 1.5`, the bot will stop taking losses when balance reaches `$10,000 * (1 - 0.02 * 1.5) == $9,700`
- `unstuck_threshold`:
	- if a position is bigger than a threshold, consider it stuck and activate unstucking.
	- `if wallet_exposure / wallet_exposure_limit > unstuck_threshold: unstucking enabled`
	- e.g. if a position size is $500 and max allowed position size is $1000, then position is 50% full. If unstuck_threshold==0.45, then unstuck the position until its size is $450.  

### Filter Parameters

Coins selected for trading are filtered by volume and noisiness. First, filter coins by volume, dropping x% of the lowest volume coins, then sort the eligible coins by noisiness and select the top noisiest coins for trading.  

- `filter_relative_volume_clip_pct`: Volume filter: disapprove the lowest relative volume coins. E.g. `filter_relative_volume_clip_pct=0.1`: drop 10% lowest volume coins. Set to zero to allow all.
- `filter_rolling_window`: number of minutes to look into the past to compute volume and noisiness, used for dynamic coin selection in forager mode.
	- noisiness is normalized relative range of 1m ohlcvs: `mean((high - low) / close)`
	- in forager mode, bot will select coins with highest noisiness for opening positions

## Live Trading Settings
- `approved_coins`: list of coins approved for trading. If empty, all coins are approved.
- `auto_gs`: automatically enable graceful stop for positions on disapproved coins
	- graceful stop means the bot will continue trading as normal, but not open a new position after current position is fully closed.
- `coin_flags`:
	- Specify flags for individual coins, overriding values from bot config.
	- E.g. `coin_flags: {"ETH": "-sm n -lm gs", "XRP": "-lm p -lc path/to/other_config.json"}` will force short mode to normal, and long mode to graceful stop for ETH; will set long mode to panic and use other config for XRP.
	- Flags:
	- `-lm` or `-sm` long or short mode. Choices: [n (normal), m (manual), gs (graceful_stop), p (panic), t (take_profit_only)].
		- normal mode: passivbot manages the position as normal
		- manual mode: passivbot ignores the position
		- graceful stop: if there is a position, passivbot will manage it, otherwise passivbot will not make new positions
		- take profit only: passivbot will only manage closing orders
	- `-lw` or `-sw` long or short wallet exposure limit.
	- `-lev` leverage.
	- `-lc` path to live config. Load all of another config's bot parameters except [n_positions, total_wallet_exposure_limit, unstuck_loss_allowance_pct, unstuck_close_pct].
- `execution_delay_seconds`: wait x seconds after executing to exchange
- `filter_by_min_effective_cost`: if true, will disallow coins where balance * WE_limit * initial_qty_pct < min_effective_cost
	- e.g. if exchange's effective min cost for a coin is $5, but bot wants to make an order of $2, disallow that coin.
- `forced_mode_long`, `forced_mode_short`: force all long positions to a given mode
	- Choices: [n (normal), m (manual), gs (graceful_stop), p (panic), t (take_profit_only)].
- `ignored_coins`: list of coins bot will not make positions on. If there are positions on that coin, turn on graceful stop. May be given as a path to a json, hjson or txt file with list of coins to be ignored. If txt, each coin is on its own line.
- `leverage`: leverage set on exchange. Default 10.
- `max_n_cancellations_per_batch`: will cancel n open orders per execution
- `max_n_creations_per_batch`: will create n new orders per execution
- `minimum_coin_age_days`: disallow coins younger than a given number of days
- `pnls_max_lookback_days`: how far into the past to fetch pnl history
- `price_distance_threshold`: minimum distance to current price action required for EMA based limit orders
- `time_in_force`: default is good-till-cancelled
- `user`: fetch API key/secret from api-keys.json

## Optimization Settings
### Bounds

When optimizing, parameter values are within the lower and upper bounds.

### Other Optimization Parameters
- `crossover_probability`: The probability of performing crossover between two individuals in the genetic algorithm. It determines how often parents will exchange genetic information to create offspring.
- `iters`: number of backtests per optimize session
- `mutation_probability`: The probability of mutating an individual in the genetic algorithm. It determines how often random changes will be introduced to the population to maintain diversity.
- `n_cpus`: number of CPU cores utilized in parallel
- `population_size`: size of population for genetic optimization algorithm
- `scoring`:
	- The optimizer uses two objectives and finds the Pareto front,
	- Finally choosing the optimal candidate based on lowest Euclidean distance to the ideal point.
	- Default values are median daily gain and Sharpe ratio.
	- The script uses the NSGA-II algorithm (Non-dominated Sorting Genetic Algorithm II) for multi-objective optimization.
	- The fitness function is set up to minimize both objectives (converted to negative values internally).

### Optimization Limits

The optimizer will penalize backtests whose metrics exceed the given values.

- `lower_bound_drawdown_worst`: lowest drawdown during backtest
- `lower_bound_equity_balance_diff_mean`: mean of the difference between equity and balance
- `lower_bound_loss_profit_ratio`: `abs(sum(losses)) / sum(profit)`
