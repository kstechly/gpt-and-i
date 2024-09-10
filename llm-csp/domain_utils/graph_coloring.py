DEFAULT_PROMPT_START = "Color the following graph, described as a set of edges, such that no two vertices on the same edge share a color.\n"
PROMPT_SPLITTER = "Please do not provide anything else in your response, and end your response with '[ANSWER END]'"
DEFAULT_PROMPT_END = "Please provide each vertex's color. Do not skip any vertices. Each color must be provided on a new line in the response and should be formatted as \"{VERTEX NUMBER}: {VERTEX COLOR ASSIGNMENT}\". " + PROMPT_SPLITTER

CHROMATIC_NUMBER_KEY = "OPTIMAL CHROMATIC NUMBER === "
GRAPH_COLORING_DIRECTORY = "../data/graph_coloring/"

STOP_PHRASE = "Verifier confirmed success."

INITIAL_NODES = 3
NEIGHBOR_P = .4
SOURCE_P = .2

import grinpy
import os
import argparse
import matplotlib.pyplot as plt
import json
import time
import re
import random
from domain_utils.color_verification import parse_messy_json, generate_cot_prompt

def parse_dimacs(instance_text):
    parsed = []
    for line in str(instance_text).split("\n"):
        text = line.split(" ")
        if text[0] == "e":
            parsed.append([text[1],text[2]])
    return parsed

def construct_dimacs(parsed_graph):
    dimacs = ""
    for edge in parsed_graph:
        dimacs+=f"\ne {edge[0]} {edge[1]}"
    return dimacs

def optimal_coloring_number(instance_text):
    if CHROMATIC_NUMBER_KEY in instance_text:
        return instance_text.split(CHROMATIC_NUMBER_KEY)[1].split("\n")[0]
    graph = grinpy.Graph(parse_dimacs(instance_text))
    return grinpy.chromatic_number(graph)

def check_coloring(model_response, instance_text):
    coloring = {}
    for line in model_response.split("\n"):
        assignment = line.strip().split(": ")
        if len(assignment) < 2: continue #throw out lines that aren't part of the coloring
        vertex_number = assignment[0]
        coloring[vertex_number] = assignment[1]
    # check if coloring is valid
    edges = parse_dimacs(instance_text)
    wrong_edges = []
    for edge in edges:
        if edge[0] not in coloring:
            return False, [f"Vertex {edge[0]} was not given a value in the coloring."]
        if edge[1] not in coloring:
            return False, [f"Vertex {edge[1]} was not given a value in the coloring."]
        if coloring[edge[0]] == coloring[edge[1]]:
            wrong_edges.append(f"Vertex {edge[0]} and vertex {edge[1]} were both colored {coloring[edge[0]]} despite being connected by an edge.")
    if wrong_edges:
        return False, wrong_edges
    # check if coloring is optimal
    optimal_num = int(optimal_coloring_number(instance_text))
    if optimal_num == len(set(coloring.values())):
        return True, []
    else: 
        return False, [f"This coloring is not optimal. It uses {len(set(coloring.values()))} colors, when only {int(optimal_coloring_number(instance_text))} are necessary.\n Please recolor."]

def evil_check_coloring(model_response, instance_text):
    raise NotImplementedError #Update this

def generate_random_graph(num_nodes, edge_p):
    graph_attempt = grinpy.gnp_random_graph(num_nodes, edge_p)
    num_tries = 1
    while not grinpy.is_planar(graph_attempt):
        graph_attempt = grinpy.gnp_random_graph(num_nodes, edge_p)
        print(f"Try #{num_tries}")
        num_tries+=1
    return graph_attempt

def generate_graph(instance_text):
    prompt = ""
    num_verts = 0
    min_vert = 1
    for edge in parse_dimacs(instance_text):
        prompt += f"Vertex {edge[0]} is connected to vertex {edge[1]}.\n"
        num_verts = max(num_verts, int(edge[0]),int(edge[1]))
        min_vert = min(min_vert, int(edge[0]), int(edge[1]))
    num_verts += (min_vert+1)%2
    return num_verts, prompt

def concat_trace(instance_output, divisor = 1):
    prompts = instance_output["prompts"]
    responses = instance_output["responses"]
    trace = prompts[-divisor] + "\n" + responses[-divisor] +"[ANSWER END]\n"
    return trace

# def concat_trace_limited(instance_output, divisor = 1, hist_length=1):
#     prompts = instance_output["prompts"]
#     responses = instance_output["responses"]
#     prompts[-1]
# TODO implement a history backprompt


def evaluate_up_to(instance_text, response_trace, responses_correct, problem_type="", backprompt_type=""):
    evaluation = {}
    responses = response_trace["responses"]
    token_cost = sum(map(len, responses))
    prompts = response_trace["prompts"][:len(responses)] # deals with extra appended (but unsent) prompts
    token_cost += sum(map(len, prompts))
    evaluation["token cost"]= token_cost
    if backprompt_type=="llm": responses = responses[::2]
    responses_correct = [check_coloring(x, instance_text)[0] for x in responses]
    evaluation["correct"] = responses_correct[-1]
    evaluation["ever corrects"] = sum(responses_correct)
    evaluation["ever correct"] = True in responses_correct
    if "top" in backprompt_type: evaluation["correct"] = evaluation["ever correct"]
    evaluation["false negatives"]= sum(responses_correct[:-1])
    evaluation["num prompts"] = len(prompts)
    self_con = max(set(responses), key = responses.count)
    responses = list(map(lambda x: x.replace(" ",""), responses))
    evaluation["num unique responses"] = len(set(responses))
    evaluation["self consistency"]=check_coloring(self_con, instance_text)[0]
    evaluation["stopped"]=response_trace["stopped"]
    evaluation["stopped correctly"]=response_trace["stopped"] and evaluation["correct"]
    return evaluation

#### Required Functions

def file_ending():
    return ".col"

def generate(instance_text, problem_type):
    prompt = DEFAULT_PROMPT_START
    prompt += f"You may use at most {optimal_coloring_number(instance_text)} colors.\n"
    num_verts, graph_text = generate_graph(instance_text)
    prompt += graph_text
    prompt+=f"There are a total of {num_verts} vertices. Please label every vertex, even if it is disconnected from the rest of the graph."
    prompt += DEFAULT_PROMPT_END
    return prompt


def evaluate(instance_text, response_trace, problem_type="", backprompt_type=""):
    evaluation = []
    subtrace = dict(response_trace)
    responses_correct_all = [check_coloring(x,instance_text)[0] for x in subtrace["responses"]]
    for n in range(1, len(response_trace["responses"])+1):
        subtrace["responses"] = response_trace["responses"][:n]
        responses_correct = responses_correct_all[:n]
        evaluation.append(evaluate_up_to(instance_text, subtrace, responses_correct, problem_type, backprompt_type))
    if "llm" in backprompt_type and STOP_PHRASE in response_trace["responses"][-1]:
        evaluation = list(evaluation[:-1])
    return evaluation

def backprompt(instance_text, instance_output, backprompt_type, *args):
    model_response = instance_output["responses"][-1]
    if backprompt_type=="llm-cot":
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            if parse_messy_json(model_response)['correct']:
                return "stop10002"
            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "This is incorrect. Feedback:\n"
            backprompt += model_response
            backprompt += f"\n\nUsing this feedback, please try again. {DEFAULT_PROMPT_END}"
            return backprompt       
        else:
            return generate_cot_prompt(instance_text, model_response)
    if backprompt_type=="llm":
        #free form feedback from the llm
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            if STOP_PHRASE in model_response:
                return "stop10002"
            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "This is incorrect. Feedback:\n"
            backprompt += model_response
            backprompt += f"\n\nUsing this feedback, please try again. {DEFAULT_PROMPT_END}"
            return backprompt       
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"The following graph, described as a set of edges, has an optimal coloring number of {optimal_coloring_number(instance_text)}:\n"
            num_verts, graph_text = generate_graph(instance_text)
            backprompt_query+= graph_text
            backprompt_query+= f"Please check if this coloring is correct:" +model_response
            backprompt_query+= f"\nIf it is, say '{STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge."
            return backprompt_query
    if backprompt_type=="llm-sample":
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            if STOP_PHRASE in model_response:
                return "stop10002"
            return instance_output["prompts"][0]
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"The following graph, described as a set of edges, has an optimal coloring number of {optimal_coloring_number(instance_text)}:\n"
            num_verts, graph_text = generate_graph(instance_text)
            backprompt_query+= graph_text
            backprompt_query+= f"Please check if this coloring is correct:" +model_response
            backprompt_query+= f"\nIf it is, say '{STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge."
            return backprompt_query
    #TODO implement a limited history version
    # if backprompt_type=="llm-one-hist":
    #     if len(instance_output["responses"])%2==0:
    #         # Return generation prompt for even numbered responses, but first check for the stop phrase
    #         if STOP_PHRASE in model_response:
    #             return "stop10002"
    #         backprompt = concat_trace(instance_output, divisor=2)
    #         backprompt += "This is incorrect. Feedback:\n"
    #         backprompt += model_response
    #         backprompt += f"\n\nUsing this feedback, please try again. {DEFAULT_PROMPT_END}"
    #         return backprompt       
    #     else:
    #         # Return checking prompt for odd numbered responses
    #         backprompt_query = f"The following graph, described as a set of edges, has an optimal coloring number of {optimal_coloring_number(instance_text)}:\n"
    #         num_verts, graph_text = generate_graph(instance_text)
    #         backprompt_query+= graph_text
    #         backprompt_query+= f"Please check if this coloring is correct:" +model_response
    #         backprompt_query+= f"\nIf it is, say '{STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge."
    #         return backprompt_query
        

    # if backprompt_type == "llm-query":
    #     
    # elif backprompt_type == "llm-wrapper":
    #     backprompt = "This is incorrect. Feedback:\n"
    #     backprompt += model_response
    #     backprompt += "\n\nUsing this feedback, please try again. " +DEFAULT_PROMPT_END
    #     return backprompt
    # if backprompt_type == "zero":
    #     return f"This coloring may or may not be correct. If it is correct, please repeat it. Do not provide anything else in your response. If it is not correct, provide a correct coloring. {DEFAULT_PROMPT_END}"
    if backprompt_type == "top":
        # Just do the same initial prompt every time. aka best of n
        return instance_output["prompts"][0]
    if backprompt_type == "think":
        return instance_output["prompts"][0]+"\n Let's think step by step."
    check, reasons = check_coloring(model_response, instance_text)
    if check: return STOP_PHRASE
    elif backprompt_type == "top-stop": return instance_output["prompts"][0]
    elif backprompt_type == "passfail": return f"{concat_trace(instance_output)}Feedback: This is not correct. Using the previously provided graph, please provide a correct coloring. {DEFAULT_PROMPT_END}"
    elif backprompt_type == "first": return f"{concat_trace(instance_output)}Feedback: {reasons[0]}\nThis is wrong. Please recolor. {DEFAULT_PROMPT_END}"
    elif backprompt_type == "full": return f"{concat_trace(instance_output)}Feedback: "+" ".join(reasons)+f"\nThis is wrong. Please recolor. {DEFAULT_PROMPT_END}"
    elif backprompt_type == "evil":
        raise NotImplementedError
        check = evil_check_coloring(model_response, instance_text)
        if not check:
            return STOP_PHRASE
        else:
            if check is str:
                return check
            else:
                correct_edges, coloring = check
                edge_num = random.randrange(0, len(correct_edges))
                return f"Vertex {correct_edges[edge_num][0]} and vertex {correct_edges[edge_num][1]} were both colored {coloring[correct_edges[edge_num][0]]} despite being connected by an edge.\nThis is wrong. Please recolor. {DEFAULT_PROMPT_END}"
 
    else: raise NotImplementedError
    

#### Precompute and instance generation scripts
# WARNING: Only works from domain_utils directory

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('task', help='generate, chromatic, or stats'),
    parser.add_argument('-s','--start', type=int, default=1, help='start index')
    parser.add_argument('-e', '--end', type=int, default=100, help='end index')
    parser.add_argument('-t','--total', type=int, default=10, help='total number of nodes')
    parser.add_argument('-p','--probability', type=float, default=NEIGHBOR_P, help='probability of edge generation (Erdős-Rényi)')
    args = parser.parse_args()
    task = args.task
    start = args.start
    end = args.end
    total_nodes = args.total
    if task == "chromatic":
        print(f"Precomputing chromatic numbers for all instances in {GRAPH_COLORING_DIRECTORY}")
        for instance in os.listdir(GRAPH_COLORING_DIRECTORY):
            if instance.startswith("instance-"):
                with open(GRAPH_COLORING_DIRECTORY+instance,"r+") as fp:
                    instance_text = fp.read()
                    print(instance_text)
                    if CHROMATIC_NUMBER_KEY in instance_text:
                        print(f"Instance {instance} was already precomputed. Skipping.")
                        continue
                    chromatic = optimal_coloring_number(instance_text)
                    print(f"Instance {instance}'s chromatic number is {chromatic}")
                    fp.write(f"\nc {CHROMATIC_NUMBER_KEY}{chromatic}")
    elif task == "generate":
        print(f"Generating new instances from {start} to {end} in {GRAPH_COLORING_DIRECTORY}")
        for x in range(start, end+1):
            destination = f"{GRAPH_COLORING_DIRECTORY}instance-{x}.col"
            dimacs = ""
            graph = grinpy.to_edgelist(generate_random_graph(total_nodes, NEIGHBOR_P))
            dimacs = construct_dimacs(graph)
            dimacs += f"\nc {CHROMATIC_NUMBER_KEY}{optimal_coloring_number(dimacs)}"
            with open(destination, "w") as fp:
                fp.write(dimacs)
    elif task == "draw":
        print(f"Drawing labeled graph from instance {start}")
        with open(f"{GRAPH_COLORING_DIRECTORY}instance-{start}.col","r") as fp:
            d_text = fp.read()
        #d_text = "e 0 2\ne 0 4\ne 0 5\ne 1 5\ne 2 3\ne 2 4\ne 2 5\ne 3 4\ne 3 5"
        G = grinpy.Graph(parse_dimacs(d_text))
        #print(grinpy.is_planar(G))
        #print(G)
        grinpy.draw_planar(G, with_labels=True)
        plt.show()
    elif task == "stats":
        print(f"Printing stats for all instances in {GRAPH_COLORING_DIRECTORY}")
        for instance in os.listdir(GRAPH_COLORING_DIRECTORY):
            if instance.startswith("instance-"):
                with open(GRAPH_COLORING_DIRECTORY+instance,"r") as fp:
                    instance_text = fp.read()
                    G = grinpy.Graph(parse_dimacs(instance_text))
                    degs = [x[1] for x in G.degree()]
                    print(f"Max degree for {instance} is {max(degs)}")
                    print(f"Avg degree for {instance} is {sum(degs)/len(degs)}")
    elif task == "dupe":
        print(f"Checking for duplicates across all instances in {GRAPH_COLORING_DIRECTORY}")
        inst_list = []
        for instance in os.listdir(GRAPH_COLORING_DIRECTORY):
            if instance.startswith("instance-"):
                with open(GRAPH_COLORING_DIRECTORY+instance,"r") as fp:
                    instance_text = fp.read()
                    G = grinpy.Graph(parse_dimacs(instance_text))
                    for x, y in inst_list:
                        if grinpy.is_isomorphic(G,x):
                            print(f"{instance} is isomorphic to {y}")
                    inst_list.append([G, instance])
        print(f"Finished dupe check")
    elif task == "convert": 
        RESULTS_LOCATION = "../responses/graph_coloring/gpt-4_chat/backprompting-full/"
        BACKPROMPT_SPLITTER = "\nVertex"
        PROMPTS_LOCATION = "../prompts/graph_coloring/"
        print(f"Converting all instances in {RESULTS_LOCATION}responses.json")
        convert_num = 0
        total_num = 0
        results = {}
        with open(RESULTS_LOCATION+"responses.json", "r") as fp:
            old_results = json.load(fp)
        with open(PROMPTS_LOCATION+"prompts.json", "r") as fp:
            queries = json.load(fp)
        #save a copy jic
        with open(RESULTS_LOCATION+f"responses-old-{int(time.time())}.json","w") as fp:
            json.dump(old_results, fp, indent=4)
        for x in old_results:
            total_num+=1
            if not type(old_results[x]) == str:
                results[x] = old_results[x]
                continue
            splitters = PROMPT_SPLITTER, BACKPROMPT_SPLITTER
            regex_p = '|'.join(map(re.escape, splitters))
            #y = old_results[x].split(PROMPT_SPLITTER)
            y = re.split(regex_p, old_results[x])
            if len(y) <= 2:
                results[x] = {"query":queries[x]}
                results[x]["response"] = old_results[x]
                convert_num+=1
            else:
                results[x] = {"query":queries[x]}
                results[x]["response"] = y[1]
                for n in range(2, len(y)):
                    if n%2:
                        results[x][f"response {int((n-1)/2-1)}"] = y[n]
                    else: 
                        results[x][f"backprompt {int(n/2-1)}"] = BACKPROMPT_SPLITTER+y[n]+PROMPT_SPLITTER
                convert_num+=1
        with open(RESULTS_LOCATION+"responses.json", "w") as fp:
            json.dump(results, fp, indent=4)
        print(f"{convert_num} out of {total_num} converted")