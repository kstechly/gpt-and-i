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

GAME24_DIRECTORY = "data/game24/"
GAME24_V_DIRECTORY = "data/game24_verification/"

WRONG_NUMBERS_PHRASE = "WRONG NUMBERS."
WRONG_EVAL_PHRASE = "NOT 24."
operations = ["*","+","-","/"]

def merge(number1, number2, operation):
    if operation == "*": return number1[0]*number2[0], f"({number1[1]}*{number2[1]})"
    if operation == "+": return number1[0]+number2[0], f"({number1[1]}+{number2[1]})"
    if operation == "-": return number1[0]-number2[0], f"({number1[1]}-{number2[1]})"
    if operation == "/" and number2[0] != Fraction(): return number1[0]/number2[0], f"({number1[1]}/{number2[1]})"
    elif operation == "/" and number1[0] != Fraction(): return number2[0]/number1[0], f"({number2[1]}/{number1[1]})"
    else: return number1[0]*number2[0], f"({number1[1]}*{number2[1]})"

def random_expression(numbers_text):
    input_nums = numbers_text.split(" ")
    ordered_nums = [(Fraction(x), str(x)) for x in input_nums]
    random.shuffle(ordered_nums)
    op1 = random.choice(operations)
    op2 = random.choice(operations)
    op3 = random.choice(operations)
    workspace = [merge(ordered_nums[0], ordered_nums[1], op1), ordered_nums[2], ordered_nums[3]]
    remaining_ops = [op2, op3]
    while len(workspace)>1:
        new_op = remaining_ops.pop()
        item1 = random.choice(workspace)
        workspace.remove(item1)
        item2 = random.choice(workspace)
        workspace.remove(item2)
        workspace.append(merge(item1, item2, new_op))   
    return workspace[0]

################
if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-s','--start', type=int, default=1, help='start index')
    # parser.add_argument('-e', '--end', type=int, default=100, help='end index')
    # args = parser.parse_args()
    # start = args.start
    # end = args.end
    print(f"Randomly solving instances 901-1000 in {GAME24_DIRECTORY}")
    numbers = {}
    by_prompt_num = {}
    max_prompt = 0
    total = []
    
    for sample in range(0,100):
        total_for_sample = 0
        counter_for_sample = 0
        while counter_for_sample <70:
            for instance in os.listdir(GAME24_DIRECTORY):
                if instance.startswith("instance-"):
                    instance_num = int(instance.split("-")[1].split(".txt")[0])
                    if 900 < instance_num < 1001:
                        with open(GAME24_DIRECTORY+instance,"r") as fp:
                            instance_text = fp.read()
                        numbers_text = instance_text.split("\n")[0]
                        expression_pair = random_expression(numbers_text)
                        total_for_sample +=1
                        if expression_pair[0] == Fraction(24):
                            counter_for_sample+=1
        print(f"Sample {sample}: {total_for_sample/70}")
        total.append(total_for_sample/70)
            # if 900 < instance_num < 1001:
            #     #print(f"==Sampling for instance {instance_num}==")
            #     numbers[instance_num] = 0
            #     by_prompt_num[instance_num] = {}
            #     for sample in range(0,100):
            #         with open(GAME24_DIRECTORY+instance,"r") as fp:
            #             instance_text = fp.read()
            #         numbers_text = instance_text.split("\n")[0]
            #         #correct expression
            #         expression_pair = [0,""]
            #         prompt_num = 0
            #         while expression_pair[0] != Fraction(24):
            #             prompt_num+=1
            #             numbers[instance_num]= numbers[instance_num]+1
            #             expression_pair = random_expression(numbers_text)
            #             #print(f"Try {numbers[instance_num]}: {expression_pair}")
            #         #print(f"{expression_pair[1]} took {numbers[instance_num]} tries")
            #         #print(f"correct: {game24.check_answer(instance_text,expression_pair[1])}")
            #         if prompt_num in by_prompt_num[instance_num]:
            #             by_prompt_num[instance_num][prompt_num] = by_prompt_num[instance_num][prompt_num]+1
            #         else:
            #             by_prompt_num[instance_num][prompt_num] = 1
            #         if prompt_num > max_prompt: max_prompt = prompt_num
            #     numbers[instance_num] = numbers[instance_num]/100
    # print(numbers.values())
    # print(sum(numbers.values())/len(numbers.values()))
    # #output the best 70
    # avgs = sorted(numbers.values())
    # print("==Best 70==")
    # print(avgs[:70])
    # print(sum(avgs[:70])/70)
    # #output the by_prompt_num stuff
    # print("==By Prompt Num==")
    # by_prompt_num_sum = [0]*(max_prompt+1)
    # print(max_prompt)
    # for instance_num in by_prompt_num:
    #     for prompt_num in by_prompt_num[instance_num]:
    #         print(prompt_num)
    #         print(by_prompt_num[instance_num])
    #         print(max_prompt)
    #         by_prompt_num_sum[prompt_num] = by_prompt_num_sum[prompt_num] + by_prompt_num[instance_num][prompt_num]
    # cumulative_by_prompt_num_sum = [sum(by_prompt_num_sum[:x+1])/100 for x in range(0,len(by_prompt_num_sum))]
    # print(cumulative_by_prompt_num_sum)            
    print(total)
    print(sum(total)/len(total))