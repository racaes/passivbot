import subprocess
import sys
import os
import pickle
import time

import numpy as np

config_params = "/home/tdb/config_to_live/GALUSDT__adg_per_exposure_short__absolute__v0b.json"
config_backtest = "/home/tdb/git/passivbot/configs/backtest/myconfig_v01.hjson"
symbols = ["GALUSDT", "SOLUSDT", "TRXUSDT",
           "TOMOUSDT", "OCEANUSDT", "IMXUSDT",
           "ETHUSDT", "BTCUSDT", "ADAUSDT", "XRPUSDT", "XMRUSDT"]
symbol_str = ",".join(symbols)
long_exposure = np.arange(21) * 0.05
long_exposure = long_exposure[1:]
t0 = time.time()
results_dict = {}
for lw in long_exposure:
    short_exposure = np.arange(5) * 0.25 * lw
    for sw in short_exposure:
        print(f"Elapsed time since start: {round(time.time() - t0, 2)} s")
        print(f"Starting (lw, sw) = ({lw:.3f}, {sw:.3f})")
        call_str = [
            "python", "backtest.py", config_params,
            "-b", config_backtest,
            "-s", symbol_str,
            "-oh", "yes",
            "-lw", str(round(lw, 3)),
            "-sw", str(round(sw, 3)),
            # "-start_date", "2021-01-01",
            # "-end_date", "2023-07-14"
        ]

        # Subprocess.run
        results_i = subprocess.run(call_str, capture_output=True, text=True)
        results_dict[(lw, sw)] = results_i
        print(f"Finished (lw, sw) = ({lw:.3f}, {sw:.3f})")
        with open('results_backtest_custom.pkl', 'wb') as fp:
            pickle.dump(results_dict, fp, protocol=pickle.HIGHEST_PROTOCOL)
        # https://docs.python.org/3/library/subprocess.html
    # break

print("End of script!")
