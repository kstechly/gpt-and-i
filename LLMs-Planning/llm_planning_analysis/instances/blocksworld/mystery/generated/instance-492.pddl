(define (problem BW-generalization-4)
(:domain mystery-4ops)(:objects c h d i g j)
(:init 
(harmony)
(planet c)
(planet h)
(planet d)
(planet i)
(planet g)
(planet j)
(province c)
(province h)
(province d)
(province i)
(province g)
(province j)
)
(:goal
(and
(craves c h)
(craves h d)
(craves d i)
(craves i g)
(craves g j)
)))