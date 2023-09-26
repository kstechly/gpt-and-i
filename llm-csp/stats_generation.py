import os
import argparse
import json
from tqdm import tqdm
import domain_utils
from domain_utils import *

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
    #parser.add_argument('-v', '--verbose', action='store_true')
    #parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    #parser.add_argument('-i', '--ignore_existing', action='store_true', help='Ignore existing output')
    parser.add_argument('-b', '--backprompting', type=str, default='', help='If backprompting, provide the type of backprompt to pass to the domain. Common types: zero, passfail, full, llm')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    #specified_instances = args.specific_instances
    #verbose = args.verbose
    backprompting = args.backprompting
    #ignore_existing = args.ignore_existing
    print(f"Engine: {engine}, Domain: {domain_name}, Backprompting: {bool(backprompting)}" )
    #evaluate_plan(engine, domain_name, backprompting)

    evals_dir = f"evaluations/{domain_name}/{engine}/"
    if backprompting:
        evals_dir+=f"backprompting-{backprompting}/"
    evals_json = evals_dir+"evaluations.json"
    if os.path.exists(evals_json):
            with open(evals_json, 'r') as file:
                evals = json.load(file)

    total_correct = {}
    total_instances = {}
    errors = {}
    for instance in tqdm(evals):
        vertex_num = evals[instance]["number of nodes"]
        if vertex_num not in total_correct:
            total_instances[vertex_num]=0
            total_correct[vertex_num]=0
            errors[vertex_num]=0
        total_instances[vertex_num]+=1
        errors[vertex_num] += evals[instance]["number of errors"]
        if evals[instance]["correct"]:
            total_correct[vertex_num]+=1

    total_correct = {x: total_correct[x] for x in sorted(list(total_correct.keys()))}
    total_instances = {x: total_instances[x] for x in sorted(list(total_correct.keys()))}
    errors = {x: errors[x] for x in sorted(list(total_correct.keys()))}
    print(total_correct)
    print(total_instances)
    formatted = ""
    for x in total_correct:
        formatted+=f"&{total_correct[x]} ({int(total_correct[x]/total_instances[x]*100)}\%)"
    print(formatted)
    print(errors)
    average_errors = {x:errors[x]/(total_instances[x]-total_correct[x]) for x in errors}
    print(average_errors)
