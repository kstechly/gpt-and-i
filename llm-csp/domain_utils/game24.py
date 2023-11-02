import argparse
import csv
import re
import sympy

CSV_LOCATION = "../data/game24/24.csv"
GAME24_DIRECTORY = "../data/game24/"

END_TAG = "[ANSWER END]"
DEFAULT_PROMPT_START = f"Use numbers and basic arithmetic operations (+ - * /) to obtain 24. You must write your response Write your answer first. At the end of your answer, write {END_TAG}\n"
# \nInput: 4 4 6 8\nAnswer: (4 + 8) * (6 - 4) = 24
STOP_PHRASE = "Verifier confirmed success."

def DEFAULT_BACKPROMPT_END(instance_text):
    return f"Using the numbers {instance_text} please provide a correct expression that evaluates to 24. Write your answer first. At the end of your answer, write {END_TAG}\nAnswer: "

def check_answer(instance_text, equation):
    input_nums = instance_text.split(" ")
    expression = equation.strip().split('\n')[-1].lower().replace('answer: ', '').split('=')[0]
    numbers = re.findall(r'\d+', expression)
    if sorted(numbers) != sorted(input_nums):
        print(equation)
        return False, f"This expression consists of the numbers {', '.join(numbers)}, but it has to consist of only and exactly {input_nums}."
    try:
        #print(sympy.simplify(expression))
        return sympy.simplify(expression) == 24, f"This expression evaluates to {sympy.simplify(expression)} instead of 24."
    except Exception as e:
        print(e)
        print(expression)
        return False, "This expression is malformed."

#### Required Functions

def file_ending():
    return ".txt"

def generate(instance_text, problem_type):
    prompt = DEFAULT_PROMPT_START
    prompt+= f"Input: {instance_text}\nAnswer: "
    return prompt

def evaluate(instance_text, response_trace, problem_type=""):
    evaluation = {}
    input_nums = instance_text.split(" ")
    #TODO put this in a function and reuse it between domains
    response_keys = [x for x in response_trace if "response" in x]
    backprompt_keys = [x for x in response_trace if "backprompt" in x]
    last_response = "response"
    last_backprompt = ""
    if len(response_keys)>1:
        last_response = f"response {len(response_keys)-2}"
    if len(backprompt_keys)>1:
        last_backprompt = f"backprompt {len(backprompt_keys)-1}"
    evaluation["correct"],_ = check_answer(instance_text, response_trace[last_response])
    evaluation["number of backprompts before correct"] = 0
    answers = []
    for x in response_keys:
        evaluation[x],_ = check_answer(instance_text,response_trace[x])
        expression = response_trace[x].strip().split('\n')[-1].lower().replace('answer: ', '').split('=')[0]
        answer = "malformed"
        try:
            answer = sympy.simplify(expression)
        except Exception as e: 
            print(e)
        evaluation[f"{x} eval"] = str(answer)
        answers.append(answer)
        if not evaluation["number of backprompts before correct"] and evaluation[x] and not x == "response":
            evaluation["number of backprompts before correct"] = int(x[-2:])
    evaluation["number of backprompts"] = len(response_keys)-1
    evaluation["unique answers"] = len(list(set(answers)))

    evaluation["stopped"] = False
    if not last_backprompt or STOP_PHRASE.replace(".", "") in response_trace[last_backprompt]:
        evaluation["stopped"] = True

    #TODO check how many different answers it has generated (basic version: eval each, check num unique final answers)


    evaluation["ever correct"] = False
    evaluation["total correct"] = 0
    for key in response_keys:
        check,_ = check_answer(instance_text, response_trace[key])
        if check:
            evaluation["ever correct"] = True
            evaluation["total correct"]+=1
    return evaluation

def backprompt(instance_text, model_response, backprompt_type):
    check, reason = check_answer(instance_text, model_response)
    if backprompt_type == "llm-query":
        backprompt_query = f"Using exactly one (no more, no fewer) of each of the numbers {instance_text} and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
        backprompt_query+= f"Please check if the following expression uses exactly one of each number and evaluates to 24: " +model_response
        backprompt_query+= f"\nIf it is, say '{STOP_PHRASE}' Do not provide anything else in your response. If it is not correct, please give feedback on what is wrong and how to correct it."
        return backprompt_query
    elif backprompt_type == "llm-wrapper":
        backprompt = "Feedback: This is not correct.\n"
        backprompt += model_response
        backprompt += f"\n\nWith this feedback, please try again. {DEFAULT_BACKPROMPT_END(instance_text)}"
        return backprompt
    elif check:
        return STOP_PHRASE
    if backprompt_type == "passfail":
        return f"Feedback: This is not correct. {DEFAULT_BACKPROMPT_END(instance_text)}"
    elif backprompt_type == "first":
        return f"Feedback: This is not correct. {reason} {DEFAULT_BACKPROMPT_END(instance_text)}"
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