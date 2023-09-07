import os
from utils import *
import argparse
import json
from tqdm import tqdm
from pysat.formula import CNF
from pysat.solvers import Solver
import domain_utils
from domain_utils import *

def evaluate_plan(engine, domain_name, specified_instances=[], ignore_existing=False, verbose=False):
    instances_dir = f"data/{domain_name}/"
    outputs_dir = f"responses/{domain_name}/{engine}/"
    evals_dir = f"evaluations/{domain_name}/{engine}/"
    outputs_json = outputs_dir+"responses.json"
    evals_json = evals_dir+"evaluations.json"

    domain = domain_utils.domains[domain_name]

    if os.path.exists(outputs_json):
            with open(outputs_json, 'r') as file:
                output = json.load(file)
    else:
        print(f"No response data found in {outputs_dir}")
        return None
    
    prev_evals = {}
    os.makedirs(evals_dir, exist_ok=True)
    if os.path.exists(evals_json):
            with open(evals_json, 'r') as file:
                prev_evals = json.load(file)

    total_correct = 0
    total_instances = 0
    evaluations = {}
    for instance in tqdm(output):
        if instance in prev_evals.keys():
            if not ignore_existing:
                evaluations[instance]=prev_evals[instance]
                total_correct += int(prev_evals[instance])
                total_instances += 1
                if verbose:
                    print(f"Instance {instance} already evaluated")
                continue
        if len(specified_instances) > 0:
            if instance+1 not in specified_instances:
                continue
            else:
                specified_instances.remove(instance)     
        
        if verbose:
            print(f"Evaluting instance {instance}")

        llm_response = output[instance]
        instance_location = f"{instances_dir}/instance-{instance}{domain.file_ending()}"
        try:
            with open(instance_location,"r") as fp:
                instance_text = fp.read()
        except FileNotFoundError:
            print(f"{instance_location} not found. Skipping.")
            continue
        evaluations[instance] = domain.evaluate(instance_text, llm_response)

        if verbose:
            print(f"Correct: {evaluations[instance]}")
        total_correct += int(evaluations[instance])
        total_instances += 1

        with open(evals_json, 'w') as file:
            json.dump(evaluations, file, indent=4)
    if verbose:
        print(f"Total correct: {total_correct}")
        print(f"Total instances: {total_instances}")
        print(f"Accuracy: {total_correct/total_instances}")


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        \n davinci = GPT-3 Davinci \
                        \n curie = GPT-3 Curie \
                        \n babbage = GPT-3 Babbage \
                        \n ada = GPT-3 Ada \
                        ')
    parser.add_argument('--domain', type=str, required=True, help='Problem domain to evaluate within')
    parser.add_argument('--verbose', type=str, default="False", help='Verbose')
    parser.add_argument('--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('--ignore_existing', action='store_true', help='Ignore existing output')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    specified_instances = args.specific_instances
    verbose = eval(args.verbose)
    ignore_existing = args.ignore_existing
    print(f"Engine: {engine}, Domain: {domain_name}, Verbose: {verbose}")
    evaluate_plan(engine, domain_name, specified_instances, ignore_existing, verbose)