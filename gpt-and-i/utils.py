import json
import os
import time
import pickle
from itertools import chain
from rich.progress import TextColumn, MofNCompleteColumn, Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn 
from rich.table import Column 
import pandas as pd
import subprocess

### json utils
def write_json(domain_name,dict_to_write,data_type):
    directory = f"data/{data_type}/{domain_name}"
    os.makedirs(directory, exist_ok=True)
    location = f"{directory}/{data_type}.json"
    with open(f'{location}.tmp',"w") as fp:
        json.dump(dict_to_write, fp, indent = 4)
    os.replace(f'{location}.tmp', location)

def read_json(domain_name, overwrite_previous, data_type, verbose=False, strange_subloc="", remove=False):
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
        elif remove:
            stamp = str(time.time())
            new_name = location.replace(".json",f"-{stamp}.json.old")
            os.rename(location, new_name)
        return previous
    else:
        if verbose: print(f"{location} does not exist. Returning empty dictionary.")
        return {}

### jsonl utils
#### these require data to be in unstructured lists
def write_jsonl(domain_name, item_to_write, data_type, llm=""):
    directory = f"data/{data_type}/{domain_name}/{llm}"
    os.makedirs(directory, exist_ok=True)
    location = f"{directory}/{data_type}.jsonl"
    with open(location, "a") as file:
        file.write(json.dumps(item_to_write) + "\n")

def read_jsonl(domain_name, data_type, llm="", verbose=False):
    location = f"data/{data_type}/{domain_name}/{llm}/{data_type}.jsonl"
    if not os.path.exists(location):
        if verbose: print(f"{location} does not exist. Returning empty list.")
        return []
    with open(location, 'r') as file:
        previous = [json.loads(line) for line in file]
    return previous

def update_format_to_jsonl(domain_name, overwrite_previous, data_type, llm, backprompt_type, temp, trial_num=0, verbose=False):
    raise ValueError("This function is deprecated.")
    prompting_details = f"backprompting-{backprompt_type}{f'-temp{temp}' if temp else ''}"
    subloc=f"{llm}_chat/{prompting_details}/{trial_num if trial_num else ''}{data_type}.json"
    original_location = f"data/{data_type}/{domain_name}/{subloc}"
    if not os.path.exists(original_location):
        if verbose: print(f"[!]: Nothing to update to new format. ({original_location} does not exist.)")
        return None
    old_data = read_json(domain_name, False, data_type, verbose, strange_subloc=subloc, remove=True)
    instance_data = [{"problem_id":key, "trial_num":f"{int(trial_num) if trial_num else 0}", **old_data[key]} for key in old_data.keys()]
    new_data = []
    for instance in instance_data:
        response_list = [{**{k: instance[k] for k in instance.keys() - {'responses', 'prompts'}}, "prompt_num":n,
                          "prompt":instance["prompts"][n], "response":instance["responses"][n],
                          "backprompt_type":backprompt_type, "temp": temp, "converted_data": True,
                          "llm": llm}
                         for n in range(0,len(instance["responses"]))]
        new_data = new_data + response_list
    if overwrite_previous:
        backup_and_remove_jsonl(original_location)
    for item in new_data:
        write_jsonl(domain_name, item, data_type, llm=llm)

def backup_and_remove_jsonl(old_name):
    stamp = str(time.time())
    new_name = old_name.replace(".jsonl",f"-{stamp}.jsonl.old")
    os.rename(old_name, new_name)

### instance utils
def read_instance(domain_name,number_of_instance,file_ending):
    try:
        with open(f"data/instances/{domain_name}/instance-{number_of_instance}{file_ending}") as fp:
            return fp.read()
    except FileNotFoundError:
        print(f"data/instances/{domain_name}/instance-{number_of_instance} not found.")

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

### LLM cost utils
costs_per_million = {
    'gpt-4': (30, 60),
    'gpt-4-0613': (30, 60),
    'gpt-4-turbo': (10, 30),
    'gpt-4-turbo-2024-04-09': (10, 30),
    'gpt-3.5-turbo-0125': (0.5, 1.5),
    'gpt-4o-2024-05-13': (5, 15),
    'gpt-4o-mini-2024-07-18': (0.15, 0.6),
    'o1-preview': (15, 60)
    }

def known_llm(llm):
    known = llm in costs_per_million.keys()
    if not known: print(f"[-]: Invalid llm name. Must be one of {costs_per_million.keys()}.")
    return known
def calculate_token_cost(llm, input_tokens, output_tokens):
    return (input_tokens * costs_per_million[llm][0] + output_tokens * costs_per_million[llm][1]) / 10**6

### data restructuring utils
def check_spec(line, key, llm, backprompt_type, temp, trial_num):
    return line["llm"] == llm and line["backprompt_type"] == backprompt_type and line["temp"] == temp and int(line["trial_num"]) == int(trial_num) and int(line["problem_id"]) == int(key)