from typing import Dict, List, Optional

from csp import AbstractConstraint, CSP


class NQueensConstraint(AbstractConstraint[int, int]):
    def __init__(self, _columns: List[int]) -> None:
        super().__init__(_columns)
        self.columns: List[int] = _columns

    def satisfied(self, _assignment: Dict[int, int]) -> bool:
        # q1c = queen 1 column, q1r = queen 1 row
        for q1c, q1r in _assignment.items():
            # q2c = queen 2 column
            for q2c in range(q1c + 1, len(self.columns) + 1):
                if q2c in _assignment:
                    q2r: int = _assignment[q2c]  # q2r = queen 2 row
                    if q1r == q2r:  # same row?
                        return False
                    if abs(q1r - q2r) == abs(q1c - q2c):  # same diagonal?
                        return False
        return True  # no conflict


def main():
    """
    solution = {1: 1, 2: 5, 3: 8, 4: 6, 5: 3, 6: 7, 7: 2, 8: 4}
    """

    variables: List[int] = [1, 2, 3, 4, 5, 6, 7, 8]

    domains: Dict[int, List[int]] = {}
    for variable in variables:
        domains[variable] = [1, 2, 3, 4, 5, 6, 7, 8]

    csp: CSP[int, int] = CSP(variables, domains)
    csp.add_constraint(NQueensConstraint(variables))

    solution: Optional[Dict[str, str]] = csp.backtracking_search()
    print(solution)


if __name__ == '__main__':
    main()