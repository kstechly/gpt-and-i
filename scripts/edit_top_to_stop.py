import json
import os
import domain_utils
from domain_utils import *
from tqdm import tqdm

domain_name = "graph_coloring"
domain = domain_utils.domains[domain_name]

origin_dir = f"backprompting-top-temp1.0/"
destination_dir = f"backprompting-top-stop-temp1.0/"
instance_dir = f"data/{domain_name}/"

def check_correct(instance, response):
    with open(f"{instance_dir}instance-{instance}{domain.file_ending()}","r") as fp:
        instance_text = fp.read()
    x, _ = domain.check_coloring(response, instance_text)
    return x
n = 0
l = []
if __name__ == "__main__":
    
    with open(f"responses/{domain_name}/gpt-4_chat/{origin_dir}responses.json", "r") as fp:
        old_data = json.load(fp)

    new_data = {}

    for instance in tqdm(old_data):
        new_data[instance] = {"prompts": old_data[instance]["prompts"], "responses": [], "stopped": False}
        for response in old_data[instance]["responses"]:
            new_data[instance]["responses"].append(response)
            if check_correct(instance, response):
                new_data[instance]["stopped"] = True
                break

    #os.makedirs(f"responses/{domain_name}/gpt-4-0613_chat/{backprompt_type}responses.json", exist_ok=True)
    with open(f"responses/{domain_name}/gpt-4_chat/{destination_dir}responses.json", "w") as fp:
        json.dump(new_data,fp, indent=4)