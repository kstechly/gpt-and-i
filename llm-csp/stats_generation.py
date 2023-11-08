import os
import argparse
import json
from tqdm import tqdm
import domain_utils
from domain_utils import *
import matplotlib.pyplot as plt

def sum_dict(dictionary,partition_key="",partition_val=""):
    summed_dictionary = {}
    for key in dictionary:
        if partition_key and partition_val and str(dictionary[key][partition_key])!=partition_val:
            continue
        for subkey in dictionary[key]:
            try: int(dictionary[key][subkey])
            except: continue
            if subkey not in summed_dictionary:
                summed_dictionary[subkey] = 0
            summed_dictionary[subkey] += int(dictionary[key][subkey])
            
    return summed_dictionary

def collapse(dictionary, prompt_num):
    # TODO make this general beyond just game24
    # takes a dictionary of instances, each of which comprises a list of identically keyed dictionaries
    # and collapses it to a dictionary of instance keyed dictionaries, containing: (while ignoring anything past prompt_num in each list)
    collapsed_dictionary = {}
    not_enough = 0
    for key in dictionary:
        instance = dictionary[key]
        collapsed_dictionary[key] = {"unique":0, "correct":0, "malformed":0, "stopped":False, "stopped correctly":False,"ever correct":False,"uniques ever correct": False}
        for n in range(0,min(len(instance),prompt_num)):
            collapsed_dictionary[key]["unique"] +=int(instance[n]["unique"])
            collapsed_dictionary[key]["correct"] +=int(instance[n]["correct"])
            collapsed_dictionary[key]["malformed"] +=int(instance[n]["eval"]=="malformed")
            collapsed_dictionary[key]["stopped"] = instance[n]["stopped"]
            collapsed_dictionary[key]["stopped correctly"] = instance[n]["stopped"] and instance[n]["correct"]
            collapsed_dictionary[key]["ever correct"] = instance[n]["correct"] or collapsed_dictionary[key]["ever correct"]
        uniques_counter = 0
        for prompt in instance:
            if prompt["unique"]: uniques_counter+=1
            collapsed_dictionary[key]["uniques ever correct"] = prompt["correct"] or collapsed_dictionary[key]["uniques ever correct"]
            if uniques_counter >= prompt_num: break
        if uniques_counter < prompt_num: 
            print(f"Not enough uniques for instance {key}")
            not_enough +=1
    print(not_enough)
    return collapsed_dictionary

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        \n davinci = GPT-3 Davinci \
                        \n curie = GPT-3 Curie \
                        \n babbage = GPT-3 Babbage \
                        \n ada = GPT-3 Ada \
                        ')
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to evaluate within')
    parser.add_argument('-b', '--backprompting', type=str, default='', help='If backprompting, provide the type of backprompt to pass to the domain. Common types: zero, passfail, full, llm')
    parser.add_argument('-p', '--problem', type=str, default='', help='If doing a domain subproblem, specify it here')
    parser.add_argument('-B', '--backprompt_num', type=int, default=15, help='If multiprompting, provide the maximum number of prompts to try. Double this number to get expected behavior for LLM backprompting')
    parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('-n', '--end_number', type=int, default=0, help='For running from instance m to n')
    parser.add_argument('-m', '--start_number', type=int, default=1, help='For running from instance m to n. You must specify -n for this to work')
    parser.add_argument('-t', '--temperature', type=float, default=0, help='Temperature from 0.0 to 2.0')
    parser.add_argument('-k', '--partitionkey', type=str, default='', help='Only get stats for a specific partition. Must use with -v')
    parser.add_argument('-v', '--partitionval', type=str, default='', help='Only get stats for a specific partition. Must use with -k')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    problem_type = args.problem
    partition_key = args.partitionkey
    partition_val = args.partitionval
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    backprompting = args.backprompting
    backprompt_num = args.backprompt_num
    specified_instances = args.specific_instances
    end_number = args.end_number
    start_number = args.start_number
    temperature = args.temperature
    if end_number>0 and specified_instances:
        print("You can't use both -s and -n")
        exit()
    elif end_number>0:
        specified_instances = list(range(start_number,end_number+1))
        print(f"Summarizing stats only for instances from {start_number} to {end_number}")

    # Check relevant directories exist and load eval data
    evals_dir = f"evaluations/{domain_name}/{engine}/"
    if backprompting:
        evals_dir+=f"backprompting-{backprompting}{f'-temp{temperature}' if temperature else ''}/"
    if problem_type:
        evals_dir+=f"{problem_type}/"
    evals_json = evals_dir+"evaluations.json"
    if os.path.exists(evals_json):
        with open(evals_json, 'r') as file:
            evals = json.load(file)
    else: 
        print("You have to run response_evaluation.py first")
        exit()

    # Select only specified instances if so flagged
    if specified_instances: evals = {str(n):evals[str(n)] for n in specified_instances}

    collapsed_evals = collapse(evals, backprompt_num)

    # Summarize data
    stats = sum_dict(collapsed_evals,partition_key=partition_key, partition_val=partition_val)
    print(stats)