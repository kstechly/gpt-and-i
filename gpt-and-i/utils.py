import json
import os
import time
import pickle
from itertools import chain
from rich.progress import TextColumn, MofNCompleteColumn, Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn  #type: ignore
from rich.table import Column #type: ignore
import pandas as pd #type: ignore

### json utils
def write_json(domain_name,text_to_write,data_type):
    directory = f"data/{data_type}/{domain_name}"
    os.makedirs(directory, exist_ok=True)
    location = f"{directory}/{data_type}.json"
    with open(f'{location}.tmp',"w") as fp:
        json.dump(text_to_write, fp, indent = 4)
    os.replace(f'{location}.tmp', location)

def read_json(domain_name, overwrite_previous, data_type, verbose=False, strange_subloc=""):
    location = f"data/{data_type}/{domain_name}/{data_type}.json"
    if strange_subloc:
        location = f"data/{data_type}/{domain_name}/{strange_subloc}"
    if os.path.exists(location):
        with open(location, 'r') as file:
            previous = json.load(file)
        if overwrite_previous:
            stamp = str(time.time())
            with open(f"data/{data_type}/{domain_name}/{data_type}-{stamp}.json.old","w") as file:
                json.dump(previous, file, indent=4)
        return previous
    else:
        if verbose: print(f"{location} does not exist. Returning empty dictionary.")
        return {}

### pickle utils
def load_pickle(file_loc):
    with open(file_loc, "rb") as fp:
        return pickle.load(fp)
def save_pickle(obj,file_loc):
    with open(file_loc, "wb") as fp:
        pickle.dump(obj, fp)

### progress bar
def progress_bar():
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(table_column=Column(justify="right")),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )

def replace_task(progress, prev, *args, **kwargs):
    if prev is not None:
        progress.remove_task(prev)
    return progress.add_task(*args, **kwargs)

def get_total_cost(domain_name):
    responses = read_json(domain_name, False, "responses", False)
    df = pd.DataFrame(flatten(responses))
    return df['estimated_cost'].sum()


### other utils
def flatten(dict):
    return list(chain(*dict.values()))

def includes_dict(l, b):
    for a in l:
        if not all(k in a.keys() for k in b.keys()): return False
        if all(a[k] == b[k] for k in b.keys()): return True
    return False

def dict_index(l, b):
    for n in range(0, len(l)):
        a = l[n]
        if all(a[k] == b[k] for k in b.keys()): return n
    return -1

def includes_sub_dict(a, b):
    try: 
        if all(a[k] == b[k] for k in b.keys()): return True
    except: return False
    return False