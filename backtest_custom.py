import subprocess
import sys
import os
import pickle
import time

import numpy as np

# config_params = "/home/tdb/config_to_live/GALUSDT__adg_per_exposure_short__absolute__v0b.json"
config_params = "/home/tdb/git/passivbot/configs/live/generic_recursive_grid_mode.json"
config_backtest = "/home/tdb/git/passivbot/configs/backtest/myconfig_v04.hjson"
symbols = ["1000FLOKIUSDT"]
           # "GALUSDT", "SOLUSDT", "TRXUSDT",
           # "TOMOUSDT", "OCEANUSDT", "IMXUSDT",
           # "ETHUSDT", "BTCUSDT", "ADAUSDT", "XRPUSDT", "XMRUSDT"]
symbol_str = ",".join(symbols)
long_exposure = np.arange(11) * 0.10
long_exposure = long_exposure[1:]
REDO = True
if os.path.isfile('results_backtest_custom.pkl') and not REDO:
    with open('results_backtest_custom.pkl', 'rb') as fp:
        results_dict = pickle.load(fp)
else:
    t0 = time.time()
    results_dict = {}
    for lw in long_exposure:
        short_exposure = np.arange(4) * 0.333 * lw
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
                # "-start_date", "2022-05-15",
                # "-end_date", "2023-07-26"
            ]

            # Subprocess.run
            results_i = subprocess.run(call_str, capture_output=True, text=True)
            results_dict[(round(lw, 3), round(sw, 3))] = results_i
            print(f"Finished (lw, sw) = ({lw:.3f}, {sw:.3f})")

            with open('results_backtest_custom.pkl', 'wb') as fp:
                pickle.dump(results_dict, fp, protocol=pickle.HIGHEST_PROTOCOL)
        # https://docs.python.org/3/library/subprocess.html
    # break

# Content analysis
full_text = ""
for k, v in results_dict.items():
    text = v.stdout
    text = text.replace("\x1b[39m", "")
    text = text.replace("\x1b[0m", "")
    text = text.replace("\x1b[31m", "")
    full_text += f"KEY: {k}\n\n" + text + "\n"

text_file = open("results_full_report.txt", "wt")
n = text_file.write(full_text)
text_file.close()

print("End of script!")
