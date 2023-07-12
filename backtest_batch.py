from backtest import main
import asyncio
import sys
import os

path_0 = './configs/live'
folders_0 = next(os.walk(path_0))[1]

for folder in folders_0:
    path_1 = os.path.join(path_0, folder)
    files_1 = next(os.walk(path_1))[2]
    for file_i in files_1:
        file_path_i = os.path.join(path_1, file_i)
        sys.argv.extend([file_i])

        asyncio.run(main())
    break

print(sys.argv)



print("End of script!")
