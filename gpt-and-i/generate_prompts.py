import os
import re
import utils
import domain_utils
from fire import Fire #type: ignore

def read_instance(domain_name,number_of_instance,file_ending):
    try:
        with open(f"data/instances/{domain_name}/instance-{number_of_instance}{file_ending}") as fp:
            return fp.read()
    except FileNotFoundError:
        print(f"data/instances/{domain_name}/instance-{number_of_instance} not found.")

def generate_prompts(domain_name, problem_type="", start=0, end=0, overwrite_previous=False):
    prompts = utils.read_json(domain_name, overwrite_previous, "instances")
    dmn = domain_utils.get_domain(domain_name)

    if not end > start:
        instance_range = [int(re.search(r'instance-(\d+)', f).group(1)) for f in os.listdir(f'data/instances/{domain_name}') if re.match(r'instance-\d+{}'.format(dmn.file_ending()), f)]
    else: instance_range = range(start, end+1)
    print(instance_range)

    for x in instance_range:
        if not overwrite_previous and str(x) in prompts.keys():
            print(f"Skipping instance-{x}, as it already exists.")
            continue
        instance = read_instance(domain_name,x,dmn.file_ending())
        if instance: prompts[f"{x}"] = dmn.generate(instance, problem_type)
    
    utils.write_json(domain_name, prompts, "instances")

if __name__=="__main__":
    Fire(generate_prompts)