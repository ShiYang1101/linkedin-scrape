from time import sleep
from tqdm import tqdm

for time in tqdm(range(10), ncols=0, 
                 bar_format = "{bar}"):
    sleep(time)