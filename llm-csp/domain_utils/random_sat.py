DEFAULT_PROMPT_START = "Given a list of requirements, you must provide a list of variable assignments that satisfies the requirements."
DEFAULT_PROMPT_MID = "You must satisfy ALL of the following requirements:"
DEFAULT_PROMPT_END = "If there is no assignment that satisfies the requirements, say \"Not satisfiable\". If there is an assignment that satisfies the requirements, please provide all variables assignments. Each assignment must be provided on a new line in the response and should be formatted as \"{VARIABLE LETTER}: {\"true\" if true \"false\" otherwise}\". Please do not provide anything else in your response."

from pysat.formula import CNF
from pysat.solvers import Solver

def cnf_to_text(cnf):
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

#### Required Functions

def file_ending():
    return ".cnf"

def generate(instance_text):
    prompt = DEFAULT_PROMPT_START
    cnf = CNF(from_string=instance_text)
    prompt += f"There are {cnf.nv} variables, A-{chr(ord('@')+cnf.nv)}."
    prompt += "\n" + DEFAULT_PROMPT_MID
    prompt += "\n" + cnf_to_text(cnf)
    prompt += "\n" + DEFAULT_PROMPT_END
    return prompt

def evaluate(instance_text, model_response):
    cnf = CNF(from_string=instance_text)
    var_assignments = [0 for _ in range(cnf.nv)]
    for line in model_response.split("\n"):
        assignment = line.strip().split(": ")
        var_number = ord(assignment[0]) - ord("@")
        var_assignments[var_number - 1] = 1 * var_number if assignment[1] == "true" else -1 * var_number
    missing = False
    #if missing a var assigment, mark wrong
    for i, va in enumerate(var_assignments):
        if va == 0:
            missing = True
    if missing == True:
        return False 
    #use solver to check 
    solver = Solver(bootstrap_with=cnf.clauses)
    return solver.solve(assumptions=var_assignments)

def backprompt(instance_text, model_response):
    raise NotImplementedError
    pass