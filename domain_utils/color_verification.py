try: 
    from domain_utils import graph_coloring
except:
    import graph_coloring
import os
import grinpy
import argparse
import random
import json
import re

COLOR_VERIFICATION_DIRECTORY = "../data/color_verification/"

NON_OPT_PHRASE = "This coloring is non-optimal."
MISSING_PHRASE = "Missing assignment."


def file_ending():
    return ".col"

def generate(instance_text, problem_type):
    # format (stored in data/color_verification) is graph instance with comments appended giving colorings of various types
    if "-cot" in problem_type:
        problem_type = problem_type.split("-cot")[0]
        if problem_type not in instance_text:
            print(f"There is no {problem_type} key in {instance_text}")
        coloring_text = instance_text.split(f"c {problem_type}")[1].split("\n")[0].replace("\\n","\n")
        return generate_cot_prompt(instance_text)
    if problem_type not in instance_text:
        print(f"There is no {problem_type} key in {instance_text}")
    coloring_text = instance_text.split(f"c {problem_type}")[1].split("\n")[0].replace("\\n","\n")
    prompt = f"The following graph, described as a set of edges, has an optimal coloring number of {graph_coloring.optimal_coloring_number(instance_text)}:\n"
    _, graph_text = graph_coloring.generate_graph(instance_text)
    prompt+= graph_text
    prompt+= f"A coloring is correct if no adjacent vertices are the same color and the total number of colors used is no more than the optimal coloring number. Please check if this coloring is correct: {coloring_text}"
    prompt+= f"\nIf it is, say '{graph_coloring.STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge. If there are none, but it uses too many colors say '{NON_OPT_PHRASE}' Do not provide anything else in your response. If the color of a vertex is not given in the coloring, say '{MISSING_PHRASE}' Do not provide anything else in your response."
    return prompt

def generate_cot_prompt(instance_text, coloring_text):
    prompt = ''
    prompt+= '\n[Instructions]\nWhen outputting your final answer, first print the [Answer] tag, then put your final answer after the [Answer] tag. Respond only in the following format:\nWrong Edges: a list of incorrect edges\nAll Vertices Colored: boolean representing if every vertex is colored\nOptimal Or Less: boolean representing if the number of colors is no more than the optimal\nCorrect: boolean'
    prompt+= f"\n\n[Graph]\nThe following graph, described as a set of edges, has an optimal coloring number of {graph_coloring.optimal_coloring_number(instance_text)}:\n"
    _, graph_text = graph_coloring.generate_graph(instance_text)
    prompt+= graph_text
    prompt+= f"\n[Coloring]\nA coloring is correct if no adjacent vertices are the same color and the total number of colors used is no more than the optimal coloring number. Please check if this coloring is correct: {coloring_text}"
    prompt+= f"\n\nLet's think step by step. Remember to output your final answer in the format described in the instructions.\n[Thoughts]"
    return prompt

def evaluate(instance_text, response_trace, problem_type="", backprompt_type=""):
    STOP_PHRASE = graph_coloring.STOP_PHRASE
    evaluation = {"num prompts": 1}
    coloring_text = instance_text.split(problem_type.split('-cot')[0])[1].split("\n")[0].replace("\\n","\n").strip()
    if "-cot" in problem_type:
        messy_json = parse_messy_json(response_trace["responses"][-1])
        claim = messy_json['correct']
    else: claim = STOP_PHRASE in response_trace["responses"][-1]
    ground_truth = graph_coloring.check_coloring(coloring_text, instance_text.split('c correct')[0])
    evaluation["correct"] = ground_truth[0] is claim
    evaluation["ground truth"] = ground_truth[0]
    evaluation["TP"] = ground_truth[0] and claim
    evaluation["FN"] = ground_truth[0] and not claim
    evaluation["TN"] = not ground_truth[0] and not claim
    evaluation["FP"] = not ground_truth[0] and claim
    evaluation["output token cost"] = len(response_trace["responses"][-1])
    evaluation["input token cost"] = len(response_trace["prompts"][-1])
    return [evaluation]

def parse_messy_json(response_raw):
    try: response = response_raw.split("[Answer]")[1].lower()
    except: 
        try: response = response_raw.split("final answer is:")[1].lower()
        except: raise ValueError(response_raw)
    # print(response)
    wrong_edges = response.split('wrong edges:')[1].split('\n')[0].strip().replace("(","[").replace(")","]")
    all_verts = response.split('all vertices colored:')[1].split('\n')[0].strip()
    optimal_or_less = response.split('optimal or less:')[1].split('\n')[0].strip()
    correct = response.split('correct:')[1].split('\n')[0].strip()
    messy_json_string = '{"wrong_edges": '+wrong_edges+', "all_verts":'+all_verts+', "opt":'+optimal_or_less+', "correct":'+correct+'}'
    return json.loads(messy_json_string)

def backprompt(instance_text, model_response, backprompt_type):
    raise NotImplementedError("No backprompting for color verification")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-s','--start', type=int, default=1, help='start index')
    parser.add_argument('-e', '--end', type=int, default=100, help='end index')
    args = parser.parse_args()
    start = args.start
    end = args.end
    print(f"Generating correct colorings from all instances in {graph_coloring.GRAPH_COLORING_DIRECTORY}")
    for instance in os.listdir(graph_coloring.GRAPH_COLORING_DIRECTORY):
        if instance.startswith("instance-"):
            with open(graph_coloring.GRAPH_COLORING_DIRECTORY+instance,"r") as fp:
                instance_text = fp.read()
            print(instance)
            chromatic_number = graph_coloring.optimal_coloring_number(instance_text)
            graph = grinpy.Graph(graph_coloring.parse_dimacs(instance_text))
            #correct coloring
            correct_coloring = grinpy.greedy_color(graph)
            coloring_text = ""
            for x in correct_coloring:
                coloring_text+=f"{x}: Color {correct_coloring[x]}\n"
            while graph_coloring.check_coloring(coloring_text, instance_text):
                coloring_text = ""
                correct_coloring = grinpy.greedy_color(graph, strategy="random_sequential")
                for x in correct_coloring:
                    coloring_text+=f"{x}: {correct_coloring[x]}\n"
            int_keys = [int(x) for x in correct_coloring.keys()]
            correct_coloring = {str(x): correct_coloring[str(x)] for x in sorted(int_keys)}
            coloring_text = ""
            for x in correct_coloring:
                    coloring_text+=f"{x}: Color {correct_coloring[x]}\n"
            print(f"correct: {not graph_coloring.check_coloring(coloring_text,instance_text)}")
            new_instance = f"{instance_text}\nc correct {repr(coloring_text)[1:-1]}"
            #ablated coloring
            coloring_text = ""
            ablation_vertex = random.choice(list(graph.nodes()))
            neighbor_vertex = random.choice(list(graph[str(ablation_vertex)]))
            neighbor_color = correct_coloring[neighbor_vertex]
            for x in correct_coloring:
                if x == ablation_vertex:
                    coloring_text+=f"{x}: Color {neighbor_color}\n"
                else: 
                    coloring_text+=f"{x}: Color {correct_coloring[x]}\n"
            print(f"ablated: {graph_coloring.check_coloring(coloring_text,instance_text)}")
            new_instance+= f"\nc ablated {repr(coloring_text)[1:-1]}"
            #non-optimal coloring
            coloring_text = ""
            ruin_subset = []
            while ruin_subset == []:
                ruin_color = random.choice(list(correct_coloring.values()))
                color_subset = [v for v in correct_coloring if correct_coloring[v] == ruin_color]
                ruin_subset = random.sample(color_subset, int(len(color_subset)/2))
            ruin_color = max(list(correct_coloring.values()))+1
            for x in correct_coloring:
                if x in ruin_subset:
                    coloring_text+=f"{x}: Color {ruin_color}\n"
                else: 
                    coloring_text+=f"{x}: Color {correct_coloring[x]}\n"
            print(f"non-optimal: {graph_coloring.check_coloring(coloring_text, instance_text)}")
            new_instance+= f"\nc non-optimal {repr(coloring_text)[1:-1]}"
            #random coloring
            coloring_text = ""
            for x in correct_coloring:
                coloring_text+=f"{x}: Color {random.randrange(0, int(chromatic_number))}\n"
            print(f"random: {graph_coloring.check_coloring(coloring_text, instance_text)}")
            new_instance+=f"\nc random {repr(coloring_text)[1:-1]}"
            #TODO llm: for an instance, look at passfail set, randomly choose a response from og to whatever max
            # FIRST: check that the llm actually evaluated that 
            coloring_text = ""
            llm_directory = "../responses/graph_coloring/gpt-4_chat/backprompting-full/"
            with open(f"{llm_directory}responses.json", "r") as fp:
                output = json.load(fp)
            llm_max_n = 100
            instance_num = int(instance.split("-")[1].split(".col")[0])
            if instance_num <= llm_max_n:
                responses = [output[str(instance_num)][x] for x in output[str(instance_num)] if "response" in x]
            coloring_text = random.choice(responses)
            print(f"llm: {graph_coloring.check_coloring(coloring_text, instance_text)}")
            new_instance+=f"\nc llm {repr(coloring_text)[1:-1]}"
            with open(COLOR_VERIFICATION_DIRECTORY+instance, "w") as fp:
                fp.write(new_instance)