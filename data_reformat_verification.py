import json
import os
import domain_utils
from domain_utils import *
import sys

domain_name = "color_verification"
domain = domain_utils.domains[domain_name]

problem_type = f"{sys.argv[1]}/"
instance_dir = "data/color_verification/"
old_format_dir = "responses-old_format20231006/color_verification/gpt-4_chat/"

def check_correct(instance, response):
    with open(f"{instance_dir}instance-{instance}{domain.file_ending()}","r") as fp:
        instance_text = fp.read()
    x, _ = domain.check_coloring(response, instance_text)
    return x

with open(f"{old_format_dir}{problem_type}responses.json", "r") as fp:
    old_data = json.load(fp)


new_data = {}
for instance in old_data:
    new_data[instance]={"prompts": [old_data[instance]["query"]], "responses":[old_data[instance]["response"]], "stopped":False}

os.makedirs(f"responses/color_verification/gpt-4_chat/{problem_type}/", exist_ok=True)
with open(f"responses/color_verification/gpt-4_chat/{problem_type}responses.json", "w") as fp:
    json.dump(new_data,fp, indent=4)
