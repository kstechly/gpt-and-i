from fire import Fire
from openai import OpenAI
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED
import domain_utils
import utils
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
import time
import json

MAX_GPT_RESPONSE_LENGTH = 1500
MAX_GPT_RESPONSE_LENGTH_SAFE = 300 #something to restrict output to if everything gets too long
MAX_BACKPROMPT_LENGTH = 15
STOP_PHRASE = "stop10002" # "Verifier confirmed success" # what the verifier has to say
STOP_STATEMENT = "[ANSWER END]" # what we look for to end LLM response generation
MAX_WORKERS = 100

input_costs_per_million  = {
    "gpt-4": 30,
    "gpt-4-0613": 30, 
    "gpt-4-turbo":10, 
    "gpt-4-turbo-2024-04-09": 10, 
    "gpt-3.5-turbo-0125": 0.5, 
    "gpt-4o-2024-05-13": 5, 
    "gpt-4o-mini-2024-07-18":0.15,
    "o1-preview":15}
output_costs_per_million = {
    "gpt-4": 60,
    "gpt-4-0613": 60, 
    "gpt-4-turbo":30, 
    "gpt-4-turbo-2024-04-09": 30, 
    "gpt-3.5-turbo-0125": 1.5, 
    "gpt-4o-2024-05-13": 15, 
    "gpt-4o-mini-2024-07-18": 0.6,
    "o1-preview":60}
input_costs_per_token = {llm: input_costs_per_million[llm]/10**6 for llm in input_costs_per_million}
output_costs_per_token = {llm: output_costs_per_million[llm]/10**6 for llm in output_costs_per_million}

def check_spec(line, key, llm, backprompt_type, temp, trial_num):
    return line["llm"] == llm and line["backprompt_type"] == backprompt_type and line["temp"] == temp and int(line["trial_num"]) == int(trial_num) and int(line["problem_id"]) == int(key)

def prepare_input(prompts, previous_output, llm, multiprompting, temp, trial_id, num_iterations):
    input = []
    for key in prompts.keys():
        furthest = -1
        full_key_output = []
        for line in previous_output:
            if check_spec(line, key, llm, multiprompting, temp, trial_id):
                full_key_output.append(line)
                if line["prompt_num"] > furthest:
                    furthest = line["prompt_num"]
                    furthest_stopped = line["stopped"]
                    if furthest +1 >= num_iterations: break
                if line["stopped"]: break
        if furthest == -1:
            input.append([{"problem_id":key, "trial_num":trial_id, "llm":llm, "backprompt_type":multiprompting, "temp":temp, "prompt_num":0, "prompt":prompts[key], "response":"", "converted_data":False, "stopped":False}])
        elif not furthest_stopped and furthest+1 < num_iterations:
            full_key_output = sorted(full_key_output, key=lambda x: x["prompt_num"])
            input.append(full_key_output)
    return input

def process_instance(instance, domain_name, verbose=False):
    dmn = domain_utils.get_domain(domain_name)
    # Note that we assume that instance is already sorted by prompt_num
    # and that it isn't stopped, nor has it reached the maximum number of iterations
    if not instance[-1]["response"]:
        if verbose: print(f">>Instance {instance[-1]['problem_id']} has never been seen before.==")
        prompt = instance[-1]["prompt"]
    else:
        if verbose: print(f">>Generating backprompt {instance[-1]['prompt_num']+1} for instance {instance[-1]['problem_id']}.==")
        prompt = dmn.backprompt(instance)
        if check_backprompt(prompt): #TODO get rid of this part
            instance[-1]["stopped"] = True
            return instance
    llm = instance[-1]["llm"]
    temp = instance[-1]["temp"]
    if verbose: print(f">>Instance {instance[-1]['problem_id']} is being processed with prompt:\n{prompt}")
    response, response_dict = send_query(prompt, llm, temp=temp)
    if not response: return None
    response_text = response.choices[0].message.content
    if verbose: print(f">>Response to instance {instance[-1]['problem_id']}:\n{response_text}")
    if not instance[-1]["response"]:
        instance[-1]["response"] = response_text
        instance[-1]["response_object"] = response_dict
    else:
        instance.append({**{k: instance[-1][k] for k in instance[-1].keys()-{'response', 'prompt', 'prompt_num', 'converted_data',
                                                                             'response_object', 'stopped'}},
            "prompt_num":instance[-1]["prompt_num"]+1, "prompt":prompt, "response":response_text, "converted_data":False, "response_object":response_dict, "stopped":False})
    if check_backprompt(dmn.backprompt(instance)): instance[-1]["stopped"] = True #TODO make a dedicated function for checking stopping
    return instance

def check_backprompt(backprompt):
    return STOP_PHRASE.lower() in backprompt.lower()

def send_query(query, llm, max_tokens=MAX_GPT_RESPONSE_LENGTH, temp=1):
    messages=[]
    messages.append({"role": "user", "content": query})
    try:
        client = OpenAI()
        start = time.time()
        response = client.chat.completions.create(model=llm, messages=messages, temperature=temp, stop="[ANSWER END]", max_tokens=max_tokens)
        end = time.time()
    except Exception as e:
        print("[-]: Failed OpenAI query execution: {}".format(e))
        return None, None
    response_dict = {**json.loads(response.model_dump_json()), "time": end-start}
    return response, response_dict

def get_responses(llm, domain_name, start=0, end=0, overwrite_previous=False, verbose=False, multiprompting="", num_iterations=15, temp=1, trial_id=0, max_cost=100):
    if llm not in input_costs_per_million:
        print(f"[-]: Invalid llm name. Must be one of {input_costs_per_million.keys()}.")
        return
    prompts = utils.read_json(domain_name, overwrite_previous=False, data_type="prompts")

    # Constrain work to only specified instances if flagged to do so
    if end > start: prompts = {str(x) : prompts[str(x)] for x in range(start, end+1)}
    print(f">>Checking {len(prompts)} instances for work to be done.")

    # convert to new format if it isn't already, then mark the file as old
    utils.update_format_to_jsonl(domain_name, overwrite_previous, "responses", llm, multiprompting, temp, trial_id, verbose)
    previous_output = utils.read_jsonl(domain_name, "responses", llm, verbose)

    # Create input of only instances that haven't been completed yet
    input = prepare_input(prompts, previous_output, llm, multiprompting, temp, trial_id, num_iterations)
    print(f">>Instances to be processed: {len(input)}")

    total_tasks = len(input)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        ) as progress:
        task = progress.add_task("[cyan]Processing... ($0.00 cost)", total=total_tasks)

        failed = 0
        cost = 0
        stopped = 0
        maxed_out = 0
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            print(f">>Deploying {min(MAX_WORKERS, total_tasks)} undergrads to process {total_tasks} instances.")
            futures = {executor.submit(process_instance, instance, domain_name, verbose) for instance in input}
            while futures and cost < max_cost:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    futures.remove(future)
                    new_instance = future.result()
                    if not new_instance: 
                        progress.update(task, advance=1)
                        failed += 1
                        continue
                    else:
                        utils.write_jsonl(domain_name, new_instance[-1], "responses", llm=llm)
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} advanced successfully.")
                        cost+=new_instance[-1]["response_object"]["usage"]["prompt_tokens"]*input_costs_per_token[llm] + new_instance[-1]["response_object"]["usage"]["completion_tokens"]*output_costs_per_token[llm]
                        progress.update(task, description=f"Processing... (${cost:.2f} cost)")
                    if len(new_instance) >= num_iterations:
                        maxed_out +=1
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} reached maximum iterations ({len(new_instance)}).")
                        progress.update(task, advance=1)
                        continue
                    elif new_instance[-1]["stopped"]:
                        stopped +=1
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} stopped successfully.")
                        progress.update(task, advance=1)
                        continue
                    futures.add(executor.submit(process_instance, new_instance, domain_name, verbose))
    print(f">>Complete. Total cost: ${cost}\n>>Number of failed instances: {failed}\n>>Number of stopped instances: {stopped}\n>>Number of maxed out instances (at {num_iterations} iterations): {maxed_out}")

if __name__=="__main__":
    Fire(get_responses)