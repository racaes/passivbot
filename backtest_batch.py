import subprocess
import sys
import os
import pickle
import time

path_0 = './configs/live'
folders_0 = next(os.walk(path_0))[1]
config_backtest = "/home/tdb/git/passivbot/configs/backtest/myconfig_v01.hjson"
t0 = time.time()
results_dict = {folder: {} for folder in folders_0}
for i, folder in enumerate(folders_0):
    path_1 = os.path.join(path_0, folder)
    files_1 = next(os.walk(path_1))[2]
    for j, file_i in enumerate(files_1):
        print(f"Elapsed time since start: {round(time.time()-t0, 2)} s")
        print(f"Starting (folder, file) = {i, j}, with names: {folder, file_i}")
        file_path_i = os.path.join(path_1, file_i)
        symbol = file_i.split("__")[0]
        call_str = [
            "python", "backtest.py", file_path_i,
            "-b", config_backtest,
            "-s", symbol,
            # "-start_date", "2021-01-01",
            # "-end_date", "2023-07-14"
        ]
        if folder.endswith("ohlcv"):
            call_str.append("-oh")
        # Subprocess.run
        results_i = subprocess.run(call_str, capture_output=True, text=True)
        results_dict[folder].update({file_i: results_i})

        print(f"Finished (folder, file) = {i, j}, with names: {folder, file_i}")
        with open('results_backtest.pkl', 'wb') as fp:
            pickle.dump(results_dict, fp, protocol=pickle.HIGHEST_PROTOCOL)
        # https://docs.python.org/3/library/subprocess.html
    # break

print("End of script!")
