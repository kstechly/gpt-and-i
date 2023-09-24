import os
import argparse
import time
import json
import time
from tqdm import tqdm
import openai
import domain_utils
from domain_utils import *

MAX_GPT_RESPONSE_LENGTH = 500
MAX_BACKPROMPT_LENGTH = 15

def get_responses(engine, domain_name, specified_instances = [], run_till_completion=False, ignore_existing=False, verbose=False, backprompting=""):
    instances_dir = f"data/{domain_name}/"
    prompt_dir = f"prompts/{domain_name}/"
    output_dir = f"responses/{domain_name}/{engine}/"
    if backprompting: output_dir += f"backprompting-{backprompting}/"
    os.makedirs(output_dir, exist_ok=True)
    output_json = output_dir+"responses.json"

    domain = domain_utils.domains[domain_name]

    if 'finetuned' in engine:
        # print(engine)
        assert engine.split(':')[1] is not None
        model = ':'.join(engine.split(':')[1:])
        # print(model)
        engine='finetuned'
        model = {'model':model}
    else:
        model = None
    
    output = {}
    prev_output = {}
    if os.path.exists(output_json):
        with open(output_json, 'r') as file:
            prev_output = json.load(file)
        if not ignore_existing:
            output = prev_output
    assert os.path.exists(prompt_dir+"prompts.json")
    with open(prompt_dir+"prompts.json", 'r') as file:
        input = json.load(file) 
    original_input_n = len(input)

    if len(specified_instances) > 0:
        input = {str(x) : input[str(x)] for x in specified_instances}
    elif not ignore_existing:
        input = {k: v for k,v in input.items() if k not in prev_output.keys()}
        if verbose:
            print(f"{original_input_n-len(input)} out of {original_input_n} instances already completed")

    while True:
        failed_instances = []
        for instance in tqdm(input):
            if verbose:
                print(f"Sending query to LLM: Instance {instance}")
            query = input[instance]
            stop_statement = "[STATEMENT]"
            llm_response = send_query(query, engine, MAX_GPT_RESPONSE_LENGTH, model=model, stop_statement=stop_statement)

            if not llm_response:
                failed_instances.append(instance)
                print(f"Failed instance: {instance}")
                continue
            if verbose:
                print(f"LLM response:\n{llm_response}")
            
            response_trace = [query, llm_response]
            
            if backprompting:
                failure = False
                instance_location = f"{instances_dir}/instance-{instance}{domain.file_ending()}"
                try:
                    with open(instance_location,"r") as fp:
                        instance_text = fp.read()
                except FileNotFoundError:
                    print(f"{instance_location} not found. Can't generate backprompt. Skipping instance {instance} entirely.")
                    continue
                for trial in range(0, MAX_BACKPROMPT_LENGTH):
                    if verbose:
                        print(f"Attempting {backprompting}-type backprompt #{trial} for instance {instance}")
                    if "sorry" in llm_response or "constraints" in llm_response:
                            print(f"Giving up because LLM apologized")
                            break
                    if backprompting == "llm":
                        print(f"Generating backprompt with LLM.")
                        backprompt_query = domain.backprompt(instance_text, llm_response, "llm-query")
                        print(f"Sending: {backprompt_query}")
                        backprompt = send_query(backprompt_query, engine, MAX_GPT_RESPONSE_LENGTH, model=model, stop_statement=stop_statement)
                        if not backprompt:
                            failure = True
                            failed_instances.append(instance)
                            print(f"Failed instance: {instance}")
                            break
                        backprompt = domain.backprompt(instance_text, backprompt, "llm-wrapper")
                    else: backprompt = domain.backprompt(instance_text, llm_response, backprompting)
                    if verbose:
                        print(f"Backprompt given: {backprompt}")
                    if check_backprompt(backprompt):
                        if verbose:
                            print(f"Verifier confirmed success.")
                        break
                    response_trace.append(backprompt)
                    query = "\n".join(response_trace)
                    '''print("###################FULL QUERY####################")
                    print(query)
                    print("###################END  QUERY####################")'''
                    llm_response = send_query(query, engine, MAX_GPT_RESPONSE_LENGTH, model=model, stop_statement=stop_statement)
                    if verbose:
                        print(f"LLM responded with:\n{llm_response}")
                    response_trace.append(llm_response)
                if failure:
                    continue

            output[instance]="\n".join(response_trace) #TODO [1:] or better: change the data format to split up the trace
            with open(output_json, 'w') as file:
                json.dump(output, file, indent=4)
        
        if run_till_completion:
            if len(failed_instances) == 0:
                break
            else:
                print(f"Retrying failed instances: {failed_instances}")
                input = {str(x):input[str(x)] for x in failed_instances}
                time.sleep(5)
        else:
            break

def check_backprompt(backprompt):
    STOP_PHRASE = "Verifier confirmed success."
    return STOP_PHRASE.lower() in backprompt.lower()

def send_query(query, engine, max_tokens, model=None, stop_statement="[STATEMENT]"):
    max_token_err_flag = False
    if engine == 'finetuned':
        if model:
            try:
                response = openai.Completion.create(
                    model=model['model'],
                    prompt=query,
                    temperature=0,
                    max_tokens=max_tokens,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=stop_statement)
            except Exception as e:
                max_token_err_flag = True
                print("[-]: Failed GPT3 query execution: {}".format(e))
            text_response = response["choices"][0]["text"] if not max_token_err_flag else ""
            return text_response.strip()
        else:
            assert model is not None
    elif '_chat' in engine:
        
        eng = engine.split('_')[0]
        # print('chatmodels', eng)
        messages=[
        {"role": "system", "content": "You are a constraint satisfaction solver that solves various CSP problems."},
        {"role": "user", "content": query}
        ]
        try:
            response = openai.ChatCompletion.create(model=eng, messages=messages, temperature=0)
        except Exception as e:
            max_token_err_flag = True
            print("[-]: Failed GPT3 query execution: {}".format(e))
        text_response = response['choices'][0]['message']['content'] if not max_token_err_flag else ""
        return text_response.strip()        
    else:
        try:
            response = openai.Completion.create(
                model=engine,
                prompt=query,
                temperature=0,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                stop=stop_statement)
        except Exception as e:
            max_token_err_flag = True
            print("[-]: Failed GPT3 query execution: {}".format(e))

        text_response = response["choices"][0]["text"] if not max_token_err_flag else ""
        return text_response.strip()

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
    parser.add_argument('-d', '--domain', type=str, required=True, help='Problem domain to query for')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-r', '--run_till_completion', type=str, default="False", help='Run till completion')
    parser.add_argument('-s', '--specific_instances', nargs='+', type=int, default=[], help='List of instances to run')
    parser.add_argument('-i', '--ignore_existing', action='store_true', help='Ignore existing output')
    parser.add_argument('-b', '--backprompt', type=str, default='', help='If backprompting, provide the type of backprompt to pass to the domain. Common types: zero, passfail, full, llm')
    args = parser.parse_args()
    engine = args.engine
    domain_name = args.domain
    if domain_name not in domain_utils.domains:
        raise ValueError(f"Domain name must be an element of {list(domain_utils.domains)}.")
    specified_instances = args.specific_instances
    verbose = args.verbose
    backprompt = args.backprompt
    run_till_completion = eval(args.run_till_completion)
    ignore_existing = args.ignore_existing
    print(f"Engine: {engine}, Domain: {domain_name}, Verbose: {verbose}, Run till completion: {run_till_completion}, Backprompt: {backprompt}")
    get_responses(engine, domain_name, specified_instances, run_till_completion, ignore_existing, verbose, backprompt)

