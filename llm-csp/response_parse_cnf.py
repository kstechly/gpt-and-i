from pysat.formula import CNF
from pysat.solvers import Solver

var_assignments = [0 for _ in range(20)]

cnf_file_name = "data/uf20-0999.cnf"

with open("responses/response.txt", "r+") as file:
    for line in file:
        assignment = line.strip().split(": ")
        var_number = ord(assignment[0]) - ord("@")
        var_assignments[var_number - 1] = 1 * var_number if assignment[1] == "true" else -1 * var_number

for i, va in enumerate(var_assignments):
    if va == 0:
        print(f"Warning: var assignment missing for variable {i + 1}")

print(var_assignments)

cnf = CNF("data/uf20-0999.cnf")
solver = Solver(bootstrap_with=cnf.clauses)
print(solver.solve(assumptions=var_assignments))
