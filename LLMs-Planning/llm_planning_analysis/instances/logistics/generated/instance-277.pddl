(define (problem LG-generalization)
(:domain logistics-strips)(:objects c0 t0 a0 l0-5 p2 l0-1 p3 l0-7 p4 l0-4 p0 l0-2 p1 l0-3 l0-0 l0-6)
(:init 
(CITY c0)
(TRUCK t0)
(AIRPLANE a0)
(LOCATION l0-5)
(in-city l0-5 c0)
(OBJ p2)
(at p2 l0-5)
(at t0 l0-5)
(LOCATION l0-1)
(in-city l0-1 c0)
(OBJ p3)
(at p3 l0-1)
(LOCATION l0-7)
(in-city l0-7 c0)
(OBJ p4)
(at p4 l0-7)
(LOCATION l0-4)
(in-city l0-4 c0)
(OBJ p0)
(at p0 l0-4)
(LOCATION l0-2)
(in-city l0-2 c0)
(OBJ p1)
(at p1 l0-2)
(LOCATION l0-3)
(in-city l0-3 c0)
(LOCATION l0-0)
(in-city l0-0 c0)
(LOCATION l0-6)
(in-city l0-6 c0)
(AIRPORT l0-6)
(at a0 l0-6)
)
(:goal
(and
(at p2 l0-1)
(at p3 l0-7)
(at p4 l0-4)
(at p0 l0-2)
)))