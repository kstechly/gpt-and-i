import os
import argparse
import json
from tqdm import tqdm
import domain_utils
from domain_utils import *
import matplotlib.pyplot as plt

def sum_dict(dictionary):
    summed_dictionary = {}
    for key in dictionary:
        for subkey in dictionary[key]:
            try: a = int(dictionary[key][subkey])
            except: continue
            if subkey not in summed_dictionary:
                summed_dictionary[subkey] = 0
            summed_dictionary[subkey] += int(dictionary[key][subkey])
    return summed_dictionary


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        \n davinci = GPT-3 Davinci \
                        \n curie = GPT-3 Curie \
                        \n babbage = GPT-3 Babbage \
                        \n ada = GPT-3 Ada \
                        ')
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to evaluate within')
    parser.add_argument('-b', '--backprompting', type=str, default='', help='If backprompting, provide the type of backprompt to pass to the domain. Common types: zero, passfail, full, llm')
    parser.add_argument('-p', '--problem', type=str, default='', help='If doing a domain subproblem, specify it here')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    problem_type = args.problem
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    backprompting = args.backprompting
    #print(f"Engine: {engine}, Domain: {domain_name}, Backprompting: {bool(backprompting)}" )

    evals_dir = f"evaluations/{domain_name}/{engine}/"
    if backprompting:
        evals_dir+=f"backprompting-{backprompting}/"
    if problem_type:
        evals_dir+=f"{problem_type}/"
    evals_json = evals_dir+"evaluations.json"
    if os.path.exists(evals_json):
        with open(evals_json, 'r') as file:
            evals = json.load(file)
    else: print("You have to run response_evaluation.py first")

    if domain_name == "graph_coloring":
        stats = sum_dict(evals)
        print(stats)
        vert_stats = sum([stats[x] for x in stats if "vertex change" in x])
        print(f"vert: {vert_stats}")
        print(f"edges: {sum([stats[x] for x in stats if 'edge corrected' in x])}")
        print(f"b-prompts: {stats['number of backprompts']}")
        edge_avgs = []
        response_edges_total = {}
        for instance in evals:
            for n in range(0,evals[instance]["number of backprompts"]):
                if f"backprompt {n} number of edges" in evals[instance]:
                    edge_avgs.append(evals[instance][f"backprompt {n} edge corrected"]/evals[instance][f"backprompt {n} number of edges"])
                if f"response {n} edges wrong" in evals[instance]:
                    if f"response {n} edges wrong" not in response_edges_total:
                        response_edges_total[f"response {n} edges wrong"] = 0
                    response_edges_total[f"response {n} edges wrong"] += 1
        print(sum(edge_avgs)/len(edge_avgs))
        print(response_edges_total)
        for x in response_edges_total:
            print(f"{x}: {stats[x]/response_edges_total[x]}")


    #if domain_name == "graph_coloring":
    if False:
        stats ={}
        for instance in evals:
            vertex_num = evals[instance]["number of nodes"]
            if vertex_num not in stats:
                stats[vertex_num] = {x:0 for x in evals[instance].keys() if "response" not in x}
                stats[vertex_num]["total instances"] = 0
            stats[vertex_num] = {x:stats[vertex_num][x]+int(evals[instance][x]) for x in evals[instance].keys() if "response" not in x}|{"total instances":stats[vertex_num]["total instances"]+1}

        correct_stats ={}
        
        for instance in evals:
            if evals[instance]["correct"]:
                vertex_num = evals[instance]["number of nodes"]
                if vertex_num not in correct_stats:
                    correct_stats[vertex_num] = {x:0 for x in evals[instance].keys() if "response" not in x}
                    correct_stats[vertex_num]["total instances"] = 0
                correct_stats[vertex_num] = {x:correct_stats[vertex_num][x]+int(evals[instance][x]) for x in evals[instance].keys() if "response" not in x}|{"total instances":correct_stats[vertex_num]["total instances"]+1}
                
        trial_stats = {}
        for instance in evals:
            if evals[instance]["ever correct"]:        
                for x in evals[instance]:
                    if "response" in x:
                        if x == "response":
                            check_trial = evals[instance][f"response"]
                            trial_num = 0
                        else:
                            trial_num = int(x[-2:])+1
                            check_trial = evals[instance][f"response {trial_num-1}"]
                            if "top" in backprompting:
                                trial_num-=1
                        if trial_num not in trial_stats:
                            trial_stats[trial_num] = 0
                        if check_trial:
                            trial_stats[trial_num]+=1
                            break
        trial_stats_summed = {}
        for x in trial_stats:
            trial_stats_summed[x] = sum([trial_stats[y] for y in trial_stats if y < x])
        '''
        formatted = str([f"&{total_instances[x]}" for x in total_correct])
        formatted += f"&{sum(total_instances.values())}\\\\"
        print(formatted)
        formatted = ""
        for x in total_correct:
            formatted+=f"&{total_correct[x]} ({int(total_correct[x]/total_instances[x]*100)}\%)"
        formatted += f"&{sum(total_correct.values())}\\\\"
        print(formatted)
        print(errors)'''

        '''
        average_stats = {node_number: {x: stats[node_number][x]/stats[node_number]["total instances"] for x in stats[node_number].keys()} for node_number in stats.keys() if stats[node_number]["total instances"]>0}
        average_correct_stats = {node_number: {x: correct_stats[node_number][x]/correct_stats[node_number]["total instances"] for x in correct_stats[node_number].keys()} for node_number in correct_stats.keys() if correct_stats[node_number]["total instances"]>0}
        print(f"avg stats: {average_stats}")
        print(f"\nAVG COR STATS: {average_correct_stats}")
        print(f"\nSTATS: {stats}")
        some_key = list(correct_stats.keys())[0]
        overall_stats = {y:sum([stats[x][y] for x in stats.keys()]) for y in stats[some_key].keys()}
        print(f"\nOverall stats: {overall_stats}")

        some_key = list(correct_stats.keys())[0]
        overall_correct_stats = {y:sum([correct_stats[x][y] for x in correct_stats.keys()]) for y in correct_stats[some_key].keys()}
        print(overall_correct_stats)
        average_overall_correct = {x : overall_correct_stats[x]/overall_correct_stats["total instances"] for x in overall_correct_stats.keys()}
        print(average_overall_correct)

        keys = list(stats.keys())
        keys.sort()
        stats = {x: stats[x] for x in keys}
        formatted = "".join([f"&{stats[x]['correct']} ({int(100*stats[x]['correct']/stats[x]['total instances'])}\%)" for x in stats])
        formatted += f"&{overall_correct_stats['correct']}\\\\"
        print(formatted)
        '''

        trial_nums = list(trial_stats.keys())
        correct_at_trial = list(trial_stats_summed.values())
        plt.plot(trial_nums,correct_at_trial)
        ax = plt.gca()
        ax.spines['bottom'].set_position(('data', 0))
        ax.spines['left'].set_position(('data', 0))
        #plt.show()

        all_stats = {}
        all_stats["trial_stats"] = trial_stats
        all_stats["stats"] = stats
        all_stats["correct_stats"] = correct_stats


        all_stats = {}
        with open("stats.json", "r") as fp:
            all_stats = json.load(fp)

        all_stats[f"{domain_name}-{backprompting}-{engine}"] = {}
        all_stats[f"{domain_name}-{backprompting}-{engine}"]["trial_stats"] = trial_stats
        all_stats[f"{domain_name}-{backprompting}-{engine}"]["stats"] = stats
        all_stats[f"{domain_name}-{backprompting}-{engine}"]["correct_stats"] = correct_stats
        all_stats[f"{domain_name}-{backprompting}-{engine}"]["evals"] = evals

        with open("stats.json", "w") as fp:
            json.dump(all_stats, fp, indent=4)

    elif domain_name == "color_verification":
        problem_types = ["correct", "ablated", "non-optimal", "random", "llm"]
        overall = {"total":0}
        overall["actually correct"] = 0
        bool_overall = {"total":0}
        bool_overall["actually correct"] = 0
        overall["coloring evaluation"] = {}
        bool_overall["coloring evaluation"] = {}
        all_stats = {}
        for problem_type in problem_types:
            evals_dir = f"evaluations/{domain_name}/{engine}/{problem_type}/"
            evals_json = evals_dir+"evaluations.json"
            if os.path.exists(evals_json):
                with open(evals_json, 'r') as file:
                    evals = json.load(file)
            totals = {"total":0}
            totals["actually correct"] = 0
            bool_totals = {"total":0}
            bool_totals["actually correct"] = 0
            totals["no hallucinations"]=0
            bool_totals["no hallucinations"]=0
            totals["coloring evaluation"] = {}
            bool_totals["coloring evaluation"] = {}
            for instance in evals:
                totals["total"]+=1
                bool_totals["total"]+=1
                overall["total"]+=1
                bool_overall["total"]+=1
                for key in evals[instance]:
                    if key == "coloring evaluation":
                        for subkey in evals[instance]["coloring evaluation"]:
                            if subkey not in totals["coloring evaluation"]:
                                totals["coloring evaluation"][subkey] = 0
                                bool_totals["coloring evaluation"][subkey] = 0
                            if subkey not in overall["coloring evaluation"]:
                                overall["coloring evaluation"][subkey] = 0
                                bool_overall["coloring evaluation"][subkey] = 0
                            totals["coloring evaluation"][subkey]+=int(evals[instance]["coloring evaluation"][subkey])
                            bool_totals["coloring evaluation"][subkey]+=int(bool(evals[instance]["coloring evaluation"][subkey]))
                            overall["coloring evaluation"][subkey]+=int(evals[instance]["coloring evaluation"][subkey])
                            bool_overall["coloring evaluation"][subkey]+=int(bool(evals[instance]["coloring evaluation"][subkey]))
                        continue
                    if key not in totals:
                        totals[key] = 0
                        bool_totals[key] = 0
                    if key not in overall:
                        overall[key] = 0
                        bool_overall[key] = 0
                    totals[key]+=int(evals[instance][key])
                    bool_totals[key]+=int(bool(evals[instance][key]))
                    overall[key]+=int(evals[instance][key])
                    bool_overall[key]+=int(bool(evals[instance][key]))
                if evals[instance]["edge hallucination"] and evals[instance]["vertex color hallucination"]:
                    if "both hallucinations" not in totals:
                        totals["both hallucinations"] = 0
                        bool_totals["both hallucinations"] = 0
                    if "both hallucinations" not in overall:
                        overall["both hallucinations"] = 0
                        bool_overall["both hallucinations"] = 0
                    totals["both hallucinations"]+=1
                    bool_totals["both hallucinations"]+=1
                    overall["both hallucinations"]+=1
                    bool_overall["both hallucinations"]+=1
                if not evals[instance]["edge hallucination"] and not evals[instance]["vertex color hallucination"]:
                    if "no hallucinations" not in overall:
                        overall["no hallucinations"] = 0
                        bool_overall["no hallucinations"] = 0
                    totals["no hallucinations"]+=1
                    bool_totals["no hallucinations"]+=1
                    overall["no hallucinations"]+=1
                    bool_overall["no hallucinations"]+=1
                    if evals[instance]["correct"]:
                        totals["actually correct"]+=1
                        bool_totals["actually correct"]+=1
                        overall["actually correct"] +=1
                        bool_overall["actually correct"] +=1
            all_stats[problem_type] = {"totals": totals, "bool_totals": bool_totals}
            print(problem_type)
            print(totals)
            print(bool_totals)
        print("----")
        print(overall)
        print(bool_overall)

        for x in all_stats:
            errors = all_stats[x]["totals"]["coloring evaluation"]["number of errors"]
            actually_correct = all_stats[x]["totals"]["actually correct"]
            print(f"{x}: {actually_correct} for {errors} errors")