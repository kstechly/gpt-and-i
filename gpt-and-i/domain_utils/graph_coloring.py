DEFAULT_PROMPT_START = "Color the following graph, described as a set of edges, such that no two vertices on the same edge share a color.\n"
PROMPT_SPLITTER = "Please do not provide anything else in your response, and end your response with '[ANSWER END]'"
DEFAULT_PROMPT_END = "Please provide each vertex's color. Do not skip any vertices. Each color must be provided on a new line in the response and should be formatted as \"{VERTEX NUMBER}: {VERTEX COLOR ASSIGNMENT}\". " + PROMPT_SPLITTER

CHROMATIC_NUMBER_KEY = "OPTIMAL CHROMATIC NUMBER === "
GRAPH_COLORING_DIRECTORY = "data/instances/graph_coloring/"

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
#from domain_utils.color_verification import parse_messy_json, generate_cot_prompt

#TODO fix these imports and doubling ups with color_verification
def generate_cot_prompt(instance_text, coloring_text):
    prompt = ''
    prompt+= '\n[Instructions]\nWhen outputting your final answer, first print the [Answer] tag, then put your final answer after the [Answer] tag. Respond only in the following format:\nWrong Edges: a list of incorrect edges\nAll Vertices Colored: boolean representing if every vertex is colored\nOptimal Or Less: boolean representing if the number of colors is no more than the optimal\nCorrect: boolean'
    prompt+= f"\n\n[Graph]\nThe following graph, described as a set of edges, has an optimal coloring number of {optimal_coloring_number(instance_text)}:\n"
    _, graph_text = parse_graph_to_prompt(instance_text)
    prompt+= graph_text
    prompt+= f"\n[Coloring]\nA coloring is correct if no adjacent vertices are the same color and the total number of colors used is no more than the optimal coloring number. Please check if this coloring is correct: {coloring_text}"
    prompt+= f"\n\nLet's think step by step. Remember to output your final answer in the format described in the instructions.\n[Thoughts]"
    return prompt

def parse_messy_json(response_raw):
    try: response_json = json.loads(response_raw.split("[Answer]")[1].lower())
    except: 
        try: response_json = json.loads(response_raw)
        except:
            try: response_json = json.loads(response_raw.split("```json")[1].split("```")[0])
            except:
                raise ValueError(response_raw)
    return response_json

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

def missing_vertex(vertex):
    return f"Vertex {vertex} was not given a value in the coloring."
def wrong_edge(v1, v2, color):
    return f"Vertex {v1} and vertex {v2} were both colored {color} despite being connected by an edge."
def not_optimal(optimal_num):
    return f"This coloring is not optimal. Only {optimal_num} colors are necessary."

def check_coloring(proposed_coloring, instance_text):
    coloring = {}
    for line in proposed_coloring.split("\n"):
        assignment = line.strip().split(": ")
        if len(assignment) < 2: continue #throw out lines that aren't part of the coloring
        vertex_number = assignment[0]
        coloring[vertex_number] = assignment[1]
    # check if coloring is valid
    edges = parse_dimacs(instance_text)
    reasons = []
    for edge in edges:
        if edge[0] not in coloring:
            reasons.append(missing_vertex(edge[0]))
        if edge[1] not in coloring:
            reasons.append(missing_vertex(edge[1]))
        if coloring[edge[0]] == coloring[edge[1]]:
            reasons.append(wrong_edge(edge[0], edge[1], coloring[edge[0]]))
    # check if coloring is optimal
    optimal_num = int(optimal_coloring_number(instance_text))
    if optimal_num == len(set(coloring.values())):
        reasons.append(not_optimal(optimal_num))
    if reasons: return False, reasons
    else: return True, []
    
def evil_check_coloring(model_response, instance_text):
    raise NotImplementedError #Update this

def extract_critique_from_llm_response(response, instance_text):
    parsed_json = parse_messy_json(response)
    missing = parsed_json["missing_vertices"]
    wrong_edges = parsed_json["wrong_edges"]
    optimal = parsed_json["optimal"]
    optimal_num = int(optimal_coloring_number(instance_text))
    reasons = [missing_vertex(m) for m in missing] + [wrong_edge(*triple) for triple in wrong_edges]
    if not optimal: reasons.append(not_optimal(optimal_num))
    return reasons

def generate_random_graph(num_nodes, edge_p):
    graph_attempt = grinpy.gnp_random_graph(num_nodes, edge_p)
    # num_tries = 1
    # while not grinpy.is_planar(graph_attempt):
    graph_attempt = grinpy.gnp_random_graph(num_nodes, edge_p)
        # if str(num_tries)[2:] == '0'*(len(str(num_tries))-2) :print(f"Try #{num_tries}")
        # num_tries+=1
    return graph_attempt

def parse_graph_to_prompt(instance_text):
    prompt = ""
    num_verts = 0
    min_vert = 1
    for edge in parse_dimacs(instance_text):
        prompt += f"Vertex {edge[0]} is connected to vertex {edge[1]}.\n"
        num_verts = max(num_verts, int(edge[0]),int(edge[1]))
        min_vert = min(min_vert, int(edge[0]), int(edge[1]))
    num_verts += (min_vert+1)%2
    return num_verts, prompt

#### Required Functions

def file_ending():
    return ".col"

def generate(instance_text):
    prompt = DEFAULT_PROMPT_START
    prompt += f"You may use at most {optimal_coloring_number(instance_text)} colors.\n"
    num_verts, graph_text = parse_graph_to_prompt(instance_text)
    prompt += graph_text
    prompt+=f"There are a total of {num_verts} vertices. Please label every vertex, even if it is disconnected from the rest of the graph."
    prompt += DEFAULT_PROMPT_END
    return prompt

def evaluate(instance):
    evaluation = []
    backprompt_type = instance[-1]["backprompt_type"]
    instance_text = get_instance_text(instance[-1]["problem_id"])
    critiques = []
    if "llm" in backprompt_type:
        generations = instance[::2]
        generations[-1]['stopped'] = instance[-1]['stopped']
        if backprompt_type != "sound+llm": critiques = instance[1::2]
    else:
        generations = instance
    for response in generations:
        correct = check_coloring(response["response"], instance_text)[0]
        verification_claim = response['stopped']
        if backprompt_type == "top":
            verification_claim = correct
        evaluation.append({"correct": correct, "verification_claim": verification_claim})
        if backprompt_type == "top" and verification_claim: break
    return evaluation

def get_instance_text(problem_id):
    with open(f"{GRAPH_COLORING_DIRECTORY}instance-{problem_id}.col","r") as fp:
        return fp.read()

def generate_verification_prompt(instance):
    instance_text = get_instance_text(instance[-1]["problem_id"])
    response = instance[-1]["response"]
    # Return checking prompt for odd numbered responses
    backprompt_query = '[Instructions]\nWhen outputting your final answer, first print the [Answer] tag, then put your final answer after the [Answer] tag. Respond only with a json dictionary in the following format:\n'+\
        '{"wrong_edges": [a list of triples: [v1, v2, c] where v1 and v2 are connected and both colored c],'+\
        '"missing_vertices": [a list of vertices that were not colored],'+\
        '"optimal": boolean representing if the number of colors used is less than the given optimal number,'+\
        '"correct": boolean representing overall correctness}'+\
        '\nEnsure that the dictionary contains all four keys, even if some are empty. Ensure that the python json library can parse the dictionary.\n'
    backprompt_query+= f"[QUERY]\nThe following graph, described as a set of edges, has an optimal coloring number of {optimal_coloring_number(instance_text)}:\n"
    _, graph_text = parse_graph_to_prompt(instance_text)
    backprompt_query+= graph_text
    backprompt_query+= f"Please check if this coloring is correct:" +response
    backprompt_query+= f"\nIf it is, say '{STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge."
    return backprompt_query

def sound_verify(instance):
    return check_coloring(instance[-1]["response"][-1], get_instance_text(instance[-1]["problem_id"]))[0]

def wrap_in_messages(s):
    return [{'role':'user', 'content':s}]

def backprompt(instance):
    backprompt_type = instance[-1]["backprompt_type"]
    verifier = backprompt_type["verifier"]
    critiquer = backprompt_type["critiquer"]
    critique_type = backprompt_type["critique_type"]
    history_len = backprompt_type["history_len"]
    history_type = backprompt_type["history_type"]
    # check if llm prompting, if so, check which portion we're in (generation or verification/critique)
    jump = 1
    if (verifier == "llm" or critiquer == "llm"):
        if len(instance)%2: return wrap_in_messages(generate_verification_prompt(instance))
        jump = 2
    # check verification and stop if it says to
    if verifier == "sound" and sound_verify(instance): return wrap_in_messages("stop10002")
    elif verifier == "llm" and parse_messy_json(instance[-1]["response"])["correct"]: return wrap_in_messages("stop10002")
    # check if 0 history length
    if history_len == 0: return wrap_in_messages(instance[0]["prompt"])
    # then generate critique
    if critiquer == "llm":
        reasons = extract_critique_from_llm_response(instance[-1]["response"], get_instance_text(instance[-1]["problem_id"]))
    elif critiquer == "sound":
        _, reasons = check_coloring(instance[-1]["response"], get_instance_text(instance[-1]["problem_id"]))
    else: raise NotImplementedError()
    # and put it together, with amount of detail specified
    if critique_type == "full":
        critique = "\n".join(reasons)
    elif critique_type == "first":
        critique = reasons[0]
    else: raise NotImplementedError()
    new_portion = [{'role':'assistant', 'content':instance[-jump]["response"]}] + wrap_in_messages(f"This is incorrect. Feedback:\n{critique}\n\nUsing this feedback, please try again. {DEFAULT_PROMPT_END}")
    # then concatenate history properly
    initial_prompt = [instance[0]["prompt"][0]]
    if history_type == "full":
        if history_len == 1: backprompt = initial_prompt + new_portion
        else: backprompt = initial_prompt + instance[-jump]["prompt"][1:][-jump*(history_len-1):] + new_portion
    else: raise NotImplementedError()
    return backprompt

# generate function
def generate_instances(start, end, total_nodes): #TODO make this num instead
    instances = {}
    for x in range(start, end+1):
        dimacs = ""
        graph = grinpy.to_edgelist(generate_random_graph(total_nodes, NEIGHBOR_P))
        dimacs = construct_dimacs(graph)
        dimacs += f"\nc {CHROMATIC_NUMBER_KEY}{optimal_coloring_number(dimacs)}"
        instances[x] = dimacs

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
    n_p = args.probability
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
            graph = grinpy.to_edgelist(generate_random_graph(total_nodes, n_p))
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
