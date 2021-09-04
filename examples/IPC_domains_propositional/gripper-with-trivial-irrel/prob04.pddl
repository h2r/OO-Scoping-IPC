(define (problem strips-pgripper-x-4)
   (:domain gripper-painting-strips)
   (:objects rooma roomb ball10 ball9 ball8 ball7 ball6 ball5 ball4
             ball3 ball2 ball1 left right red blue)
   (:init (room rooma)
          (room roomb)
          (color red)
          (color blue)
          (ball ball10)
          (ball ball9)
          (ball ball8)
          (ball ball7)
          (ball ball6)
          (ball ball5)
          (ball ball4)
          (ball ball3)
          (ball ball2)
          (ball ball1)
          (ball-color ball4 red)
          (ball-color ball5 red)
          (ball-color ball6 red)
          (ball-color ball7 red)
          (ball-color ball8 red)
          (ball-color ball9 red)
          (ball-color ball10 red)
          (at-robby rooma)
          (free left)
          (free right)
          (at ball10 rooma)
          (at ball9 rooma)
          (at ball8 rooma)
          (at ball7 rooma)
          (at ball6 rooma)
          (at ball5 rooma)
          (at ball4 rooma)
          (at ball3 rooma)
          (at ball2 rooma)
          (at ball1 rooma)
          (gripper left)
          (gripper right))
   (:goal (and (at ball10 roomb)
               (at ball9 roomb)
               (at ball8 roomb)
               (at ball7 roomb)
               (at ball6 roomb)
               (at ball5 roomb)
               (at ball4 roomb)
               (at ball3 roomb)
               (at ball2 roomb)
               (at ball1 roomb))))