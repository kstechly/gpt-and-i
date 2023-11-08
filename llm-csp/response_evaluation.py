import os
import argparse
import json
from tqdm import tqdm
import domain_utils
from domain_utils import *

def evaluate_plan(engine, domain_name, specified_instances=[], ignore_existing=False, verbose=False, multiprompting="", problem_type="", temp=0):
    domain = domain_utils.domains[domain_name]
    
    # Check for/set up relevant directories
    instances_dir = f"data/{domain_name}/"
    outputs_dir = f"responses/{domain_name}/{engine}/"
    evals_dir = f"evaluations/{domain_name}/{engine}/"
    if multiprompting:
        outputs_dir+=f"backprompting-{multiprompting}{f'-temp{temp}' if temp else ''}/"
        evals_dir+=f"backprompting-{multiprompting}{f'-temp{temp}' if temp else ''}/"
    if problem_type:
        outputs_dir+=f"{problem_type}/"
        evals_dir+=f"{problem_type}/"
    outputs_json = outputs_dir+"responses.json"
    evals_json = evals_dir+"evaluations.json"

    # Load response data
    if os.path.exists(outputs_json):
            with open(outputs_json, 'r') as file:
                output = json.load(file)
    else:
        print(f"No response data found in {outputs_dir}")
        return None
    
    # Constrain work to only specified instances if flagged to do so
    if len(specified_instances) > 0:
        output = {str(x) : output[str(x)] for x in specified_instances}
    
    # Load previously done work
    evaluations = {}
    os.makedirs(evals_dir, exist_ok=True)
    if os.path.exists(evals_json) and not ignore_existing:
        with open(evals_json, 'r') as file:
            evaluations = json.load(file)

    # Evaluate each instance individually
    for instance in tqdm(output):
        if instance in evaluations:
            if verbose: print(f"==Instance {instance} already evaluated. Skipping==")
            continue
        if verbose: print(f"==Evaluating instance {instance}==")

        # Load actual instance data
        instance_location = f"{instances_dir}/instance-{instance}{domain.file_ending()}"
        try:
            with open(instance_location,"r") as fp:
                instance_text = fp.read()
        except FileNotFoundError:
            print(f"{instance_location} not found. Skipping.")
            continue

        # Evaluate instance
        evaluations[instance] = domain.evaluate(instance_text, output[instance], problem_type, multiprompting)
        if verbose: print(f"==Evaluation for instance {instance}: ==\n{evaluations[instance]}")
        
        # Dump to file
        with open(evals_json, 'w') as file:
            json.dump(evaluations, file, indent=4)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        ')
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to evaluate within')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('-i', '--ignore_existing', action='store_true', help='Ignore existing output')
    parser.add_argument('-b', '--backprompting', type=str, default='', help='If multiprompting, provide the type of multiprompt to pass to the domain. Common types: zero, passfail, full, llm, top')
    parser.add_argument('-n', '--end_number', type=int, default=0, help='For running from instance m to n')
    parser.add_argument('-m', '--start_number', type=int, default=1, help='For running from instance m to n. You must specify -n for this to work')
    parser.add_argument('-t', '--temperature', type=float, default=0, help='Temperature from 0.0 to 2.0')
    parser.add_argument('-p', '--problem', type=str, default='', help='If doing a domain subproblem, specify it here')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    specified_instances = args.specific_instances
    specified_instances = args.specific_instances
    verbose = args.verbose
    backprompting = args.backprompting
    ignore_existing = args.ignore_existing
    end_number = args.end_number
    start_number = args.start_number
    problem_type = args.problem
    temperature = args.temperature
    if end_number>0 and specified_instances:
        print("You can't use both -s and -n")
    elif end_number>0:
        specified_instances = list(range(start_number,end_number+1))
        print(f"Running instances from {start_number} to {end_number}")
    print(f"Engine: {engine}, Domain: {domain_name}, Verbose: {verbose}, Backprompting: {bool(backprompting)}" )
    evaluate_plan(engine, domain_name, specified_instances, ignore_existing, verbose, backprompting, problem_type=problem_type, temp=temperature)