from pysat.formula import CNF
from pysat.solvers import Solver

stuff = []
for i in range(1,100):
    stuff.append(CNF(f"instance-{i}.cnf"))
    print(stuff)

print(len(stuff)==len(set(stuff)))
