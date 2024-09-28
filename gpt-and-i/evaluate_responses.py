import domain_utils
import utils
from fire import Fire
from rich import progress

def prepare_input(prompts, previous_output, llm, backprompt_type, temp, trial_id, num_iterations):
    #TODO refactor
    print(f">>Preparing LLM output...")
    #TODO save this work if already done and fast check it if it's been done before
    #     Can I read the jsonl file backwards and find where I last left off?
    input = []
    for key in prompts.keys():
        full_key_output = []
        furthest = -1
        for line in previous_output:
            if utils.check_spec(line, key, llm, backprompt_type, temp, trial_id):
                if line["prompt_num"] > num_iterations: continue
                full_key_output.append(line)
                if line["prompt_num"] > furthest:
                    furthest = line["prompt_num"]
        if furthest > -1:
            full_key_output = sorted(full_key_output, key=lambda x: x["prompt_num"])
            input.append(full_key_output)
    print(f">>Output reformatted for evaluation.")
    return input

def evaluate_per_instance(domain_name, input, verbose=False):
    dmn = domain_utils.get_domain(domain_name)
    evals = {}
    # {problem_id: 
    #   [{'correct': BOOL, 'verification_claim': BOOL}]
    # }
    for instance in input:
        if verbose: print(f">>Evaluating instance {instance[0]['problem_id']}.")
        evals[instance[0]["problem_id"]] = dmn.evaluate(instance)
    return evals

def print_stats(evaluated_data):
    flat_data = [e for instance in evaluated_data.values() for e in instance]
    instance_total = len(evaluated_data)
    print(f">>Number of instances: {instance_total}")
    print(f">>Number of generation prompts sent: {len(flat_data)} (Avg per instance: {len(flat_data)/instance_total})")
    correct_total = sum([e["correct"] for e in flat_data])
    print(f'>>Number of correct generations: {correct_total} (Avg per instance: {correct_total/instance_total})')
    verification_claim_total = sum([e["verification_claim"] for e in flat_data])
    print(f'>>Number of verifications stating TRUE: {verification_claim_total} (Avg per response: {verification_claim_total/len(flat_data)})')
    tp_total = sum([e["verification_claim"] and e["correct"] for e in flat_data])
    print(f'>>Number of TP verifications: {tp_total} (Avg per correct instance: {tp_total/correct_total})')
    fp_total = sum([e["verification_claim"] and not e["correct"] for e in flat_data])
    print(f'>>Number of FP verifications: {fp_total} (Avg per incorrect instance: {fp_total/(len(flat_data)-correct_total)})')
    initial_correct = sum([instance[0]["correct"] for instance in evaluated_data.values()])
    print(f'>>Initial accuracy: {100*initial_correct/instance_total:>5.2f}%')
    print(f'>>Final accuracy: {100*tp_total/instance_total:>5.2f}%')

    # TODO
    # print(f'[-] Critique evaluation not yet implemented.')
    # print(f'[-] Per instance and per prompt charting not yet implemented.')
    # get the per instance averages
    # correct, also prompts done per
    ## gen
    ## ver
    ## crit

    # get the per prompt num averages (with a chart over the number of prompts)
    ## gen
    ## ver
    ## crit
    return 100*initial_correct/instance_total, 100*tp_total/instance_total

def evaluate_plan(llm, domain_name, start=0, end=0, overwrite_previous=False, verbose=False, backprompt_type="", num_iterations=15, temp=1, trial_id=0):
    # TODO make this not re-evaluate every time (for speed?)
    prompts = utils.read_json(domain_name, overwrite_previous=False, data_type="prompts")
    if end > start: prompts = {str(x) : prompts[str(x)] for x in range(start, end+1)}
    # utils.update_format_to_jsonl(domain_name, overwrite_previous, "responses", llm, backprompt_type, temp, trial_id, verbose)
    output = utils.read_jsonl(domain_name, "responses", llm, verbose)
    b_types = []
    for line in output:
        if line["backprompt_type"] not in b_types: b_types.append(line["backprompt_type"])
    print(f">>Backprompt_types with data available: {b_types}")
    
    # the following calculates the cost across ALL experiments
    # total_cost = sum([utils.calculate_token_cost(llm, x["response_object"]["usage"]["prompt_tokens"], x["response_object"]["usage"]["completion_tokens"]) for x in output])

    print(f">>Loaded {len(output)} responses.")
    # TODO this is a hack, and really slow, just use pandas
    if backprompt_type == "all":
        all_b_types = {}
        for b_type in b_types:
            print(f">Evaluating {len(prompts)} instances with backprompt type {b_type}.")
            input = prepare_input(prompts, output, llm, b_type, temp, trial_id, num_iterations)
            evaluated_data = evaluate_per_instance(domain_name, input, verbose)
            print(f">Stats for backprompt type {b_type}:")
            all_b_types[b_type] = print_stats(evaluated_data)
        print(f"> b_type chart:")
        for b_type in all_b_types.keys():
            print(f"{all_b_types[b_type][0]:>5.2f}% -> {all_b_types[b_type][1]:>5.2f}% ({b_type})")
    else: 
        input = prepare_input(prompts, output, llm, backprompt_type, temp, trial_id, num_iterations)
        print(f">>Evaluating {len(prompts)} instances.")
        evaluated_data = evaluate_per_instance(domain_name, input, verbose)
        print_stats(evaluated_data)

if __name__=="__main__":
    Fire(evaluate_plan)