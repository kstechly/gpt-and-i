(define (problem BW-generalization-4)
(:domain mystery-4ops)(:objects k c a b e i d f l h)
(:init 
(harmony)
(planet k)
(planet c)
(planet a)
(planet b)
(planet e)
(planet i)
(planet d)
(planet f)
(planet l)
(planet h)
(province k)
(province c)
(province a)
(province b)
(province e)
(province i)
(province d)
(province f)
(province l)
(province h)
)
(:goal
(and
(craves k c)
(craves c a)
(craves a b)
(craves b e)
(craves e i)
(craves i d)
(craves d f)
(craves f l)
(craves l h)
)))