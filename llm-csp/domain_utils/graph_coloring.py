DEFAULT_PROMPT_START = "Color the following graph, described as a set of edges, such that no two vertices on the same edge share a color.\n"
DEFAULT_PROMPT_END = "Please provide each vertex's color. Each color must be provided on a new line in the response and should be formatted as \"{VERTEX NUMBER}: {VERTEX COLOR ASSIGNMENT}\". Please do not provide anything else in your response."

import  grinpy

def parse_dimacs(instance_text):
    parsed = []
    print(instance_text)
    for line in instance_text.split("\n"):
        print(line)
        text = line.split(" ")
        if text[0] == "e":
            parsed.append((text[1],text[2]))
    return parsed
def optimal_coloring_number(instance_text):
    graph = grinpy.Graph(parse_dimacs(instance_text))
    return grinpy.chromatic_number(graph)
def check_coloring(coloring, instance_text):
    edges = parse_dimacs(instance_text)
    # check if coloring is valid
    for edge in edges:
        if coloring[edge[0]] == coloring[edge[1]]:
            return False
    # check if coloring is optimal
    if optimal_coloring_number(instance_text) == len(set(coloring.values)):
        return True
    else: return False

#### Required Functions

def file_ending():
    return ".col"

def generate(instance_text):
    prompt = DEFAULT_PROMPT_START
    prompt += f"You may use at most {optimal_coloring_number(instance_text)} colors.\n"
    for edge in parse_dimacs(instance_text):
        prompt += f"Vertex {edge[0]} is connected to vertex {edge[1]}.\n"
    prompt += DEFAULT_PROMPT_END
    return prompt  

def evaluate(instance_text,model_response):
    coloring = {}
    for line in model_response:
        assignment = line.strip().split(": ")
        vertex_number = assignment[0]
        color = assignment[1]
        coloring[vertex_number] = color
    return check_coloring(coloring, instance_text)