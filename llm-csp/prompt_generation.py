from utils import *
import json
import os

START = 1
END = 1
DEFAULT_PROMPT_START = "You are tasked with solving a boolean satisfiability problem. Given a list of requirements, you must provide a list of variable assignments that satisfies the requirements."
DEFAULT_PROMPT_MID = "You must satisfy ALL of the following requirements:"
DEFAULT_PROMPT_END = "If there is no assignment that satisfies the requirements, say \"Not satisfiable\". If there is an assignment that satisfies the requirements, please provide all variables assignments. Each assignment must be provided on a new line in the response and should be formatted as \"{VARIABLE LETTER}: {\"true\" if true \"false\" otherwise}\". Please do not provide anything else in your response."

from pysat.formula import CNF
from pysat.solvers import Solver

def cnf_to_text(cnf_location):
    cnf = CNF(cnf_location)
    cumulative_requirement_text = ""

    for i, clause in enumerate(cnf.clauses):
        single_requirement_text = f"Requirement {i + 1}: "
        is_first = True
        for var in clause:
            letter_var = chr(ord('@')+abs(var))
            var_req = "true" if var > 0 else "false"
            if not is_first:
                single_requirement_text += ", or "
            is_first = False
            single_requirement_text += f"{letter_var} must be {var_req}"
        cumulative_requirement_text += single_requirement_text + "\n"

    return cumulative_requirement_text

if __name__=="__main__":
    prompts = {}
    for x in range(START-1,END):
        prompt = DEFAULT_PROMPT_START
        cnf = CNF(f"data/instance-{x+1}.cnf")
        prompt += f"There are {cnf.nv} variables, A-{chr(ord('@')+cnf.nv)}."
        prompt += "\n" + DEFAULT_PROMPT_MID
        prompt += "\n" + cnf_to_text(f"data/instance-{x+1}.cnf")
        prompt += "\n" + DEFAULT_PROMPT_END

        prompts[f"{x+1}"] = prompt
    
    os.makedirs("prompts", exist_ok=True)
    with open("prompts/prompts.json", "w") as f:
        json.dump(prompts, f, indent = 4)
