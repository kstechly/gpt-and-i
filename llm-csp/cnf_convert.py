from pysat.formula import CNF
from pysat.solvers import Solver

MAX_VARIABLE = 20
MIN_VARIABLE = 1

cnf = CNF("data/uf20-0999.cnf")
print(cnf.clauses)

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

print(cumulative_requirement_text)

solver = Solver(bootstrap_with=cnf.clauses)

print(solver.solve())
