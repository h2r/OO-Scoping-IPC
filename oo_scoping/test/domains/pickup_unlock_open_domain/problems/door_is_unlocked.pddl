(define (problem pickup-unlock-open-initial)
    (:domain pickup-unlock-open)

    (:objects
        d - door
    )

    (:init
        (not (has-key d))
        (is-unlocked d)
        (not (is-open d))
    )

    (:goal
        (is-open d)
    )
)
