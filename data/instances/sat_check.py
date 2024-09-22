from pysat.formula import CNF
from pysat.solvers import Solver

total = 0
total_correct = 0
for x in range(1,101):
    cnf = CNF(f"instance-{x}.cnf")
    solver = Solver(bootstrap_with=cnf.clauses)
    total+=1
    total_correct+=int(solver.solve())

print(total)
print(total_correct)
print(total_correct/total)
