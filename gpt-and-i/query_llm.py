from fire import Fire
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import domain_utils
import utils
from rich.progress import (Progress, SpinnerColumn, TextColumn, BarColumn,
                           TaskProgressColumn, TimeRemainingColumn)
import time
import json

MAX_GPT_RESPONSE_LENGTH = 1500
MAX_BACKPROMPT_LENGTH = 15
# TODO fix the STOP_PHRASE bullshit and just do this correctly
# what the verifier has to say
STOP_PHRASE = "stop10002"
# what we look for to end LLM response generation
STOP_STATEMENT = "[ANSWER END]"
MAX_WORKERS = 1000


# TODO make this take in prompts, prev, and dict of relevant keys
def prepare_input(prompts, previous_output, llm, backprompt_type, temp,
                  trial_id, num_iterations):
    input = []
    furthest = {x: -1 for x in prompts.keys()}
    full_key_output = {x: [] for x in prompts.keys()}
    blacklist = []
    for line in previous_output:
        id = line["problem_id"]
        if id in blacklist or id not in prompts.keys():
            continue
        prompt_num = line["prompt_num"]
        if prompt_num + 1 >= num_iterations or line["stopped"]:
            if utils.check_spec(line, id, llm, backprompt_type, temp,
                                trial_id):
                blacklist.append(id)
            continue
        if utils.check_spec(line, id, llm, backprompt_type, temp, trial_id):
            full_key_output[id].append(line)
            if prompt_num > furthest[id]:
                furthest[id] = prompt_num
    for key in prompts.keys():
        if key in blacklist:
            continue
        if furthest[key] == -1:
            input.append(
                [{"problem_id": key, "trial_num": trial_id, "llm": llm,
                  "backprompt_type": backprompt_type, "temp": temp,
                  "prompt_num": 0,
                  "prompt": [{"role": "user", "content": prompts[key]}],
                  "response": "", "converted_data": False, "stopped": False}])
        else:
            full_key_output[key] = sorted(
                full_key_output[key],
                key=lambda x: x["prompt_num"])
            input.append(full_key_output[key])
    return input


def process_instance(instance, domain_name, verbose=False):
    dmn = domain_utils.get_domain(domain_name)
    # Note that we assume that instance is already sorted by prompt_num
    # and that it isn't stopped, nor has it reached the maximum number of
    # iterations
    if not instance[-1]["response"]:
        if verbose:
            print(
                f">>Instance {instance[-1]['problem_id']} has never been seen "
                "before.==")
        prompt = instance[-1]["prompt"]
    else:
        if verbose:
            print(
                f">>Generating backprompt {instance[-1]['prompt_num']+1} for "
                "instance {instance[-1]['problem_id']}.==")
        prompt = dmn.backprompt(instance)
        if check_backprompt(prompt):  # TODO get rid of this part
            instance[-1]["stopped"] = True
            return instance
    llm = instance[-1]["llm"]
    temp = instance[-1]["temp"]
    if verbose:
        print(
            f">>Instance {instance[-1]['problem_id']} is being sent to the "
            "API")
    response, response_dict = send_query(prompt, llm, temp=temp)
    if not response:
        return None
    response_text = response.choices[0].message.content
    if verbose:
        print(
            f">>Response to instance {instance[-1]['problem_id']}:\n"
            f"{response_text}")
    if not instance[-1]["response"]:
        instance[-1]["response"] = response_text
        instance[-1]["response_object"] = response_dict
    else:
        instance.append(
            {**
             {k: instance[-1][k]
              for k in instance[-1].keys() -
              {'response', 'prompt', 'prompt_num', 'converted_data',
               'response_object', 'stopped'}},
             "prompt_num": instance[-1]["prompt_num"] + 1, "prompt": prompt,
             "response": response_text, "converted_data": False,
             "response_object": response_dict, "stopped": False})
    if check_backprompt(dmn.backprompt(instance)):
        # TODO make a dedicated function for checking stopping
        instance[-1]["stopped"] = True
    return instance


def check_backprompt(backprompt):
    return STOP_PHRASE.lower() in backprompt[-1]['content'].lower()


def send_query(prompt, llm, temp=1):
    # try:
    client = OpenAI()
    print(client)
    start = time.time()
    print(llm)
    if "o1" in llm:
        response = client.chat.completions.create(model=llm, messages=prompt)
    else:
        print("sending")
        response = client.chat.completions.create(
            model=llm, messages=prompt, temperature=temp, stop="[ANSWER END]")
        print("recieved")
    end = time.time()
    print(end - start)
    # except Exception as e:
    #    print("[-]: Failed OpenAI query execution: {}".format(e))
    #    return None, None
    response_dict = {
        **json.loads(response.model_dump_json()),
        "time": end - start}
    return response, response_dict


def get_responses(
        llm, domain_name, start=0, end=0, overwrite_previous=False,
        verbose=False, generator="llm", verifier="sound", critiquer="",
        critique_type="full", history_len=15, history_type="full",
        num_iterations=15, temp=1, trial_id=0, max_cost=100, problem_type=""):
    if history_len == 0:
        critiquer = ""
    backprompt_type = {
        "generator": generator,
        "verifier": verifier,
        "critiquer": critiquer,
        "critique_type": critique_type,
        "history_len": history_len,
        "history_type": history_type}
    if not utils.known_llm(llm):
        return
    prompts = utils.read_json(
        domain_name,
        overwrite_previous=False,
        data_type="prompts")

    # Constrain work to only specified instances if flagged to do so
    if "ALL" in problem_type:
        pprompts = {}
        p_key = problem_type.split("ALL")[1]
        for p_type in ["correct", "ablated", "non-optimal", "random"]:
            pprompts.update(
                {f"{x}{p_type}{p_key}": prompts[f"{x}{p_type}{p_key}"]
                 for x in range(start, end + 1)})
        prompts = pprompts
    elif problem_type:
        prompts = {
            f"{x}{problem_type}": prompts[f"{x}{problem_type}"]
            for x in range(start, end + 1)}
    elif end > start:
        prompts = {str(x): prompts[str(x)] for x in range(start, end + 1)}
    print(f">>Checking {len(prompts)} instances for work to be done.")

    previous_output = utils.read_jsonl(domain_name, "responses", llm, verbose)

    # Create input of only instances that haven't been completed yet
    input = prepare_input(
        prompts,
        previous_output,
        llm,
        backprompt_type,
        temp,
        trial_id,
        num_iterations)
    print(f">>Instances to be processed: {len(input)}")

    total_tasks = len(input) * num_iterations
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn()
    ) as progress:
        task = progress.add_task(
            "[cyan]Processing... $0.00 (0 tasks in queue. 0 tasks completed)",
            total=total_tasks)

        failed = 0
        cost = 0
        stopped = 0
        maxed_out = 0
        completed_tasks = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            print(
                f">>Deploying {min(MAX_WORKERS, len(input))} undergrads to "
                "process {len(input)} instances.")
            futures = {
                executor.submit(
                    process_instance, instance, domain_name, verbose)
                for instance in input}
            while futures and cost < max_cost:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    futures.remove(future)
                    new_instance = future.result()
                    if not new_instance:
                        failed += 1
                        continue
                    else:
                        utils.write_jsonl(
                            domain_name, new_instance[-1],
                            "responses", llm=llm)
                        if verbose:
                            print(
                                f">>Instance {new_instance[-1]['problem_id']} "
                                f"advanced successfully to iteration "
                                f"{new_instance[-1]['prompt_num']}.")
                        cost += utils.calculate_token_cost(llm,
                                                           new_instance[-1]
                                                           ["response_object"]
                                                           ["usage"]
                                                           ["prompt_tokens"],
                                                           new_instance[-1]
                                                           ["response_object"]
                                                           ["usage"]
                                                           ["completion_tokens"
                                                            ]
                                                           )
                        completed_tasks += 1
                    progress.update(
                        task,
                        advance=1,
                        description=f"Processing... ${cost:.2f} ("
                        f"{len(futures)+1} tasks in queue. {completed_tasks} "
                        f"tasks completed)")
                    if len(new_instance) >= num_iterations:
                        maxed_out += 1
                        if verbose:
                            print(
                                f">>Instance {new_instance[-1]['problem_id']} "
                                f"reached maximum iterations "
                                f"({len(new_instance)}).")
                        continue
                    elif new_instance[-1]["stopped"]:
                        stopped += 1
                        if verbose:
                            print(
                                f">>Instance {new_instance[-1]['problem_id']} "
                                f"stopped successfully.")
                        progress.update(
                            task,
                            advance=num_iterations -
                            len(new_instance),
                            description=f"Processing... ${cost:.2f} "
                            f"({len(futures)+1} tasks in queue. "
                            f"{completed_tasks} tasks completed)")
                        continue
                    futures.add(
                        executor.submit(
                            process_instance,
                            new_instance,
                            domain_name,
                            verbose))
    print(f">>Complete. Total cost: ${cost}\n>>Number of failed instances: "
          f"{failed}\n>>Number of stopped instances: {stopped}\n>>Number of "
          f"maxed out instances (at {num_iterations} iterations): {maxed_out}")


if __name__ == "__main__":
    Fire(get_responses)
