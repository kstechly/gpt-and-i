from typing import Dict, List, Optional

from csp import AbstractConstraint, CSP


class MapColoringConstraint(AbstractConstraint[str, str]):
    def __init__(self, place1: str, place2: str) -> None:
        super().__init__([place1, place2])
        self.place1: str = place1
        self.place2: str = place2

    def satisfied(self, assignment: Dict[str, str]) -> bool:
        # If either place is not in the assignment then it is not
        # yet possible for their colors to be conflicting
        if self.place1 not in assignment or self.place2 not in assignment:
            return True
        # check the color assigned to place1 is not the same as the
        # color assigned to place2
        return assignment[self.place1] != assignment[self.place2]

    
def map_coloring_solution():
    """
    solution = {
        'Western Australia': 'red',
        'Northern Territory': 'green',
        'South Australia': 'blue',
        'Queensland': 'red',
        'New South Wales': 'green',
        'Victoria': 'red',
        'Tasmania': 'green'
    }"""

    variables: List[str] = [
        "Western Australia", "Northern Territory", "South Australia",
        "Queensland", "New South Wales", "Victoria", "Tasmania"
    ]

    constraints = [
        [0, 1], [0, 2], [2, 1], [3, 1], [3, 2], [3, 4], [4, 2], [5, 2], [5, 4], [5, 6]
    ]

    domains: Dict[str, List[str]] = {}
    for variable in variables:
        domains[variable] = ["red", "green", "blue"]

    csp: CSP[str, str] = CSP(variables, domains)

    for c in constraints:
        csp.add_constraint(MapColoringConstraint(variables[c[0]],variables[c[1]]))

    solution: Optional[Dict[str, str]] = csp.backtracking_search()
    return solution

if __name__ == '__main__':
    print(map_coloring_solution())
    