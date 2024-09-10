import matplotlib.pyplot as plt
import json

with open("stats.json", "r") as fp:
        all_stats = json.load(fp)

'''
legend = []
for variety in all_stats:
    trial_stats = all_stats[variety]["trial_stats"]
    trial_nums = list(range(0,16))
    trial_stats_summed = {}
    for x in range(0,16):
        print(x)
        trial_stats_summed[x] = sum([trial_stats[y] for y in trial_stats if int(y) < x])
    correct_at_trial = list(trial_stats_summed.values())
    linestyle = "-"
    if "top" in variety:
         linestyle = "--"
    plt.plot(trial_nums,correct_at_trial, linestyle=linestyle)
    legend.append(variety)
plt.legend(legend)
plt.ylabel("# Instances Correct")
plt.xlabel("Trial #")
plt.show()
'''

'''
legend = []
for variety in all_stats:
    trial_stats = all_stats[variety]["trial_stats"]
    trial_nums = list(range(0,16))
    trial_stats_summed = {}
    for x in range(0,16):
        print(x)
        trial_stats_summed[x] = trial_stats[str(x)] if str(x) in trial_stats else 0 
    correct_at_trial = list(trial_stats_summed.values())
    linestyle = "-"
    if "top" in variety:
         linestyle = "--"
    plt.plot(trial_nums,correct_at_trial, linestyle=linestyle)
    legend.append(variety)
plt.legend(legend)
plt.ylabel("# Instances Correct")
plt.xlabel("Trial #")
plt.show()
'''

'''
instances = list(range(1,101))
legend = []

for variety in all_stats:
    evals = all_stats[variety]["evals"]
    num_backprompts = [evals[instance]["number of backprompts"] for instance in evals]
    legend.append(variety)
    plt.scatter(instances, num_backprompts, s=3)
plt.legend(legend, bbox_to_anchor=(1.05, 1.0), loc='upper left')
plt.show()
'''


'''
instances = list(range(1,101))
legend = []

sum_correct = [0]*100
for variety in all_stats:
    evals = all_stats[variety]["evals"]
    sum_correct = [sum_correct[int(instance)-1] + int(evals[instance]["ever correct"]) for instance in evals]
sumsum = {x: sum_correct.count(x) for x in sum_correct}
sumsum = {x: sumsum[x] for x in sorted(list(sumsum.keys()))}
print(sumsum)
print(all_stats.keys())
plt.bar(range(0,6), sumsum.values())
plt.ylabel("Number of Instances")
plt.xlabel("Number of Techniques Solving Correctly")
#plt.bar(instances, sum_correct)
plt.show()
'''

'''
back_nums = []
for variety in all_stats:
    back_num = 0
    evals = all_stats[variety]["evals"]
    for instance in evals:
        back_num+=evals[instance]["number of backprompts"]
    back_nums.append(back_num/100)
plt.bar(all_stats.keys(), back_nums)
plt.show()
'''

'''
back_nums = []
for variety in all_stats:
    back_num = 0
    total = 0
    evals = all_stats[variety]["evals"]
    for instance in evals:
        back_num+=evals[instance]["number of backprompts before correct"]
        total+=1 if evals[instance]["ever correct"] else 0
    back_nums.append(back_num/total)
plt.bar(all_stats.keys(), back_nums)
plt.show()
'''

plt.figure(dpi=300,layout="constrained")
varieties = ["Direct\n(No Backprompt)", "LLM\nSelf-Critique", "External Verifier\nPass/Fail", "External Verifier\nFirst Error", "External Verifier\nAll Errors"]
varieties_codes = ["graph_coloring-llm-gpt-4_chat", "graph_coloring-passfail-gpt-4_chat","graph_coloring-first-gpt-4_chat","graph_coloring-full-gpt-4_chat"]
performance = [16]
for variety in varieties_codes:
    some_key = list(all_stats[variety]["stats"].keys())[0]
    overall_stats = {y:sum([all_stats[variety]["stats"][x][y] for x in all_stats[variety]["stats"].keys()]) for y in all_stats[variety]["stats"][some_key].keys()}
    performance.append(overall_stats["correct"])
plt.bar(varieties, performance)
plt.ylim(top=50)
current_values = plt.gca().get_yticks()
plt.gca().set_yticklabels([f"{int(x)}%" for x in current_values])
plt.ylabel("Percent Correct When Stopped")
plt.xlabel("Type of Backprompt")
plt.xticks(fontsize=9)
plt.title("Performance Across Backprompting Regimes")
plt.savefig("/home/kaya/yochan/paper_assets/csp-llm/correct_for_backprompt.png")
print("Saved.")


plt.figure(dpi=300,layout="constrained")
varieties = ["Top 15\nt=1.0", "Top 5\nt=0.5", "Top 5\nt=1.0", "Top 5\nt=1.5"]
varieties_codes = ["graph_coloring-15top1-gpt-4_chat","graph_coloring-05top0.5-gpt-4_chat","graph_coloring-05top1-gpt-4_chat","graph_coloring-05top1.5-gpt-4_chat"]
performance = []
for variety in varieties_codes:
    some_key = list(all_stats[variety]["stats"].keys())[0]
    overall_stats = {y:sum([all_stats[variety]["stats"][x][y] for x in all_stats[variety]["stats"].keys()]) for y in all_stats[variety]["stats"][some_key].keys()}
    performance.append(overall_stats["ever correct"])
plt.bar(varieties, performance)
plt.ylim(top=50)
current_values = plt.gca().get_yticks()
plt.gca().set_yticklabels([f"{int(x)}%" for x in current_values])
plt.ylabel("Percent of Instances with a Correct Answer")
plt.xlabel("Number of Samples and Sampling Temperature")
plt.title("Performance Across Sampling Regimes")
plt.xticks(fontsize=9)
plt.savefig("/home/kaya/yochan/paper_assets/csp-llm/correct_for_top.png")
print("Saved.")
