(define (problem MINECRAFTCONTRIVED-3)
    (:domain minecraft-contrived)


(:objects
	steve - agent
	old-pointy - diamond-pickaxe
	dmd0 dmd1 dmd2 - diamond
	stick0 stick1 - stick
	rt0 rt1 rt2 rt3 rt4 rt5 rt6 rt7 rt8 rt9 rt10 rt11 rt12 rt13 rt14 rt15 rt16 rt17 rt18 rt19 - red-tulip
	df0 df1 df2 df3 df4 df5 df6 df7 df8 df9 df10 df11 - daisy-flower
	of0 of1 of2 - orchid-flower
	wb1 wb2 - wooden-block
	woolb1 woolb2 woolb3 - wool-block
)


(:init
	(agent-alive steve)
	(= (x steve) 0)
	(= (y steve) 0)
	(= (z steve) 0)
	( = ( agent-num-diamond steve ) 0 )
	( = ( agent-num-stick steve ) 0 )
	( = ( agent-num-diamond-pickaxe steve ) 1 )
	( = ( agent-num-apple steve ) 0 )
	( = ( agent-num-potato steve ) 0 )
	( = ( agent-num-rabbit steve ) 0 )
	( = ( agent-num-wool-block steve ) 2 )
	(= (x wb1) 11)
	(= (y wb1) 8)
	(= (z wb1) 0)
	(block-present wb1)
	(= (x wb2) 10)
	(= (y wb2) 8)
	(= (z wb2) 0)
	(block-present wb2)
	(= (x woolb1) 10)
	(= (y woolb1) 0)
	(= (z woolb1) 0)
	(block-present woolb1)
	( = ( block-hits wb1 ) 0 )
	( = ( block-hits wb2 ) 0 )
	(= (agent-num-wooden-block steve) 0)
	( = ( block-hits woolb1 ) 0 )
	( = ( block-hits woolb2 ) 0 )
	( = ( block-hits woolb3 ) 0 )
	(= (agent-num-wool-block steve) 2)
	( = ( item-hits rt0 ) 0 )
	( = ( item-hits rt1 ) 0 )
	( = ( item-hits rt2 ) 0 )
	( = ( item-hits rt3 ) 0 )
	( = ( item-hits rt4 ) 0 )
	( = ( item-hits rt5 ) 0 )
	( = ( item-hits rt6 ) 0 )
	( = ( item-hits rt7 ) 0 )
	( = ( item-hits rt8 ) 0 )
	( = ( item-hits rt9 ) 0 )
	( = ( item-hits rt10 ) 0 )
	( = ( item-hits rt11 ) 0 )
	( = ( item-hits rt12 ) 0 )
	( = ( item-hits rt13 ) 0 )
	( = ( item-hits rt14 ) 0 )
	( = ( item-hits rt15 ) 0 )
	( = ( item-hits rt16 ) 0 )
	( = ( item-hits rt17 ) 0 )
	( = ( item-hits rt18 ) 0 )
	( = ( item-hits rt19 ) 0 )
	(= (agent-num-red-tulip steve) 0)
	( = ( item-hits of0 ) 0 )
	( = ( item-hits of1 ) 0 )
	( = ( item-hits of2 ) 0 )
	(= (agent-num-orchid-flower steve) 0)
	( = ( item-hits df0 ) 0 )
	( = ( item-hits df1 ) 0 )
	( = ( item-hits df2 ) 0 )
	( = ( item-hits df3 ) 0 )
	( = ( item-hits df4 ) 0 )
	( = ( item-hits df5 ) 0 )
	( = ( item-hits df6 ) 0 )
	( = ( item-hits df7 ) 0 )
	( = ( item-hits df8 ) 0 )
	( = ( item-hits df9 ) 0 )
	( = ( item-hits df10 ) 0 )
	( = ( item-hits df11 ) 0 )
	(= (agent-num-daisy-flower steve) 0)
	(= (x old-pointy) 0)
	(= (y old-pointy) 0)
	(= (z old-pointy) 0)
	( not ( present old-pointy ) )
	(= (x stick0) 1)
	(= (y stick0) 0)
	(= (z stick0) 0)
	( present stick0 )
	(= (x stick1) 1)
	(= (y stick1) 1)
	(= (z stick1) 0)
	( present stick1 )
	(= (x dmd0) 2)
	(= (y dmd0) 0)
	(= (z dmd0) 0)
	(present dmd0)
	(= (x dmd1) 2)
	(= (y dmd1) 1)
	(= (z dmd1) 0)
	(present dmd1)
	(= (x dmd2) 2)
	(= (y dmd2) 2)
	(= (z dmd2) 0)
	(present dmd2)
	(= (x rt0) 2)
	(= (y rt0) 6)
	(= (z rt0) 0)
	( present rt0 )
	(= (x rt1) 3)
	(= (y rt1) 6)
	(= (z rt1) 0)
	( present rt1 )
	(= (x rt2) 4)
	(= (y rt2) 6)
	(= (z rt2) 0)
	( present rt2 )
	(= (x rt3) 5)
	(= (y rt3) 6)
	(= (z rt3) 0)
	( present rt3 )
	(= (x rt4) 6)
	(= (y rt4) 6)
	(= (z rt4) 0)
	( present rt4 )
	(= (x rt5) 7)
	(= (y rt5) 6)
	(= (z rt5) 0)
	( present rt5 )
	(= (x rt6) 8)
	(= (y rt6) 6)
	(= (z rt6) 0)
	( present rt6 )
	(= (x rt7) 8)
	(= (y rt7) 5)
	(= (z rt7) 0)
	( present rt7 )
	(= (x rt8) 8)
	(= (y rt8) 4)
	(= (z rt8) 0)
	( present rt8 )
	(= (x rt9) 8)
	(= (y rt9) 3)
	(= (z rt9) 0)
	( present rt9 )
	(= (x rt10) 8)
	(= (y rt10) 2)
	(= (z rt10) 0)
	( present rt10 )
	(= (x rt11) 7)
	(= (y rt11) 2)
	(= (z rt11) 0)
	( present rt11 )
	(= (x rt12) 6)
	(= (y rt12) 2)
	(= (z rt12) 0)
	( present rt12 )
	(= (x rt13) 5)
	(= (y rt13) 2)
	(= (z rt13) 0)
	( present rt13 )
	(= (x rt14) 4)
	(= (y rt14) 2)
	(= (z rt14) 0)
	( present rt14 )
	(= (x rt15) 3)
	(= (y rt15) 2)
	(= (z rt15) 0)
	( present rt15 )
	(= (x rt16) 2)
	(= (y rt16) 2)
	(= (z rt16) 0)
	( present rt16 )
	(= (x rt17) 2)
	(= (y rt17) 3)
	(= (z rt17) 0)
	( present rt17 )
	(= (x rt18) 2)
	(= (y rt18) 4)
	(= (z rt18) 0)
	( present rt18 )
	(= (x rt19) 2)
	(= (y rt19) 5)
	(= (z rt19) 0)
	( present rt19 )
	(= (x df0) 3)
	(= (y df0) 5)
	(= (z df0) 0)
	( present df0 )
	(= (x df1) 4)
	(= (y df1) 5)
	(= (z df1) 0)
	( present df1 )
	(= (x df2) 5)
	(= (y df2) 5)
	(= (z df2) 0)
	( present df2 )
	(= (x df3) 6)
	(= (y df3) 5)
	(= (z df3) 0)
	( present df3 )
	(= (x df4) 7)
	(= (y df4) 5)
	(= (z df4) 0)
	( present df4 )
	(= (x df5) 7)
	(= (y df5) 4)
	(= (z df5) 0)
	( present df5 )
	(= (x df6) 7)
	(= (y df6) 3)
	(= (z df6) 0)
	( present df6 )
	(= (x df7) 6)
	(= (y df7) 3)
	(= (z df7) 0)
	( present df7 )
	(= (x df8) 5)
	(= (y df8) 3)
	(= (z df8) 0)
	( present df8 )
	(= (x df9) 4)
	(= (y df9) 3)
	(= (z df9) 0)
	( present df9 )
	(= (x df10) 3)
	(= (y df10) 3)
	(= (z df10) 0)
	( present df10 )
	(= (x df11) 3)
	(= (y df11) 4)
	(= (z df11) 0)
	( present df11 )
	(= (x of0) 4)
	(= (y of0) 4)
	(= (z of0) 0)
	( present of0 )
	(= (x of1) 5)
	(= (y of1) 4)
	(= (z of1) 0)
	( present of1 )
	(= (x of2) 6)
	(= (y of2) 4)
	(= (z of2) 0)
	( present of2 )
)


(:goal (and
                (= (x steve) 3)
                (= (y steve) 4)
                (= (z steve) 0)
            )
        )
        


)