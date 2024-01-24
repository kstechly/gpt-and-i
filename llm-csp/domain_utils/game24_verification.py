try: 
    from domain_utils import game24
except:
    import game24
import os
import argparse
import random
import json
import re
import sympy
from fractions import Fraction

GAME24_DIRECTORY = game24.GAME24_DIRECTORY
GAME24_V_DIRECTORY = "../data/game24_verification/"

WRONG_NUMBERS_PHRASE = "WRONG NUMBERS."
WRONG_EVAL_PHRASE = "NOT 24."
operations = ["*","+","-","/"]

def generate_correct(numbers_text):
    #basic dfs
    input_nums = numbers_text.split(" ")
    input_nums = [(Fraction(x), str(x)) for x in input_nums]
    return loop_solve(input_nums)[1]
    
def loop_solve(input_nums):
    for first_num in input_nums:
        input_nums2 = list(input_nums)
        input_nums2.remove(first_num)
        for second_num in input_nums2:
            for operation in operations:
                if second_num[0] == Fraction() and operation == "/": continue
                input_nums3 = list(input_nums2)
                input_nums3.remove(second_num)
                input_nums3.append(merge(first_num, second_num, operation))
                if len(input_nums3) == 1: 
                    if input_nums3[0][0] == Fraction(24): return input_nums3[0]
                else:
                    looped = loop_solve(input_nums3)
                    try:
                        if looped[0] == Fraction(24): return looped
                    except: continue

def merge(number1, number2, operation):
    if operation == "*": return number1[0]*number2[0], f"({number1[1]}*{number2[1]})"
    if operation == "+": return number1[0]+number2[0], f"({number1[1]}+{number2[1]})"
    if operation == "-": return number1[0]-number2[0], f"({number1[1]}-{number2[1]})"
    if operation == "/": return number1[0]/number2[0], f"({number1[1]}/{number2[1]})"
        
def ablate_operation(correct_expression):
    ops = [x for x in operations if x in correct_expression]
    original_op = random.choice(ops)
    new_ops = list(operations)
    new_ops.remove(original_op)
    new_op = random.choice(new_ops)
    return re.sub(f"\\{original_op}", new_op, correct_expression, count=1)

def ablate_number(correct_expression, numbers_text):
    input_nums = numbers_text.split(" ")
    original_num = str(random.choice(input_nums))
    new_num = str(random.choice(range(1,13)))
    if new_num==original_num: return ablate_number(correct_expression, numbers_text)
    return re.sub(original_num, new_num, correct_expression, count=1)

def random_expression(numbers_text):
    input_nums = numbers_text.split(" ")
    ordered_nums = [(Fraction(x), str(x)) for x in input_nums]
    random.shuffle(ordered_nums)
    op1 = random.choice(operations)
    op2 = random.choice(operations)
    op3 = random.choice(operations)
    return merge(merge(merge(ordered_nums[0], ordered_nums[1], op1), ordered_nums[2], op2), ordered_nums[3], op3)[1]

#################### REQUIRED FUNCTIONS

def file_ending():
    return ".txt"

def generate(instance_text, problem_type):
    # format (stored in data/game24_verification) is numbers instance with lines appended giving expressions of various types
    if "-no-info" in problem_type:
        problem_type = problem_type.split("-no-info")[0]
        if problem_type not in instance_text:
            print(f"There is no {problem_type} key in {instance_text}")
        prompt = f"Please evaluate the following expression: "
        prompt+= instance_text.split(problem_type)[1].split("\n")[0] + "\n"
        prompt+= '\nRespond only in JSON format as described below:\n{\n   "evaluation": "number the expression evaluated to"}\nEnsure that Python\'s json.loads can parse this.'
        prompt+= f"Do not provide anything else in your response."
        return prompt
    if problem_type not in instance_text:
        print(f"There is no {problem_type} key in {instance_text}")
    numbers = instance_text.split("\n")[0]
    prompt = f"Using each of the numbers {numbers} exactly as many times as they appear in the list and the basic arithmetic operations (+ - * /), it is possible to write an expression that evaluates to 24. "
    prompt = f"Please check if the following expression uses only the given numbers (and no others) and evaluates to 24: "
    prompt+= instance_text.split(problem_type)[1].split("\n")[0] + "\n"
    prompt+= '\nRespond only in JSON format as described below:\n{\n   "evaluation": "number the expression evaluated to",\n   "correct": boolean}\nEnsure that Python\'s json.loads can parse this.'
    # prompt+= "In your first line, write only 'EVALUATION: ' followed by the number the given expression evaluates to. In the following line, you will give more precise feedback.\n"
    # prompt+= f"If the expression uses the wrong numbers, too many, or too few of the given numbers, say '{WRONG_NUMBERS_PHRASE}. "
    # prompt+= f"If the expression does not evaluate to 24, say '{WRONG_EVAL_PHRASE}'. "
    # prompt+= f"If the expression uses the given numbers correctly, and evaluates to 24, say '{game24.STOP_PHRASE}'. "
    prompt+= f"Do not provide anything else in your response."
    return prompt

def evaluate(instance_text, response_trace, problem_type="", backprompt_type=""):
    evaluation = {}
    expression = instance_text.split(problem_type.split("-no-info")[0])[1].split("\n")[0].strip()
    try: evaluation["correct simplification"] = sympy.simplify(expression) is response_trace["responses"][-1]["evaluation"]
    except: evaluation["correct simplification"] = False
    if "-no-info" in problem_type: evaluation["correct"] = evaluation["correct simplification"]
    else: evaluation["correct"] = game24.check_answer(expression)[0] is response_trace["responses"][-1]["correct"]
    return evaluation

def backprompt(instance_text, model_response, backprompt_type):
    raise NotImplementedError("No backprompting for verification")

################
if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-s','--start', type=int, default=1, help='start index')
    # parser.add_argument('-e', '--end', type=int, default=100, help='end index')
    # args = parser.parse_args()
    # start = args.start
    # end = args.end
    print(f"Generating proposed solutions for all instances in {GAME24_DIRECTORY}")
    llm_directory = "../responses/game24/gpt-4-0613_chat/backprompting-passfail/"
    with open(f"{llm_directory}responses.json", "r") as fp:
        output = json.load(fp)
    for instance in os.listdir(GAME24_DIRECTORY):
        if instance.startswith("instance-"):
            with open(GAME24_DIRECTORY+instance,"r") as fp:
                instance_text = fp.read()
            numbers_text = instance_text.split("\n")[0]
            #correct expression
            expression_text = generate_correct(numbers_text)
            correct_text = expression_text
            print(f"correct: {game24.check_answer(instance_text,expression_text)}")
            new_instance = f"{instance_text}\ncorrect {expression_text}"
            #ablated operation expression
            expression_text = ablate_operation(correct_text)
            print(f"ablated operation: {game24.check_answer(instance_text,expression_text)}")
            new_instance+= f"\nablated_op {expression_text}"
            #wrong number expression
            expression_text = ablate_number(correct_text, numbers_text)
            print(f"ablated number: {game24.check_answer(instance_text,expression_text)}")
            new_instance+= f"\nablated_number {expression_text}"
            # #random expression
            expression_text = random_expression(numbers_text)
            print(f"random: {game24.check_answer(instance_text, expression_text)}")
            new_instance+= f"\nrandom {expression_text}"
            # randomly chosen from LLM generations
            expression_text = ""
            instance_num = instance.split("-")[1].split(".txt")[0]
            if instance_num in output:
                responses = output[instance_num]['responses']
                expression_text = random.choice(responses)
                print(f"llm: {game24.check_answer(instance_text, expression_text)}")
                new_instance+=f"\nllm {expression_text}"
            with open(GAME24_V_DIRECTORY+instance, "w") as fp:
                fp.write(new_instance)