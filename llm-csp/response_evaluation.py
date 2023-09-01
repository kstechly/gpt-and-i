import os
from utils import *
import argparse
import json
from tqdm import tqdm
from pysat.formula import CNF
from pysat.solvers import Solver



def evaluate_plan(engine, specified_instances=[], ignore_existing=False, verbose=False):
    output_dir = f"responses/{engine}/"
    output_json = output_dir+"responses.json"
    if os.path.exists(output_json):
            with open(output_json, 'r') as file:
                output = json.load(file)
    else:
        print(f"No response data found in {output_dir}")
        return None
    evals_dir = f"evaluations/{engine}/"
    evals_json = evals_dir+"evaluations.json"
    prev_evals = {}
    if os.path.exists(evals_json):
            with open(evals_json, 'r') as file:
                prev_evals = json.load(file)
    os.makedirs(evals_dir, exist_ok=True)
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

        cnf_location = f"data/instance-{instance}.cnf"
        if verbose:
            print(f"Evaluting instance {instance}")

        #text to variable assignments
        llm_response = output[instance].split("\n")
        cnf = CNF(cnf_location)
        var_assignments = [0 for _ in range(cnf.nv)]
        for line in llm_response:
            assignment = line.strip().split(": ")
            var_number = ord(assignment[0]) - ord("@")
            var_assignments[var_number - 1] = 1 * var_number if assignment[1] == "true" else -1 * var_number

        missing = False
        #if missing a var assigment, mark wrong
        for i, va in enumerate(var_assignments):
            if va == 0:
                missing = True
        if missing == True:
            evaluations[instance] = False
            continue

        #use solver to check 
        solver = Solver(bootstrap_with=cnf.clauses)
        evaluations[instance] = solver.solve(assumptions=var_assignments)

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
    parser.add_argument('--verbose', type=str, default="False", help='Verbose')
    parser.add_argument('--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('--ignore_existing', action='store_true', help='Ignore existing output')
    args = parser.parse_args()
    engine = args.engine
    specified_instances = args.specific_instances
    verbose = eval(args.verbose)
    ignore_existing = args.ignore_existing
    print(f"Engine: {engine}, Verbose: {verbose}")
    evaluate_plan(engine, specified_instances, ignore_existing, verbose)