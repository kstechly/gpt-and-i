import os
import argparse
import time
import json
import time
from tqdm import tqdm
import openai

MAX_GPT_RESPONSE_LENGTH = 500

def get_responses(engine, domain, specified_instances = [], run_till_completion=False, ignore_existing=False, verbose=False):
    prompt_dir = f"prompts/{domain}/"
    output_dir = f"responses/{domain}/{engine}/"
    os.makedirs(output_dir, exist_ok=True)
    output_json = output_dir+"responses.json"

    if 'finetuned' in engine:
        # print(engine)
        assert engine.split(':')[1] is not None
        model = ':'.join(engine.split(':')[1:])
        # print(model)
        engine='finetuned'
        model = {'model':model}
    else:
        model = None

    while True:
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
    
        failed_instances = []
        for instance in tqdm(input):
            if instance in prev_output.keys():
                if not ignore_existing:
                    if verbose:
                        print(f"Instance {instance} already completed")
                    continue
            if len(specified_instances) > 0:
                if instance not in specified_instances:
                    continue
                else:
                    specified_instances.remove(instance)
            
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
                print(f"LLM response: {llm_response}")
            output[instance]=llm_response
            with open(output_json, 'w') as file:
                json.dump(output, file, indent=4)
        
        if run_till_completion:
            if len(failed_instances) == 0:
                break
            else:
                print(f"Retrying failed instances: {failed_instances}")
                time.sleep(5)
        else:
            break
    
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
    args = parser.parse_args()
    engine = args.engine
    domain = args.domain
    specified_instances = args.specific_instances
    verbose = args.verbose
    run_till_completion = eval(args.run_till_completion)
    ignore_existing = args.ignore_existing
    print(f"Engine: {engine}, Domain: {domain}, Verbose: {verbose}, Run till completion: {run_till_completion}")
    get_responses(engine, domain, specified_instances, run_till_completion, ignore_existing, verbose)

