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
    if problem_type not in instance_text:
        print(f"There is no {problem_type} key in {instance_text}")
    coloring_text = instance_text.split(f"c {problem_type}")[1].split("\n")[0].replace("\\n","\n")
    prompt = f"The following graph, described as a set of edges, has an optimal coloring number of {graph_coloring.optimal_coloring_number(instance_text)}:\n"
    _, graph_text = graph_coloring.generate_graph(instance_text)
    prompt+= graph_text
    prompt+= f"A coloring is correct if no adjacent vertices are the same color and the total number of colors used is no more than the optimal coloring number. Please check if this coloring is correct: {coloring_text}"
    prompt+= f"\nIf it is, say '{graph_coloring.STOP_PHRASE}' Do not provide anything else in your response. If it is incorrect, please point out which same-color vertices share an edge. If there are none, but it uses too many colors say '{NON_OPT_PHRASE}' Do not provide anything else in your response. If the color of a vertex is not given in the coloring, say '{MISSING_PHRASE}' Do not provide anything else in your response."
    return prompt

def evaluate(instance_text, response_trace, problem_type=""):
    #TODO
    # .lower().replace(".","")
    evaluation = {}
    STOP_PHRASE = graph_coloring.STOP_PHRASE
    response = response_trace["response"]
    coloring_text = instance_text.split(problem_type)[1].split("\n")[0].replace("\\n","\n").strip()

    fake_trace = {"response":coloring_text}
    coloring_evaluation = graph_coloring.evaluate(instance_text, fake_trace)
    evaluation["coloring evaluation"] = coloring_evaluation

    edges = graph_coloring.parse_dimacs(instance_text)

    coloring = {}
    for line in coloring_text.split("\n"):
        assignment = line.strip().split(": ")
        if len(assignment) < 2:
            continue
        vertex_number = assignment[0]
        color = assignment[1]
        coloring[vertex_number] = color

    #I HAVE TO KNOW WHICH TYPE IT WAS?? or pass the right instance

    # check for one of the key phrases first, THEN
    # separate into sentences. loop over them
    # extract "color n" substrings, all other contiguous digits should be separate vertices
    # except INSTANCE 74, which went crazy
    # this is a typology of errors
    # hallucinations: edges, colors
    evaluation["correct"] = False
    evaluation["ever correct"] = False
    evaluation["stopped"] = False
    evaluation["stopped correctly"] = False
    evaluation["non-opted"] = False
    evaluation["non-opted correctly"] = False
    evaluation["missinged"] = False
    evaluation["missinged correctly"] = False
    evaluation["malformed"] = False
    evaluation["confused edge"] = False
    evaluation["edge hallucination"] = 0
    evaluation["vertex color hallucination"] = 0
    evaluation["colorless edges"] = 0
    evaluation["number of edges mentioned"] = 0
    if STOP_PHRASE.lower().replace(".","") in response.lower():
        evaluation["stopped"] = True
        if coloring_evaluation["correct"]:
            evaluation["stopped correctly"] = True
            evaluation["correct"] = True
    elif NON_OPT_PHRASE.lower().replace(".","") in response.lower():
        evaluation["non-opted"] = True
        if coloring_evaluation["full coloring"] and not coloring_evaluation["correct"]:
            evaluation["non-opted correctly"] = True
            evaluation["correct"] = True
    elif MISSING_PHRASE.lower().replace(".","") in response.lower():
        evaluation["missinged"] = True
        if not coloring_evaluation["valid assignment"]:
            evaluation["missinged correctly"] = True
            evaluation["correct"] = True
    else:
        if not coloring_evaluation["correct"] and not coloring_evaluation["full coloring"] and not coloring_evaluation["valid assignment"]:
            evaluation["correct"] = True
        for sentence in response.split("."):
            if not sentence:
                continue
            color_number = None
            vert1_color = None
            vert2_color = None
            #check for malformed prompts
            if len(sentence.split("vert"))>3:
                if "This coloring is incorrect due" in sentence:
                    sentence = sentence.split("This coloring is incorrect due")[1]
                    print(f"funky split on {sentence}")
                else:
                    evaluation["malformed"] = True
                    print(f"malformed: {sentence}")
            else:
                #extract color
                #check for next sentence being "both are color n."
                color_substrings = sentence.lower().split('color')
                cleaned_color_substrings = [color_substrings[0]]
                if len(color_substrings)>1 and "same-color" not in sentence.lower():
                    color_substrings = color_substrings[1:]
                    #print(color_substrings)
                    for x in color_substrings:
                        y = re.search(r'(\d+)', x)
                        if y:
                            if color_number is not None and color_number is not y.group():
                                evaluation["confused edge"] = True
                                vert1_color = color_number
                                vert2_color = y.group()
                                #TODO check for this later when computing if it recognized the colors right
                            color_number = y.group()
                            if len(x.split(y.group(),1))>1:
                                cleaned_color_substrings.append(" ".join(x.split(y.group(),1)[1:]))
                        else: 
                            cleaned_color_substrings.append(x)
                    #print(f"Extracted color number: {color_number} from {sentence}")
                    if vert1_color is None:
                        vert1_color = color_number
                        vert2_color = color_number
                else:
                    #TODO check for next sentence "both are color n." case
                    print(f"colorless: {sentence}")
                #extract edge
                cleaned_sentence = " ".join(cleaned_color_substrings).lower()
                #print(sentence)

                #print(f"cleaned: {cleaned_sentence}")
                vertex_r = re.findall(r'\d+', cleaned_sentence)
                vertex_pair = list(vertex_r)
                if len(vertex_pair)==1:
                    if vert1_color is None:
                        evaluation["colorless edges"] +=1
                        print(f"no color: {sentence}")
                    elif vert1_color not in coloring[vertex_pair[0]]:
                        evaluation["vertex color hallucination"]+=1
                elif vertex_pair:
                    evaluation["number of edges mentioned"]+=1
                    #check if this edge exists
                    if vertex_pair not in edges:
                        evaluation["edge hallucination"] +=1
                    #check if verts are colored right
                    if vert1_color is None:
                        evaluation["colorless edges"] +=1
                        print(f"no color: {sentence}")
                    elif vert1_color not in coloring[vertex_pair[0]] or vert2_color not in coloring[vertex_pair[1]]:
                        evaluation["vertex color hallucination"] +=1

                #
                #compare edge
                #
                #calculate a list of most connected vertices
                #calculate where in that list the verts from the edge fall
                #calculate the connectivity of each vert in edge

        #one weighting: per response
        #another: per occurrence
        
        



        #stats I want:
        # is it the first edge?
        # does the edge even exist?
        # does it find a false missing assignment?

    #TODO
    return evaluation

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