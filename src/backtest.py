import numpy as np
import pandas as pd
import os
import json
import passivbot_rust as pbr
import asyncio
import argparse
from procedures import (
    utc_ms,
    make_get_filepath,
    fetch_market_specific_settings_multi,
    load_config,
    dump_config,
    coin_to_symbol,
    add_arguments_recursively,
    update_config_with_args,
    format_config,
    format_end_date,
)
from pure_funcs import (
    get_template_live_config,
    ts_to_date,
    sort_dict_keys,
    calc_hash,
)
import pprint
from copy import deepcopy
from downloader import prepare_hlcvs, prepare_hlcvs_combined, add_all_eligible_coins_to_config
from pathlib import Path
from plotting import plot_fills_forager
from collections import defaultdict
import matplotlib.pyplot as plt
import logging
from main import manage_rust_compilation
import gzip
import traceback

import tempfile
from contextlib import contextmanager

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
)


@contextmanager
def create_shared_memory_file(hlcvs):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    shared_memory_file = temp_file.name
    try:
        with open(shared_memory_file, "wb") as f:
            f.write(hlcvs.tobytes())
        yield shared_memory_file
    finally:
        os.unlink(shared_memory_file)


plt.rcParams["figure.figsize"] = [29, 18]


def oj(*x):
    return os.path.join(*x)


def process_forager_fills(fills):
    fdf = pd.DataFrame(
        fills,
        columns=[
            "minute",
            "coin",
            "pnl",
            "fee_paid",
            "balance",
            "qty",
            "price",
            "psize",
            "pprice",
            "type",
        ],
    )
    return fdf


def analyze_fills_forager(coins, hlcvs, fdf, equities):
    analysis = {}
    pnls = {}
    for pside in ["long", "short"]:
        fdfc = fdf[fdf.type.str.contains(pside)]
        profit = fdfc[fdfc.pnl > 0.0].pnl.sum()
        loss = fdfc[fdfc.pnl < 0.0].pnl.sum()
        if len(fdfc) == 0:
            pnls[pside] = 0.0
            analysis[f"loss_profit_ratio_{pside}"] = 1.0
            continue
        pnls[pside] = profit + loss
        analysis[f"loss_profit_ratio_{pside}"] = abs(loss / profit)

    div_by = 60  # save some disk space. Set to 1 to dump uncropped
    analysis["pnl_ratio_long_short"] = pnls["long"] / (pnls["long"] + pnls["short"])
    bdf = fdf.groupby((fdf.minute // div_by) * div_by).balance.last()
    edf = equities.iloc[::div_by]
    nidx = np.arange(min(bdf.index[0], edf.index[0]), max(bdf.index[-1], edf.index[-1]), div_by)
    bal_eq = pd.DataFrame({"balance": bdf, "equity": edf}, index=nidx).astype(float).ffill().bfill()
    return sort_dict_keys(analysis), bal_eq


def compare_dicts(dict1, dict2, path=""):
    for key in sorted(set(dict1.keys()) | set(dict2.keys())):
        if key not in dict1:
            print(f"{path}{key}: Missing in first dict. Value in second dict: {dict2[key]}")
        elif key not in dict2:
            print(f"{path}{key}: Missing in second dict. Value in first dict: {dict1[key]}")
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            compare_dicts(dict1[key], dict2[key], f"{path}{key}.")
        elif dict1[key] != dict2[key]:
            print(f"{path}{key}: Values differ. First dict:  {dict1[key]} Second dict: {dict2[key]}")


def compare_dict_keys(dict1, dict2):
    def get_all_keys(d):
        keys = set(d.keys())
        for value in d.values():
            if isinstance(value, dict):
                keys.update(get_all_keys(value))
        return keys

    return get_all_keys(dict1) == get_all_keys(dict2)


def check_keys(dict0, dict1):
    def check_nested(d0, d1):
        for key, value in d0.items():
            if key not in d1:
                return False
            if isinstance(value, dict):
                if not isinstance(d1[key], dict):
                    return False
                if not check_nested(value, d1[key]):
                    return False
        return True

    return check_nested(dict0, dict1)


def get_cache_hash(config, exchange):
    to_hash = {
        "coins": config["live"]["approved_coins"],
        "end_date": format_end_date(config["backtest"]["end_date"]),
        "start_date": config["backtest"]["start_date"],
        "exchange": config["backtest"]["exchanges"] if exchange == "combined" else exchange,
        "minimum_coin_age_days": config["live"]["minimum_coin_age_days"],
        "gap_tolerance_ohlcvs_minutes": config["backtest"]["gap_tolerance_ohlcvs_minutes"],
    }
    return calc_hash(to_hash)


def load_coins_hlcvs_from_cache(config, exchange):
    cache_hash = get_cache_hash(config, exchange)
    cache_dir = Path("caches") / "hlcvs_data" / cache_hash[:16]
    if os.path.exists(cache_dir):
        coins = json.load(open(cache_dir / "coins.json"))
        mss = json.load(open(cache_dir / "market_specific_settings.json"))
        if config["backtest"]["compress_cache"]:
            fname = cache_dir / "hlcvs.npy.gz"
            logging.info(f"{exchange} Attempting to load hlcvs data from cache {fname}...")
            with gzip.open(fname, "rb") as f:
                hlcvs = np.load(f)
        else:
            fname = cache_dir / "hlcvs.npy"
            logging.info(f"{exchange} Attempting to load hlcvs data from cache {fname}...")
            hlcvs = np.load(fname)
        return cache_dir, coins, hlcvs, mss


def save_coins_hlcvs_to_cache(config, coins, hlcvs, exchange, mss):
    cache_hash = get_cache_hash(config, exchange)
    cache_dir = Path("caches") / "hlcvs_data" / cache_hash[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    if all([os.path.exists(cache_dir / x) for x in ["coins.json", "hlcvs.npy"]]):
        return
    logging.info(f"Dumping cache...")
    json.dump(coins, open(cache_dir / "coins.json", "w"))
    json.dump(mss, open(cache_dir / "market_specific_settings.json", "w"))
    uncompressed_size = hlcvs.nbytes
    sts = utc_ms()
    if config["backtest"]["compress_cache"]:
        fpath = cache_dir / "hlcvs.npy.gz"
        logging.info(f"Attempting to save hlcvs data to cache {fpath}...")
        with gzip.open(fpath, "wb", compresslevel=1) as f:
            np.save(f, hlcvs)
        compressed_size = (cache_dir / "hlcvs.npy.gz").stat().st_size
        line = (
            f"{compressed_size/(1024**3):.2f} GB compressed "
            f"({compressed_size/uncompressed_size*100:.1f}%)"
        )
    else:
        fpath = cache_dir / "hlcvs.npy"
        logging.info(f"Attempting to save hlcvs data to cache {fpath}...")
        np.save(fpath, hlcvs)
        line = ""
    logging.info(
        f"Successfully dumped hlcvs cache {fpath}: "
        f"{uncompressed_size/(1024**3):.2f} GB uncompressed, "
        f"{line}"
    )

    logging.info(f"Seconds to dump cache: {(utc_ms() - sts) / 1000:.4f}")
    return cache_dir


async def prepare_hlcvs_mss(config, exchange):
    results_path = oj(
        config["backtest"]["base_dir"],
        exchange,
        "",
    )
    try:
        sts = utc_ms()
        result = load_coins_hlcvs_from_cache(config, exchange)
        if result:
            logging.info(f"Seconds to load cache: {(utc_ms() - sts) / 1000:.4f}")
            cache_dir, coins, hlcvs, mss = result
            logging.info(f"Successfully loaded hlcvs data from cache")
            return coins, hlcvs, mss, results_path, cache_dir
    except:
        logging.info(f"Unable to load hlcvs data from cache. Fetching...")
    if exchange == "combined":
        mss, timestamps, hlcvs = await prepare_hlcvs_combined(config)
    else:
        mss, timestamps, hlcvs = await prepare_hlcvs(config, exchange)
    coins = sorted(mss)
    logging.info(f"Finished preparing hlcvs data for {exchange}. Shape: {hlcvs.shape}")
    try:
        cache_dir = save_coins_hlcvs_to_cache(config, coins, hlcvs, exchange, mss)
    except Exception as e:
        logging.error(f"failed to save hlcvs to cache {e}")
        traceback.print_exc()
        cache_dir = ""
    return coins, hlcvs, mss, results_path, cache_dir


def prep_backtest_args(config, mss, exchange, exchange_params=None, backtest_params=None):
    coins = sorted(set(config["backtest"]["coins"][exchange]))  # sort for consistency
    bot_params = {k: config["bot"][k].copy() for k in ["long", "short"]}
    for pside in bot_params:
        bot_params[pside]["wallet_exposure_limit"] = (
            bot_params[pside]["total_wallet_exposure_limit"] / bot_params[pside]["n_positions"]
            if bot_params[pside]["n_positions"] > 0
            else 0.0
        )
    if exchange_params is None:
        exchange_params = [
            {k: mss[coin][k] for k in ["qty_step", "price_step", "min_qty", "min_cost", "c_mult"]}
            for coin in coins
        ]
    if backtest_params is None:
        backtest_params = {
            "starting_balance": config["backtest"]["starting_balance"],
            "maker_fee": mss[coins[0]]["maker"],
            "coins": coins,
        }
    return bot_params, exchange_params, backtest_params


def expand_analysis(analysis, fills, config):
    return analysis


def run_backtest(hlcvs, mss, config: dict, exchange: str):
    bot_params, exchange_params, backtest_params = prep_backtest_args(config, mss, exchange)
    logging.info(f"Backtesting {exchange}...")
    sts = utc_ms()

    with create_shared_memory_file(hlcvs) as shared_memory_file:
        fills, equities, analysis = pbr.run_backtest(
            shared_memory_file,
            hlcvs.shape,
            hlcvs.dtype.str,
            bot_params,
            exchange_params,
            backtest_params,
        )

    logging.info(f"seconds elapsed for backtest: {(utc_ms() - sts) / 1000:.4f}")
    return fills, equities, expand_analysis(analysis, fills, config)


def post_process(config, hlcvs, fills, equities, analysis, results_path, exchange):
    sts = utc_ms()
    fdf = process_forager_fills(fills)
    equities = pd.Series(equities)
    analysis_py, bal_eq = analyze_fills_forager(
        config["backtest"]["coins"][exchange], hlcvs, fdf, equities
    )
    for k in analysis_py:
        if k not in analysis:
            analysis[k] = analysis_py[k]
    logging.info(f"seconds elapsed for analysis: {(utc_ms() - sts) / 1000:.4f}")
    pprint.pprint(analysis)
    results_path = make_get_filepath(
        oj(results_path, f"{ts_to_date(utc_ms())[:19].replace(':', '_')}", "")
    )
    json.dump(analysis, open(f"{results_path}analysis.json", "w"), indent=4, sort_keys=True)
    config["analysis"] = analysis
    dump_config(config, f"{results_path}config.json")
    fdf.to_csv(f"{results_path}fills.csv")
    bal_eq.to_csv(oj(results_path, "balance_and_equity.csv"))
    plot_forager(
        results_path,
        config["backtest"]["coins"][exchange],
        fdf,
        bal_eq,
        hlcvs,
        config["disable_plotting"],
    )


def plot_forager(
    results_path, coins: [str], fdf: pd.DataFrame, bal_eq, hlcvs, disable_plotting: bool = False
):
    plots_dir = make_get_filepath(oj(results_path, "fills_plots", ""))
    plt.clf()
    bal_eq.plot()
    plt.savefig(oj(results_path, "balance_and_equity.png"))

    if not disable_plotting:
        for i, coin in enumerate(coins):
            try:
                logging.info(f"Plotting fills for {coin}")
                hlcvs_df = pd.DataFrame(hlcvs[:, i, :3], columns=["high", "low", "close"])
                fdfc = fdf[fdf.coin == coin]
                plt.clf()
                plot_fills_forager(fdfc, hlcvs_df)
                plt.title(f"Fills {coin}")
                plt.xlabel = "time"
                plt.ylabel = "price"
                plt.savefig(oj(plots_dir, f"{coin}.png"))
            except Exception as e:
                logging.info(f"Error plotting {coin} {e}")


async def main():
    manage_rust_compilation()
    parser = argparse.ArgumentParser(prog="backtest", description="run forager backtest")
    parser.add_argument(
        "config_path", type=str, default=None, nargs="?", help="path to json passivbot config"
    )
    parser.add_argument(
        "--disable_plotting",
        "-dp",
        dest="disable_plotting",
        action="store_true",
        help="disable plotting",
    )
    template_config = get_template_live_config("v7")
    del template_config["optimize"]
    keep_live_keys = {
        "approved_coins",
        "ignored_coins",
        "minimum_coin_age_days",
    }
    for key in sorted(template_config["live"]):
        if key not in keep_live_keys:
            del template_config["live"][key]
    add_arguments_recursively(parser, template_config)
    args = parser.parse_args()
    if args.config_path is None:
        logging.info(f"loading default template config configs/template.json")
        config = load_config("configs/template.json", verbose=False)
    else:
        logging.info(f"loading config {args.config_path}")
        config = load_config(args.config_path)
    update_config_with_args(config, args)
    config = format_config(config, verbose=False)
    await add_all_eligible_coins_to_config(config)
    config["disable_plotting"] = args.disable_plotting
    config["backtest"]["cache_dir"] = {}
    config["backtest"]["coins"] = {}
    if config["backtest"]["combine_ohlcvs"]:
        exchange = "combined"
        coins, hlcvs, mss, results_path, cache_dir = await prepare_hlcvs_mss(config, exchange)
        exchange_preference = defaultdict(list)
        for coin in coins:
            exchange_preference[mss[coin]["exchange"]].append(coin)
        for ex in exchange_preference:
            logging.info(f"chose {ex} for {','.join(exchange_preference[ex])}")
        config["backtest"]["coins"][exchange] = coins
        config["backtest"]["cache_dir"][exchange] = str(cache_dir)
        fills, equities, analysis = run_backtest(hlcvs, mss, config, exchange)
        post_process(config, hlcvs, fills, equities, analysis, results_path, exchange)
    else:
        configs = {exchange: deepcopy(config) for exchange in config["backtest"]["exchanges"]}
        tasks = {}
        for exchange in config["backtest"]["exchanges"]:
            tasks[exchange] = asyncio.create_task(prepare_hlcvs_mss(configs[exchange], exchange))
        for exchange in tasks:
            coins, hlcvs, mss, results_path, cache_dir = await tasks[exchange]
            configs[exchange]["backtest"]["coins"][exchange] = coins
            configs[exchange]["backtest"]["cache_dir"][exchange] = str(cache_dir)
            fills, equities, analysis = run_backtest(hlcvs, mss, configs[exchange], exchange)
            post_process(configs[exchange], hlcvs, fills, equities, analysis, results_path, exchange)


if __name__ == "__main__":
    asyncio.run(main())
