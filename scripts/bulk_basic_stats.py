import response_evaluation
import argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        ')
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to evaluate within')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('-i', '--ignore_existing', action='store_true', help='Ignore existing output')
    parser.add_argument('-b', '--backprompting', nargs='+', type=str, default=[], help='If multiprompting, provide the types of multiprompt to pass to the domain. Common types: zero, passfail, full, llm, top')
    parser.add_argument('-n', '--end_number', type=int, default=0, help='For running from instance m to n')
    parser.add_argument('-m', '--start_number', type=int, default=1, help='For running from instance m to n. You must specify -n for this to work')
    parser.add_argument('-t', '--temperature', type=float, default=0, help='Temperature from 0.0 to 2.0')
    parser.add_argument('-p', '--problem', type=str, default='', help='If doing a domain subproblem, specify it here')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    specified_instances = args.specific_instances
    specified_instances = args.specific_instances
    verbose = args.verbose
    backprompts = args.backprompting
    ignore_existing = args.ignore_existing
    end_number = args.end_number
    start_number = args.start_number
    problem_type = args.problem
    temperature = args.temperature
    if end_number>0 and specified_instances:
        print("You can't use both -s and -n")
    elif end_number>0:
        specified_instances = list(range(start_number,end_number+1))
        print(f"Running instances from {start_number} to {end_number}")
    print(f"Engine: {engine}, Domain: {domain_name}, Verbose: {verbose}" )
    sp = {}
    spa = {}
    for backprompt in backprompts:
        sp[backprompt], spa[backprompt] = response_evaluation.evaluate_plan(engine, domain_name, specified_instances, ignore_existing, verbose, backprompt, problem_type=problem_type, temp=temperature)
    print(sp)
    print(spa)
    sp2 = {x: sp[x]["correct"] for x in sp}
    costs = {x: sp[x]["token cost"] for x in sp}
    ever_creditors = ["list-previous"]
    for x in ever_creditors:
        if x in sp: sp2[x] = sp[x]["ever correct"]
    if "llm" in sp: sp2["llm (ever)"] = sp["llm"]["ever correct"]
    if "llm-passfail" in sp: sp2["llm-passfail (ever)"] = sp["llm-passfail"]["ever correct"]
    try: 
        x, _ = response_evaluation.evaluate_plan(engine, domain_name, specified_instances, ignore_existing, verbose, "top", problem_type=problem_type, temp=1.0)
        print(x)
        costs["top-temp1.0"] = x["token cost"]
        sp2["top-temp1.0"] = x["ever correct"]
    except: pass
    print(sp2)
    print(costs)