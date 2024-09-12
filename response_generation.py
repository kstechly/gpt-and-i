import os
import argparse
import time
import json
import time
from tqdm import tqdm
from openai import OpenAI
import concurrent.futures

client = OpenAI()
import domain_utils
from domain_utils import *
# from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModel, StoppingCriteriaList, StoppingCriteria
# from huggingface_hub import login

MAX_GPT_RESPONSE_LENGTH = 1500
MAX_GPT_RESPONSE_LENGTH_SAFE = 300
MAX_BACKPROMPT_LENGTH = 15
STOP_PHRASE = "stop10002" # "Verifier confirmed success" # what the verifier has to say
STOP_STATEMENT = "[ANSWER END]" # what we look for to end LLM response generation

def get_responses(engine, domain_name, specified_instances = [], run_till_completion=False, ignore_existing=False, verbose=False, multiprompting="", problem_type="", multiprompt_num=15, temp=0, model=None, trial_id=0):
    domain = domain_utils.domains[domain_name]
    cost = 0.00

    # Check for/set up relevant directories
    instances_dir = f"data/{domain_name}/"
    prompt_dir = f"prompts/{domain_name}/"
    output_dir = f"responses/{domain_name}/{engine}/"
    if multiprompting: output_dir += f"backprompting-{multiprompting}{f'-temp{temp}' if temp else ''}/"
    if problem_type: output_dir+=f"{problem_type}/"
    os.makedirs(output_dir, exist_ok=True)
    if trial_id: output_dir+=f"{trial_id}"
    output_json = output_dir+"responses.json"

    # Load prompts
    with open(prompt_dir+f"prompts{f'-{problem_type}' if problem_type else ''}.json", 'r') as file:
        input = json.load(file)

    # Constrain work to only specified instances if flagged to do so
    if len(specified_instances) > 0:
        input = {str(x) : input[str(x)] for x in specified_instances}

    # Load previously done work
    output = {}
    if os.path.exists(output_json):
        with open(output_json, 'r') as file:
            # NOTE: the following json file should be a dictionary of dictionaries (each representing an instance), each containing three things: prompts (an ordered list of prompts), responses (an ordered list of corresponding responses), and stopped (a boolean of whether generation has been stopped on purpose yet)
            output = json.load(file)
            if ignore_existing:
                stamp = str(time.time())
                with open(f"{output_dir}responses-{stamp}.json","w") as file:
                    json.dump(output, file, indent=4)
                    output = {}
    def process_item(instance):
        instance_output = {"prompts":[input[str(instance)]], "responses":[], "stopped":False}
        finished_prompts = 0

        # Load actual instance data
        instance_location = f"{instances_dir}/instance-{instance}{domain.file_ending()}"
        try:
            with open(instance_location,"r") as fp:
                instance_text = fp.read()
        except FileNotFoundError:
            print(f"{instance_location} not found. Skipping instance {instance} entirely.")
            return

        # Check if this instance is already complete
        if instance in output:
            instance_output = output[instance]
            finished_prompts = len(instance_output["responses"])
            if instance_output["stopped"]:
                if verbose: print(f"===Instance {instance} already completed===")
                return
            elif finished_prompts >= multiprompt_num:
                if verbose: print(f"===Instance {instance} already maxed out at {finished_prompts} out of {multiprompt_num} backprompts===")
                return
            elif verbose: print(f"===Instance {instance} not complete yet. Continuing from backprompt {finished_prompts+1}===")
        elif verbose: print(f"===Instance {instance} has never been seen before===")

        # with open(f'{output_json}.{instance}','w') as file:
        #     instance_output = json.load(file)

        # Loop over the multiprompts until verifier stops or times out
        while len(instance_output["responses"])< multiprompt_num and not instance_output["stopped"]:
            if len(instance_output["prompts"]) > len(instance_output["responses"]):
                if verbose: print(f"==Sending prompt {len(instance_output['prompts'])} of length {len(instance_output['prompts'][-1])} to LLM for instance {instance}==")
                if verbose: print(instance_output["prompts"][-1])
                # cost += len(instance_output['prompts'][-1])*0.00003/3
                llm_response = send_query(instance_output["prompts"][-1], engine, MAX_GPT_RESPONSE_LENGTH, stop_statement=STOP_STATEMENT, temp=temp, model=model)
                if not llm_response:
                    failed_instances.append(instance)
                    print(f"==Failed instance: {instance}==")
                    break
                if verbose: print(f"==LLM response to instance {instance}: ==\n{llm_response}")
                # cost += len(llm_response)*0.00006/3
                instance_output["responses"].append(llm_response)
            if len(instance_output["prompts"]) == len(instance_output["responses"]) and multiprompting:
                backprompt_query = domain.backprompt(instance_text, instance_output, multiprompting, problem_type)
                try: pass
                except: 
                    failed_instances.append(instance)
                    raise ValueError(f"==Failed instance: {instance} (Couldn't generate backprompt)==")
                    break
                instance_output["prompts"].append(backprompt_query)
                if check_backprompt(backprompt_query):
                    instance_output["stopped"] = True
                    if verbose: print(f"==Stopping instance {instance} after {len(instance_output['responses'])} responses.==")
            # if verbose: print(f"***Current cost: {cost:.2f}***")
            with open(f"{output_json}.{instance}.tmp", 'w') as file:
                json.dump(output, file, indent=4)
            os.replace(f"{output_json}.{instance}.tmp", f'{output_json}.{instance}')
            if instance_output["stopped"]: break
        output[instance]=instance_output

    # Loop over instances until done, multiproccessed
    while True:
        failed_instances = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            thread_exceptions = executor.map(process_item, input)
        print("done?")
        with open(f"{output_json}.tmp", 'w') as file:
            json.dump(output, file, indent=4)
        os.replace(f"{output_json}.tmp", output_json)
        try:
            for thread_ex in thread_exceptions:
                thread_ex
        except Exception as e:
            print(e)
		

        # Run till completion implementation
        if run_till_completion:
            if len(failed_instances) == 0:
                break
            else:
                print(f"Retrying failed instances: {failed_instances}")
                input = {str(x):input[str(x)] for x in failed_instances}
                time.sleep(5)
        else:
            print(f"Failed instances: {failed_instances}")
            # print(f"Total Cost: {cost:.2f}")
            break

def check_backprompt(backprompt):
    return STOP_PHRASE.lower() in backprompt.lower()

def get_llama2_70b():
        max_memory_mapping = {0: '19.0GB', 1: "19.0GB", 2: "19.0GB", 3: "19.0GB", 4: "19.0GB", 5: "19.0GB", 6: "43.0GB", 7: "43.0GB"}
        #Change the cache dir for your own env
        cache_dir = os.getenv('LLAMA2_CACHE_DIR', '/data/karthik/LLM_models/llama2_70b/')
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-70b-hf")
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-70b-hf", cache_dir=cache_dir,
                                                     local_files_only=False, load_in_8bit=True, device_map='auto',
                                                     max_memory=max_memory_mapping)
        return {'model': model, 'tokenizer': tokenizer}

def get_llama2_13b():
        max_memory_mapping = {0: '43.0GB', 1: "43.0GB", 2: "43.0GB", 3: "43.0GB", 4: "43.0GB", 5: "43.0GB"}
        #Change the cache dir for your own env
        cache_dir = os.getenv('LLAMA2_CACHE_DIR', '/data/karthik/LLM_models/llama2_13b/')
        tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-13b-hf")
        model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-13b-hf", cache_dir=cache_dir,
                                                     local_files_only=False, load_in_8bit=True, device_map='auto',
                                                     max_memory=max_memory_mapping)
        return {'model': model, 'tokenizer': tokenizer}

def generate_from_huggingfaceLLM(model, tokenizer, query, max_tokens, stop_statement="[PLAN END]"):
    encoded_input = tokenizer(query, return_tensors='pt')
    stop = tokenizer(stop_statement, return_tensors='pt')
    stoplist = StoppingCriteriaList([stop])
    output_sequences = model.generate(input_ids=encoded_input['input_ids'].cuda(), max_new_tokens=max_tokens,
                                      temperature=0.001, top_p=1)
    return tokenizer.decode(output_sequences[0], skip_special_tokes=True)


def send_query(query, engine, max_tokens, stop_statement="09h2309uharsuytbayuhfar", temp=0, top_num=5, model=None):
    #TODO fix stop statement
    if '_chat' in engine:
        eng = engine.split('_')[0]
        # print('chatmodels', eng)
        messages=[
        {"role": "system", "content": "You are a constraint satisfaction solver that solves various CSP problems."},
        {"role": "user", "content": query}
        ]
        try:
            response = client.chat.completions.create(model=eng, messages=messages, temperature=temp, max_tokens=max_tokens, tool_choice=None)
            text_response = response.choices[0].message.content
        except Exception as e:
            print("[-]: Failed GPT query execution: {}".format(e))
            text_response = ""
            print("BUT! Trying safer token count...")
            try:
                response = client.chat.completions.create(model=eng, messages=messages, temperature=temp, max_tokens=MAX_GPT_RESPONSE_LENGTH_SAFE, tool_choice=None)
                text_response = response.choices[0].message.content
            except Exception as e:
                print("Couldn't fix it, that's a huge rip man: {}".format(e))
        # print("====FINISH REASON====")
        # print(response.choices[0].finish_reason)
        return text_response.strip()        
    elif 'llama' in engine:
        if model:
            response = generate_from_huggingfaceLLM(model['model'], model['tokenizer'], query, max_tokens, stop_statement=stop_statement)
            response = response.replace(query, '')
            response = response.replace('<s>', '')
            return response.strip()
        else:
            assert model is not None
    else:
        try:
            print("Did you forget to add _chat?")
            exit()
            response = client.completions.create(model=engine,
            prompt=query,
            temperature=0,
            max_tokens=max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=stop_statement)
        except Exception as e:
            max_token_err_flag = True
            print("[-]: Failed GPT query execution: {}".format(e))
        text_response = response.choices[0].text if not max_token_err_flag else ""
        return text_response.strip()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--engine', type=str, required=True, help='Engine to use \
                        \n gpt-4_chat = GPT-4 \
                        \n gpt-3.5-turbo_chat = GPT-3.5 Turbo \
                        ')
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to query for')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-r', '--run_till_completion', type=str, default="False", help='Run till completion')
    parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('-i', '--ignore_existing', action='store_true', help='Ignore existing output')
    parser.add_argument('-b', '--backprompt', type=str, default='', help='If multiprompting, provide the type of backprompt to pass to the domain. Common types: zero, passfail, full, llm, top')
    parser.add_argument('-B', '--backprompt_num', type=int, default=15, help='If multiprompting, provide the maximum number of prompts to try. Double this number to get expected behavior for LLM backprompting')
    parser.add_argument('-n', '--end_number', type=int, default=0, help='For running from instance m to n')
    parser.add_argument('-m', '--start_number', type=int, default=1, help='For running from instance m to n. You must specify -n for this to work')
    parser.add_argument('-p', '--problem', type=str, default='', help='If doing a domain subproblem, specify it here')
    parser.add_argument('-t', '--temperature', type=float, default=0, help='Temperature from 0.0 to 2.0')
    parser.add_argument('-T', '--trial', type=int, default=1, help='A unique number identifying which trial run this is continuing/starting')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    specified_instances = args.specific_instances
    verbose = args.verbose
    backprompt = args.backprompt
    backprompt_num = args.backprompt_num
    if not backprompt: backprompt_num = 1
    run_till_completion = eval(args.run_till_completion)
    ignore_existing = args.ignore_existing
    end_number = args.end_number
    start_number = args.start_number
    problem_type = args.problem
    temperature = args.temperature
    trial_num = args.trial
    if end_number>0 and specified_instances:
        print("You can't use both -s and -n")
    elif end_number>0:
        specified_instances = list(range(start_number,end_number+1))
        print(f"Running instances from {start_number} to {end_number}")
    print(f"Engine: {engine}, Domain: {domain_name}, Verbose: {verbose}, Run till completion: {run_till_completion}, Multiprompt Type: {backprompt}, Problem Type: {problem_type}, Trial ID: {trial_num}")

    model = None
    if 'llama' in engine:
        # HuggingFace parameters
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        #get environment variable huggingface_token
        token = os.environ["HF_TOKEN"]
        login(token=token)
        #Load model if needed
        if engine == 'llama2_70b':
            model = get_llama2_70b()
        elif engine == 'llama2_13b':
            model = get_llama2_13b()
    for x in range(0,trial_num):
        print(f"****TRIAL {x}*****")
        get_responses(engine, domain_name, specified_instances, run_till_completion, ignore_existing, verbose, backprompt, problem_type, multiprompt_num=backprompt_num, temp=temperature, model=model, trial_id=x)