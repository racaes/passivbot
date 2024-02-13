import os
import json

output_folder = "au_20240213_multi_rec_grid"
output_base_folder = "/home/tdb/config_to_live/custom_configs"

output_folder = os.path.join(output_base_folder, output_folder)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

input_folder = "/home/tdb/git/passivbot/configs/live/multisymbol/recursive_grid"

verbose = False
save_res = True
# MODIFICATION INSTRUCTIONS
au_mods_dict = {
    "long": {
        "auto_unstuck_delay_minutes": 120,
        "auto_unstuck_ema_dist": -0.1,
        "auto_unstuck_qty_pct": 0.5,
        "auto_unstuck_wallet_exposure_threshold": 1.0
    },
    "short": {
        "auto_unstuck_delay_minutes": 120,
        "auto_unstuck_ema_dist": -0.1,
        "auto_unstuck_qty_pct": 1.0,
        "auto_unstuck_wallet_exposure_threshold": 1.0
    }
}

params_list = [
    "auto_unstuck_delay_minutes",
    "auto_unstuck_ema_dist",
    "auto_unstuck_qty_pct",
    "auto_unstuck_wallet_exposure_threshold"
]

for i, file in enumerate(os.listdir(input_folder)):
    with open(os.path.join(input_folder, file), "r") as f:
        data = json.load(f)

    for op_type in ["long", "short"]:
        for k in params_list:
            data[op_type][k] = au_mods_dict[op_type][k]
            if verbose:
                print(file, op_type, k, data[op_type][k])
    if verbose:
        print("\n")

    if save_res:
        with open(os.path.join(output_folder, file), "w") as f:
            json.dump(data, f)
    if i > 10 and False:
        break

print("End of Script!")
