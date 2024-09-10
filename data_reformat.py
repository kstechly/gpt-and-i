import json
import os
import domain_utils
from domain_utils import *
import sys

domain_name = "graph_coloring"
domain = domain_utils.domains[domain_name]

backprompt_type = f"backprompting-{sys.argv[1]}/"
backprompt_cat = sys.argv[2]
instance_dir = "data/graph_coloring/"
old_format_dir = "responses-old_format20231006/graph_coloring/gpt-4_chat/"

def check_correct(instance, response):
    with open(f"{instance_dir}instance-{instance}{domain.file_ending()}","r") as fp:
        instance_text = fp.read()
    x, _ = domain.check_coloring(response, instance_text)
    return x

with open(f"{old_format_dir}{backprompt_type}responses.json", "r") as fp:
    old_data = json.load(fp)


# TWO MORE NEEDED
## llm: strip the backprompt text, and reorganize into the responses, then reconstruct the prompts for each 

new_data = {}
if backprompt_cat == "reg":
    for instance in old_data:
        new_data[instance]={"prompts": [old_data[instance]["query"]], "subprompts":[old_data[instance]["query"]], "responses":[], "stopped":False}
        last_response = "response"
        response_keys = [x for x in old_data[instance] if "response" in x]
        new_data[instance]["responses"] = [old_data[instance][x] for x in response_keys]
        backprompt_keys = [x for x in old_data[instance] if "backprompt" in x]
        new_data[instance]["subprompts"].extend([old_data[instance][x] for x in backprompt_keys])
        chain = old_data[instance]["query"]
        for r in range(1, len(new_data[instance]["subprompts"])):
            chain  = chain + "\n" + new_data[instance]["responses"][r] + "\n" + new_data[instance]["subprompts"][r]
            new_data[instance]["prompts"].append(chain)
        if len(response_keys)>1:
            last_response = f"response {len(response_keys)-2}"
        new_data[instance]["stopped"]=check_correct(instance,old_data[instance][last_response])
elif backprompt_cat == "top":
    for instance in old_data:
        new_data[instance]={"prompts": [], "responses":[], "stopped":False}
        response_keys = [x for x in old_data[instance] if "response" in x]
        responses = [old_data[instance][x] for x in response_keys]
        for response in responses:
            new_data[instance]["responses"].append(response)
            new_data[instance]["prompts"].append(old_data[instance]["query"])
elif backprompt_cat == "llm":
    for instance in old_data:
        new_data[instance]={"prompts": [old_data[instance]["query"]], "responses":[], "stopped":False}
        last_response = "response"
        response_keys = [x for x in old_data[instance] if "response" in x]
        responses = [old_data[instance][x] for x in response_keys]
        backprompt_keys = [x for x in old_data[instance] if "backprompt" in x]
        backprompts = [old_data[instance][x] for x in backprompt_keys]

        # Now I need to separate the pieces and recombine them into one big response list, with growing prompts
        new_data[instance]["responses"].append(responses[0])
        chain = old_data[instance]["query"]
        with open(f"{instance_dir}instance-{instance}{domain.file_ending()}","r") as fp:
            instance_text = fp.read()
        for r in range(0, len(backprompts)):
            # first construct the prompt to get the b-prompt from the LLM, append to prompts
            backprompt_query = f"The following graph, described as a set of edges, has an optimal coloring number of {domain.optimal_coloring_number(instance_text)}:\n"
            num_verts, graph_text = domain.generate_graph(instance_text)
            backprompt_query+= graph_text
            backprompt_query+= f"Please check if this coloring is correct:" +responses[r]
            backprompt_query+= f"\nIf it is, say '{domain.STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge."     
            new_data[instance]["prompts"].append(backprompt_query)
            # then extract the LLM's critique response
            backprompt = backprompts[r]
            backprompt = backprompt.removeprefix("\nThis is incorrect. Feedback:\n").removesuffix("\n\nUsing this feedback, please try again. Please provide each vertex's color. Do not skip any vertices. Each color must be provided on a new line in the response and should be formatted as \"{VERTEX NUMBER}: {VERTEX COLOR ASSIGNMENT}\". Please do not provide anything else in your response.")
            new_data[instance]["responses"].append(backprompt)
            # then construct the full length prompt
            chain  = chain + "\n" + responses[r] + "\n" + backprompts[r]
            new_data[instance]["prompts"].append(chain)
            # then just append the response
            new_data[instance]["responses"].append(responses[r+1])
        new_data[instance]["stopped"] = len(responses)<16#the number of instances is less than 15
else: print(f"invalid cat: {backprompt_cat}")

os.makedirs(f"responses/graph_coloring/gpt-4_chat/{backprompt_type}/", exist_ok=True)
with open(f"responses/graph_coloring/gpt-4_chat/{backprompt_type}responses.json", "w") as fp:
    json.dump(new_data,fp, indent=4)
