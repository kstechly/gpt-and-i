DEFAULT_PROMPT_START = "Color the following graph, described as a set of edges, such that no two vertices on the same edge share a color.\n"
DEFAULT_PROMPT_END = "Please provide each vertex's color. Each color must be provided on a new line in the response and should be formatted as \"{VERTEX NUMBER}: {VERTEX COLOR ASSIGNMENT}\". Please do not provide anything else in your response."

CHROMATIC_NUMBER_KEY = "OPTIMAL CHROMATIC NUMBER === "
GRAPH_COLORING_DIRECTORY = "../data/graph_coloring/"

INITIAL_NODES = 3
NEIGHBOR_P = .4
SOURCE_P = .2

import grinpy
import os
import argparse
import random

def parse_dimacs(instance_text):
    parsed = []
    for line in str(instance_text).split("\n"):
        text = line.split(" ")
        if text[0] == "e":
            parsed.append((text[1],text[2]))
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
def check_coloring(coloring, instance_text):
    edges = parse_dimacs(instance_text)
    # check if coloring is valid
    for edge in edges:
        if coloring[edge[0]] == coloring[edge[1]]:
            #print(f"{edge[0]}={coloring[edge[0]]} and {edge[1]}={coloring[edge[1]]}")
            return False
    # check if coloring is optimal
    if int(optimal_coloring_number(instance_text)) == len(set(coloring.values())):
        return True
    else: 
        return False

#### Required Functions

def file_ending():
    return ".col"

def generate(instance_text):
    prompt = DEFAULT_PROMPT_START
    prompt += f"You may use at most {optimal_coloring_number(instance_text)} colors.\n"
    vertices = []
    num_verts = 0
    min_vert = 1
    for edge in parse_dimacs(instance_text):
        prompt += f"Vertex {edge[0]} is connected to vertex {edge[1]}.\n"
        num_verts = max(num_verts, int(edge[0]),int(edge[1]))
        min_vert = min(min_vert, int(edge[0]), int(edge[1]))
    num_verts += (min_vert+1)%2
    prompt+=f"There are a total of {num_verts} vertices. Please label every vertex, even if it is disconnected from the rest of the graph."
    prompt += DEFAULT_PROMPT_END
    return prompt  

def evaluate(instance_text,model_response):
    coloring = {}
    for line in model_response.split("\n"):
        assignment = line.strip().split(": ")
        vertex_number = assignment[0]
        color = assignment[1]
        coloring[vertex_number] = color
    return check_coloring(coloring, instance_text)


#### Precompute and instance generation scripts
# WARNING: Only works from domain_utils directory

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('task', help='generate or chromatic'),
    parser.add_argument('-s','--start', type=int, default=1, help='start index')
    parser.add_argument('-e', '--end', type=int, default=100, help='end index')
    parser.add_argument('-t','--total', type=int, default=10, help='total number of nodes')
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
            seed = random.random()
            # TODO decide on the random graph generation procedure
            graph = grinpy.to_edgelist(grinpy.partial_duplication_graph(total_nodes, INITIAL_NODES, NEIGHBOR_P, SOURCE_P))
            dimacs = construct_dimacs(graph)
            dimacs += f"\nc {CHROMATIC_NUMBER_KEY}{optimal_coloring_number(dimacs)}"
            with open(destination, "w") as fp:
                fp.write(dimacs)
            print(dimacs)