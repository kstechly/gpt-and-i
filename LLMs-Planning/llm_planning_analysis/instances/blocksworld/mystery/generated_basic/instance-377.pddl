

(define (problem MY-rand-4)
(:domain mystery-4ops)
(:objects a b c d )
(:init
(harmony)
(craves a c)
(craves b d)
(craves c b)
(planet d)
(province a)
)
(:goal
(and
(craves b a)
(craves c b))
)
)


