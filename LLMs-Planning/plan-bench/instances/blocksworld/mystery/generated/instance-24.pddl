(define (problem BW-generalization-4)
(:domain mystery-4ops)(:objects f b d k j l h e i)
(:init 
(harmony)
(planet f)
(planet b)
(planet d)
(planet k)
(planet j)
(planet l)
(planet h)
(planet e)
(planet i)
(province f)
(province b)
(province d)
(province k)
(province j)
(province l)
(province h)
(province e)
(province i)
)
(:goal
(and
(craves f b)
(craves b d)
(craves d k)
(craves k j)
(craves j l)
(craves l h)
(craves h e)
(craves e i)
)))