import csv
import re
import sympy
import json
from pprint import pprint

CSV_LOCATION = "data/instances/game24/24.csv"
GAME24_DIRECTORY = "data/instances/game24/"

END_TAG = "[ANSWER END]"
DEFAULT_PROMPT_START = f"Use numbers and basic arithmetic operations (+ - * /) to obtain 24. You must write your response. Write your answer first, followed by {END_TAG}\n"
# \nInput: 4 4 6 8\nAnswer: (4 + 8) * (6 - 4) = 24
STOP_PHRASE = "stop10002"
STOP_PHRASE_MASK = "Twenty-four achieved"

def DEFAULT_BACKPROMPT_END(instance_text):
    return f"Using the numbers {instance_text} please provide a correct expression that evaluates to 24. Write your answer first. At the end of your answer, write {END_TAG}\nAnswer: "

def check_answer(instance_text, equation):
    input_nums = instance_text.split("\n")[0].split(" ")
    expression = equation.strip().split('\n')[0].lower().split('=')[0]
    numbers = re.findall(r'\d+', expression)
    if sorted(numbers) != sorted(input_nums): return False, f"This expression consists of the numbers {', '.join(numbers)}, but it has to consist of only and exactly {input_nums}."
    expression = fix_expression(expression)
    try: return sympy.simplify(expression) == 24, f"This expression evaluates to {sympy.simplify(expression)} instead of 24."
    except: return False, "This expression is malformed." #NOTE: this will reject expressions that could be fixed by just appending a close parens

def concat_trace(instance_output, divisor = 1):
    raiseNotImplementedError("FIX MEEEEE")
    prompts = instance_output["prompts"]
    responses = instance_output["responses"]
    trace = prompts[-divisor] + responses[-divisor] +"[ANSWER END]\n"
    return trace

def list_previous(instance_output, evaluate=False):
    responses = instance_output["responses"]
    prev_list = ""
    for response in responses:
        expression = response.strip().split('\n')[0].lower().split('=')[0]
        try: answer = sympy.simplify(response.split("=")[0])
        except: continue
        prev_list+= expression
        if evaluate: prev_list+="="+answer
        prev_list+="\n"
    return prev_list

def fix_expression(expression): # hand-crafted fixes for rare LLM outputs that don't play nice with sympy
    expression = expression.replace("x","*")
    expression = expression.replace("÷","/")
    expression = expression.replace("×","*")
    expression = expression.replace("[","(")
    expression = expression.replace("]",")")
    return expression

def simplify_with_error(expression):
    expression = fix_expression(expression)
    try: simplified = sympy.simplify(expression)
    except:
        try: simplified = sympy.simplify(f"{expression})")
        except:
            #print(f"Can't simplify {expression}")
            simplified = expression
    return simplified

def evaluate_up_to(instance_text, response_trace, responses_correct, responses_evals, problem_type="", backprompt_type=""):
    evaluation = {}
    responses = response_trace["responses"]
    token_cost = sum(map(len, responses))
    prompts = response_trace["prompts"][:len(responses)] # deals with extra appended (but unsent) prompts
    token_cost += sum(map(len, prompts))
    evaluation["token cost"]= token_cost

    # print(responses)
    # if len(responses)>1: exit()

    if "llm" in backprompt_type:
        evals = responses[1::2]
        responses = responses[::2]
    evaluation["correct"] = responses_correct[-1]
    # print(responses_correct)
    evaluation["ever corrects"] = sum(responses_correct)
    evaluation["ever correct"] = True in responses_correct
    evaluation['false_positive'] = False
    if "llm" in backprompt_type and len(evals)==len(responses):
        try:
            json_string = re.search("{([^}]*)}",evals[-1]).group(0).lower()
            claim = json.loads(json_string)['correct']
        except:
            claim = False
        # print(responses_correct[-2])
        # print(claim)
        if claim and not responses_correct[-2]:
            # print('caught one')
            evaluation["false_positive"] = True
    if "top" in backprompt_type: evaluation["correct"] = evaluation["ever correct"]
    evaluation["false negatives"]= sum(responses_correct[:-1])
    evaluation["num prompts"] = len(prompts)
    self_con = max(set(responses), key = responses.count)
    responses = list(map(lambda x: x.replace(" ",""), responses))
    evaluation["num unique responses"] = len(set(responses))
    evaluation["num unique evaluations"] = len(set(responses_evals))
    evaluation["self consistency"]=check_answer(instance_text,self_con)[0]
    # print(evaluation['false_positive'])
    return evaluation

#### Required Functions

def file_ending():
    return ".txt"

def generate(instance_text, problem_type):
    prompt = DEFAULT_PROMPT_START
    prompt+= f"Input: {instance_text}\nAnswer: "
    return prompt

def evaluate(instance_text, response_trace, problem_type="", backprompt_type=""):
    # print("===")
    evaluation = []
    subtrace = dict(response_trace)
    responses_correct_all = [check_answer(instance_text,x)[0] for x in subtrace["responses"]]
    responses_evals_all = list(map(lambda x: simplify_with_error(x.strip().split('\n')[0].lower().split('=')[0]), subtrace["responses"]))
    for n in range(1, len(response_trace["responses"])+1):
        subtrace["responses"] = response_trace["responses"][:n]
        responses_correct = responses_correct_all[:n]
        responses_evals = responses_evals_all[:n]
        evaluation.append(evaluate_up_to(instance_text, subtrace, responses_correct, responses_evals, problem_type, backprompt_type))
    fp = evaluation[-1]['false_positive']
    if "llm" in backprompt_type:
        evaluation = list(evaluation[:-1])
    evaluation[-1]['false_positive'] = fp
    # pprint(response_trace)
    assert not (fp and evaluation[-1]['correct'])
    return evaluation

def get_instance_text(problem_id):
    with open(f"{GAME24_DIRECTORY}instance-{problem_id}{file_ending()}") as fp:
        return fp.read()

def convert_instance_to_old_format(instance):
    instance_text = get_instance_text(instance[-1]["problem_id"])
    instance_output = {"prompts":[instance[x]["prompt"] for x in range(0,len(instance))], "responses":[instance[x]["response"] for x in range(0,len(instance))]}
    backprompt_type = instance[-1]["backprompt_type"]
    verifier = backprompt_type["verifier"]
    critiquer = backprompt_type["critiquer"]
    critique_type = backprompt_type["critique_type"]
    history_len = backprompt_type["history_len"]
    history_type = backprompt_type["history_type"]
    if verifier == "llm" and critiquer == "llm":
        backprompt_name = "llm"
    else: raiseNotImplementedError()
    return instance_text, instance_output, backprompt_name

def backprompt_old(instance):
    instance_text, instance_output, backprompt_type = convert_instance_to_old_format(instance)
    model_response = instance_output["responses"][-1]
    if backprompt_type == "llm":
        #free form feedback from the llm
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = {}
            try:
                json_string = re.search("{([^}]*)}",model_response).group(0).lower()
                llm_json = json.loads(json_string)
            except:
                llm_json["correct"] = False
                llm_json["feedback"] = model_response
            if llm_json["correct"]:
                return STOP_PHRASE
            backprompt = "Feedback: This is not correct.\n"
            backprompt += llm_json["feedback"]
            backprompt += f"\n\nWith this feedback, please try again."
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "llm-cot":
        # A basic zero-shot CoT prompt for verification
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = {}
            try:
                json_string = re.search("{([^}]*)}",model_response).group(0).lower()
                llm_json = json.loads(json_string)
            except:
                llm_json["correct"] = False
                llm_json["feedback"] = model_response
            # json_string = re.search("{([^}]*)}",model_response).group(0).lower()
            # llm_json = json.loads(json_string)
            if llm_json["correct"]:
                return STOP_PHRASE
            backprompt = "Feedback: This is not correct.\n"
            backprompt += llm_json["feedback"]
            backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= f"\nFirst, think step by step. Check that the expression uses only the correct numbers, has exactly the right number of instances each number, and evaluates to 24. Then decide what your final answer is."
            backprompt_query+= '\nWhen outputting your final answer, first print the [Answer] tag, then put your final answer after the [Answer] tag and respond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            backprompt_query+= f"\n\nLet's think step by step.\n[Thoughts]"
            return backprompt_query
    if backprompt_type == "llm-evaluate":
        #told to evaluate the number first
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            json_string = re.search("{([^}]*)}",model_response).group(0).lower()
            llm_json = json.loads(json_string)
            if llm_json["correct"]:
                return STOP_PHRASE
            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "Feedback: This is not correct.\n"
            backprompt += f"This expression evaluates to {llm_json['evaluation']}."
            backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Calculate what this expression evaluates to: " +model_response
            backprompt_query+= f"\nThen check whether it uses exactly and only the numbers provided. If it does, and equals 24, then it is correct."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "evaluation": "number the expression evaluated to",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "llm-passfail":
        # Binary LLM feedback
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            json_string = re.search("{([^}]*)}",model_response).group(0).lower()
            llm_json = json.loads(json_string)
            if llm_json["correct"]:
                return STOP_PHRASE
            return f"{concat_trace(instance_output, divisor=2)}Feedback: This is not correct. {DEFAULT_BACKPROMPT_END(instance_text)}"
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n"correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "llm-sample":
        # llm sample into llm verifier, run at higher temp
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            json_string = re.search("{([^}]*)}",model_response).group(0).lower()
            try:
                llm_json = json.loads(json_string)
            except:
                try: llm_json = json.loads(model_response)
                except:
                    raise ValueError(f"Could not parse JSON: {json_string}")
            if llm_json["correct"]:
                return STOP_PHRASE
            return instance_output["prompts"][0]
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "llm-lang-top":
        # New prompts are just as short, but now translated. Uses an external verifier
        if len(instance_output["responses"])%2==0:
            # Return generation prompt made by LLM for even numbered responses
            return model_response
        else:
            # Return translation prompt for odd numbered responses
            backprompt_query = f"While ensuring that no information is lost, and without including anything else in your response, translate the following into Spanish. Do not say {END_TAG} at any point:"
            backprompt_query+= f"\n\n{instance_output['prompts'][0]}"
            return backprompt_query
    if backprompt_type == "top":
        # Just do the same initial prompt every time
        return instance_output["prompts"][0]
    if backprompt_type == "sure":
        # Just ask "Are you sure?" and repeat the prompt
        return f"{concat_trace(instance_output)}Feedback: Are you sure? {DEFAULT_BACKPROMPT_END(instance_text)}"
    if backprompt_type == "list-previous":
        # includes a list of all previously tried guesses, no implications of incorrectness
        backprompt = DEFAULT_PROMPT_START
        backprompt+= f"Input: {instance_text}\nNote: Do not respond with any of the following expressions:\n"
        backprompt+= list_previous(instance_output)
        backprompt+= "\nAnswer: "
        return backprompt
    check, reason = check_answer(instance_text, model_response)
    if backprompt_type == "llm+sound":
        # LLM verifies, but the critique is generated by the sound critiquer
        # if the sound critiquer has nothing, don't provide information
        if len(instance_output["responses"])%2==0:
        # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = {}
            try:
                json_string = re.search("{([^}]*)}",model_response).group(0).lower()
                llm_json = json.loads(json_string)
            except:
                llm_json["correct"] = False
                llm_json["feedback"] = model_response
            if llm_json["correct"]:
                return STOP_PHRASE

            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "Feedback: This is not correct.\n"
            backprompt += reason if check else ""
            backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if check: return STOP_PHRASE
    if backprompt_type == "sound+llm":
        # Sound verification, LLM critique
        # if the LLM says correct, don't provide information
        if len(instance_output["responses"])%2==0:
        # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = {}
            try:
                json_string = re.search("{([^}]*)}",model_response).group(0).lower()
                llm_json = json.loads(json_string)
            except:
                llm_json["correct"] = False
                llm_json["feedback"] = model_response
            if llm_json["correct"]:
                return STOP_PHRASE

            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "Feedback: This is not correct.\n"
            backprompt += llm_json['feedback'] if llm_json['correct'] else ""
            backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "top-stop":
        # Just do the same initial prompt every time, but stop it if it's correct
        return instance_output["prompts"][0]
    if backprompt_type == "passfail":
        return f"{concat_trace(instance_output)}Feedback: This is not correct. {DEFAULT_BACKPROMPT_END(instance_text)}"
    elif backprompt_type == "evaluate":
        return f"{concat_trace(instance_output)}Feedback: This is not correct. {reason} {DEFAULT_BACKPROMPT_END(instance_text)}"
    elif backprompt_type == "list-wrong":
        # includes a list of all incorrect previous guesses, stops when done
        backprompt = DEFAULT_PROMPT_START
        backprompt+= f"Input: {instance_text}\nNote: The following expressions are incorrect as they either do NOT use all the correct numbers or they do NOT evaluate to 24:\n"
        backprompt+= list_previous(instance_output)
        backprompt+= "\nAnswer: "
        return backprompt
    elif backprompt_type == "list-evals":
        # includes a list of all previous guesses with their true evaluations
        backprompt = DEFAULT_PROMPT_START
        backprompt+= f"Input: {instance_text}\nNote: The following expressions are incorrect as they either do NOT use all the correct numbers or they do NOT evaluate to 24:\n"
        backprompt+= list_previous(instance_output, evaluate=True)
        backprompt+= "\nAnswer: "
        return backprompt
    else: raise NotImplementedError


def backprompt(instance):
    backprompt_type = instance[-1]["backprompt_type"]
    verifier = backprompt_type["verifier"]
    critiquer = backprompt_type["critiquer"]
    critique_type = backprompt_type["critique_type"]
    history_len = backprompt_type["history_len"]
    history_type = backprompt_type["history_type"]
    # check if llm prompting, if so, check which portion we're in (generation or verification/critique)
    text = backprompt_old(instance)
    jump = 1
    if (verifier == "llm" or critiquer == "llm"):
        if len(instance)%2: return wrap_in_messages(text)
        jump = 2
    new_portion = [{'role':'assistant', 'content':instance[-jump]["response"]}] + wrap_in_messages(f"This is incorrect. {text}\n{DEFAULT_BACKPROMPT_END(instance[-1]['prompt'][0])}")
    # then concatenate history properly
    initial_prompt = [instance[0]["prompt"][0]]
    if history_type == "full":
        if history_len == 1: backprompt = initial_prompt + new_portion
        else: backprompt = initial_prompt + instance[-jump]["prompt"][1:][-jump*(history_len-1):] + new_portion
    else: raise NotImplementedError()
    return backprompt


def wrap_in_messages(s):
    return [{'role':'user', 'content':s}]

#### Instance conversion script

if __name__ == "__main__":
    print(f"Generating instance text files from csv at {CSV_LOCATION}")
    instances = []
    with open(CSV_LOCATION) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            instances.append(row[1])
    for x in range(1,len(instances)):
        print(x)
        with open(f"{GAME24_DIRECTORY}instance-{x}.txt","w") as fp:
            fp.write(instances[x])
    print(f"Generated {len(instances)-1} instances")
