from fire import Fire
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
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
MAX_WORKERS = 1000

def prepare_input(prompts, previous_output, llm, backprompt_type, temp, trial_id, num_iterations):
    #TODO refactor
    input = []
    for key in prompts.keys():
        furthest = -1
        full_key_output = []
        for line in previous_output:
            if utils.check_spec(line, key, llm, backprompt_type, temp, trial_id):
                full_key_output.append(line)
                if line["prompt_num"] > furthest:
                    furthest = line["prompt_num"]
                    furthest_stopped = line["stopped"]
                    if furthest +1 >= num_iterations: break
                if line["stopped"]: break
        if furthest == -1:
            input.append([{"problem_id":key, "trial_num":trial_id, "llm":llm, "backprompt_type":backprompt_type, "temp":temp, "prompt_num":0, "prompt":[{"role":"user", "content": prompts[key]}], "response":"", "converted_data":False, "stopped":False}])
        elif not furthest_stopped and furthest+1 < num_iterations:
            full_key_output = sorted(full_key_output, key=lambda x: x["prompt_num"])
            input.append(full_key_output)
    return input

def process_instance(instance, domain_name, verbose=False):
    dmn = domain_utils.get_domain(domain_name)
    # Note that we assume that instance is already sorted by prompt_num
    # and that it isn't stopped, nor has it reached the maximum number of iterations
    if not instance[-1]["response"]:
        # if verbose: print(f">>Instance {instance[-1]['problem_id']} has never been seen before.==")
        prompt = instance[-1]["prompt"]
    else:
        # if verbose: print(f">>Generating backprompt {instance[-1]['prompt_num']+1} for instance {instance[-1]['problem_id']}.==")
        prompt = dmn.backprompt(instance)
        if check_backprompt(prompt): #TODO get rid of this part
            instance[-1]["stopped"] = True
            return instance
    llm = instance[-1]["llm"]
    temp = instance[-1]["temp"]
    # if verbose: print(f">>Instance {instance[-1]['problem_id']} is being processed with prompt:\n{prompt}")
    response, response_dict = send_query(prompt, llm, temp=temp)
    if not response: return None
    response_text = response.choices[0].message.content
    # if verbose: print(f">>Response to instance {instance[-1]['problem_id']}:\n{response_text}")
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
    return STOP_PHRASE.lower() in backprompt[-1]['content'].lower()

def send_query(prompt, llm, max_tokens=MAX_GPT_RESPONSE_LENGTH, temp=1):
    try:
        client = OpenAI()
        start = time.time()
        response = client.chat.completions.create(model=llm, messages=prompt, temperature=temp, stop="[ANSWER END]", max_tokens=max_tokens)
        end = time.time()
    except Exception as e:
        print("[-]: Failed OpenAI query execution: {}".format(e))
        return None, None
    response_dict = {**json.loads(response.model_dump_json()), "time": end-start}
    return response, response_dict

def get_responses(llm, domain_name, start=0, end=0, overwrite_previous=False, verbose=False, generator = "llm", verifier = "sound", critiquer = "", critique_type = "full", history_len = 15, history_type = "full", num_iterations=15, temp=1, trial_id=0, max_cost=100):
    if history_len == 0: critiquer = ""
    backprompt_type = {"generator":generator, "verifier":verifier, "critiquer":critiquer, "critique_type":critique_type, "history_len":history_len, "history_type":history_type}
    if not utils.known_llm(llm): return
    prompts = utils.read_json(domain_name, overwrite_previous=False, data_type="prompts")

    # Constrain work to only specified instances if flagged to do so
    if end > start: prompts = {str(x) : prompts[str(x)] for x in range(start, end+1)}
    print(f">>Checking {len(prompts)} instances for work to be done.")

    # convert to new format if it isn't already, then mark the file as old
    utils.update_format_to_jsonl(domain_name, overwrite_previous, "responses", llm, backprompt_type, temp, trial_id, verbose)
    previous_output = utils.read_jsonl(domain_name, "responses", llm, verbose)

    # Create input of only instances that haven't been completed yet
    input = prepare_input(prompts, previous_output, llm, backprompt_type, temp, trial_id, num_iterations)
    print(f">>Instances to be processed: {len(input)}")

    total_tasks = len(input)*num_iterations
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        ) as progress:
        task = progress.add_task("[cyan]Processing... $0.00 (0 tasks in queue. 0 tasks completed)", total=total_tasks)

        failed = 0
        cost = 0
        stopped = 0
        maxed_out = 0
        completed_tasks = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            print(f">>Deploying {min(MAX_WORKERS, len(input))} undergrads to process {len(input)} instances.")
            futures = {executor.submit(process_instance, instance, domain_name, verbose) for instance in input}
            while futures and cost < max_cost:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    futures.remove(future)
                    new_instance = future.result()
                    if not new_instance: 
                        failed += 1
                        continue
                    else:
                        utils.write_jsonl(domain_name, new_instance[-1], "responses", llm=llm)
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} advanced successfully to iteration {new_instance[-1]['prompt_num']}.")
                        cost+=utils.calculate_token_cost(llm, new_instance[-1]["response_object"]["usage"]["prompt_tokens"], new_instance[-1]["response_object"]["usage"]["completion_tokens"])
                        completed_tasks += 1
                    progress.update(task, advance=1, description=f"Processing... ${cost:.2f} ({len(futures)+1} tasks in queue. {completed_tasks} tasks completed)")
                    if len(new_instance) >= num_iterations:
                        maxed_out +=1
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} reached maximum iterations ({len(new_instance)}).")
                        continue
                    elif new_instance[-1]["stopped"]:
                        stopped +=1
                        if verbose: print(f">>Instance {new_instance[-1]['problem_id']} stopped successfully.")
                        progress.update(task, advance=num_iterations-len(new_instance), description=f"Processing... ${cost:.2f} ({len(futures)+1} tasks in queue. {completed_tasks} tasks completed)")
                        continue
                    futures.add(executor.submit(process_instance, new_instance, domain_name, verbose))
    print(f">>Complete. Total cost: ${cost}\n>>Number of failed instances: {failed}\n>>Number of stopped instances: {stopped}\n>>Number of maxed out instances (at {num_iterations} iterations): {maxed_out}")

if __name__=="__main__":
    Fire(get_responses)