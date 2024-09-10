import json
import os
import domain_utils
from domain_utils import *
import argparse

START = 1
END = 100

def write_json(domain_name,text_to_write, problem_type=""):
    os.makedirs(f"prompts/{domain_name}", exist_ok=True)
    location = f"prompts/{domain_name}/prompts-{problem_type}.json" if problem_type else f"prompts/{domain_name}/prompts.json"
    with open(location,"w") as fp:
        json.dump(text_to_write, fp, indent = 4)

def read_instance(domain_name,number_of_instance,file_ending):
    try:
        with open(f"data/{domain_name}/instance-{number_of_instance}{file_ending}") as fp:
            return fp.read()
    except FileNotFoundError:
        print(f"data/{domain_name}/instance-{number_of_instance} not found.")

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-s','--start', type=int, default=START, help='Start number of instances to process')
    parser.add_argument('-e','--end', type=int, default=END, help='End number of instances to process')
    parser.add_argument('-d','--domain', type=str, required="True", help='Problem domain to generate for')
    #parser.add_argument('-m','--multishot', type=int, default=0, help='Number of worked examples to prepend to each prompt')
    parser.add_argument('-p','--problem', type=str, default="", help='Problem variant to generate')
    args = parser.parse_args()
    start = args.start
    end = args.end
    #multishot = args.multishot
    domain_name = args.domain
    problem_type = args.problem
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    domain = domain_utils.domains[domain_name]

    prompts = {}
    for x in range(start,end+1):
        instance = read_instance(domain_name,x,domain.file_ending())
        if instance:
            prompts[f"{x}"] = domain.generate(instance, problem_type)
    write_json(domain_name, prompts, problem_type)