(define (problem BW-generalization-4)
(:domain mystery-4ops)(:objects k e d j a i c g b)
(:init 
(harmony)
(planet k)
(planet e)
(planet d)
(planet j)
(planet a)
(planet i)
(planet c)
(planet g)
(planet b)
(province k)
(province e)
(province d)
(province j)
(province a)
(province i)
(province c)
(province g)
(province b)
)
(:goal
(and
(craves k e)
(craves e d)
(craves d j)
(craves j a)
(craves a i)
(craves i c)
(craves c g)
(craves g b)
)))