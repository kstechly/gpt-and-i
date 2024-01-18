import argparse
import csv
import re
import sympy
import json

CSV_LOCATION = "../data/game24/24.csv"
GAME24_DIRECTORY = "../data/game24/"

END_TAG = "[ANSWER END]"
DEFAULT_PROMPT_START = f"Use numbers and basic arithmetic operations (+ - * /) to obtain 24. You must write your response. Write your answer first, followed by {END_TAG}\n"
# \nInput: 4 4 6 8\nAnswer: (4 + 8) * (6 - 4) = 24
STOP_PHRASE = "Verifier confirmed success."
STOP_PHRASE_MASK = "Twenty-four achieved"

def DEFAULT_BACKPROMPT_END(instance_text):
    return f"Using the numbers {instance_text} please provide a correct expression that evaluates to 24. Write your answer first. At the end of your answer, write {END_TAG}\nAnswer: "

def check_answer(instance_text, equation):
    input_nums = instance_text.split(" ")
    expression = equation.strip().split('\n')[0].lower().split('=')[0]
    numbers = re.findall(r'\d+', expression)
    if sorted(numbers) != sorted(input_nums): return False, f"This expression consists of the numbers {', '.join(numbers)}, but it has to consist of only and exactly {input_nums}."
    try: return sympy.simplify(expression) == 24, f"This expression evaluates to {sympy.simplify(expression)} instead of 24."
    except: return False, "This expression is malformed."
    
def concat_trace(instance_output, divisor = 1):
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

#### Required Functions

def file_ending():
    return ".txt"

def generate(instance_text, problem_type):
    prompt = DEFAULT_PROMPT_START
    prompt+= f"Input: {instance_text}\nAnswer: "
    return prompt

def evaluate(instance_text, response_trace, problem_type="", backprompt_type=""):
    evaluation = []
    uniques = []
    input_nums = instance_text.split(" ")
    responses = response_trace["responses"] #list of responses as strings

    if backprompt_type=="llm":
        # rejigger responses so that it only contains solver responses
        raise NotImplementedError
    
    for response in responses:
        response_eval = {}
        response_eval["unique"] = False
        expression = response.strip().split('\n')[0].lower().split('=')[0].lower().replace(' ','')
        response_eval["expression"] = expression
        if expression not in uniques:
            response_eval["unique"] = True 
            uniques.append(expression)
        response_eval["correct"],_ = check_answer(instance_text, response)
        try: answer = sympy.simplify(expression)
        except: answer = "malformed"
        response_eval["eval"] = str(answer)
        response_eval["stopped"] = False
        evaluation.append(response_eval)
    # print(uniques)
    evaluation[-1]["stopped"] = response_trace["stopped"]
    return evaluation

def backprompt(instance_text, instance_output, backprompt_type):
    model_response = instance_output["responses"][-1]
    if backprompt_type == "llm":
        #free form feedback from the llm
        print(len(instance_output["responses"]))
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = json.loads(model_response)
            if llm_json["correct"]:
                return STOP_PHRASE
            backprompt = concat_trace(instance_output, divisor=2)
            backprompt += "Feedback: This is not correct.\n"
            backprompt += llm_json["feedback"]
            backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
            return backprompt
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= f"\nIf it is not correct, please give feedback on what is wrong and how to correct it."
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n   "feedback": "feedback",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
            return backprompt_query
    if backprompt_type == "llm-evaluate":
        #told to evaluate the number first
        print(len(instance_output["responses"]))
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = json.loads(model_response)
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
        print(len(instance_output["responses"]))
        if len(instance_output["responses"])%2==0:
            # Return generation prompt for even numbered responses, but first check for the stop phrase
            llm_json = json.loads(model_response)
            if llm_json["correct"]:
                return STOP_PHRASE
            return f"{concat_trace(instance_output)}Feedback: This is not correct. {DEFAULT_BACKPROMPT_END(instance_text)}"
        else:
            # Return checking prompt for odd numbered responses
            backprompt_query = f"Using each of the numbers {instance_text} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
            backprompt_query+= f"Please check if the following expression uses only the correct numbers (and no others) and evaluates to 24: " +model_response
            backprompt_query+= '\nRespond only in JSON format as described below:\n{\n"correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
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
    if check: return STOP_PHRASE
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