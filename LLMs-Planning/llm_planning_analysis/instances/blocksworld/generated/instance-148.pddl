(define (problem BW-generalization-4)
(:domain blocksworld-4ops)(:objects j g l k e d h f a c)
(:init 
(handempty)
(ontable j)
(ontable g)
(ontable l)
(ontable k)
(ontable e)
(ontable d)
(ontable h)
(ontable f)
(ontable a)
(ontable c)
(clear j)
(clear g)
(clear l)
(clear k)
(clear e)
(clear d)
(clear h)
(clear f)
(clear a)
(clear c)
)
(:goal
(and
(on j g)
(on g l)
(on l k)
(on k e)
(on e d)
(on d h)
(on h f)
(on f a)
(on a c)
)))