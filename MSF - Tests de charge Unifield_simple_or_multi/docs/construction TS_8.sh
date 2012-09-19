#!/bin/bash

#1.xml
#boucle de 1 à 4 pour analytic_distribution


#2.xml
#on retrouve la boucle de 1 à 4 de analytic_distribution
#boucle de 1 à 4 pour cost_center_distribution_line/1

#3.xml
#analytic_distribution de 2 à 4
#funding_pool_distribution_line de 1 à 3

#4.xml
#account_move_line autant de fois que nécessaire de 1 à 28
#account_analytic_line autant de fois que nécessaire de 1 à 28



for analytic_line in {2..28}; do

	# first value is 5
	one=$((($analytic_line-1)*4+1))

	cp 1.xml $one.xml;

	two=$(($one+1))
	cp 2.xml $two.xml;

	three=$(($one+2))
	cp 3.xml $three.xml;

	four=$(($one+3))
	cp 4.xml $four.xml;



# analytic_distribution dans 1, 2, 3
	# cost_center_distribution_line dans 2
# funding_pool_distribution_line dans 3
# account_move_line dans 4
# account_analytic_line dans 4


	# 1.xml
	sed -i "s/analytic_distribution\/1/analytic_distribution\/$one/" $one.xml;
	sed -i "s/analytic_distribution\/2/analytic_distribution\/$two/" $one.xml;
	sed -i "s/analytic_distribution\/3/analytic_distribution\/$three/" $one.xml;
	sed -i "s/analytic_distribution\/4/analytic_distribution\/$four/" $one.xml;

	# 2.xml
	sed -i "s/analytic_distribution\/1/analytic_distribution\/$one/" $two.xml;
	sed -i "s/analytic_distribution\/2/analytic_distribution\/$two/" $two.xml;
	sed -i "s/analytic_distribution\/3/analytic_distribution\/$three/" $two.xml;
	sed -i "s/analytic_distribution\/4/analytic_distribution\/$four/" $two.xml;

	sed -i "s/cost_center_distribution_line\/1/cost_center_distribution_line\/$one/" $two.xml;
	sed -i "s/cost_center_distribution_line\/2/cost_center_distribution_line\/$two/" $two.xml;
	sed -i "s/cost_center_distribution_line\/3/cost_center_distribution_line\/$three/" $two.xml;
	sed -i "s/cost_center_distribution_line\/4/cost_center_distribution_line\/$four/" $two.xml;


	# 3.xml
	sed -i "s/analytic_distribution\/2/analytic_distribution\/$two/" $three.xml;
	sed -i "s/analytic_distribution\/3/analytic_distribution\/$three/" $three.xml;
	sed -i "s/analytic_distribution\/4/analytic_distribution\/$four/" $three.xml;

	sed -i "s/funding_pool_distribution_line\/1/funding_pool_distribution_line\/$one/" $three.xml;
	sed -i "s/funding_pool_distribution_line\/2/funding_pool_distribution_line\/$two/" $three.xml;
	sed -i "s/funding_pool_distribution_line\/3/funding_pool_distribution_line\/$three/" $three.xml;


	# 4.xml
	sed -i "s/account_move_line\/1/account_move_line\/$one/" $four.xml;

	# three and four not to mess up the first round
	sed -i "s/account_analytic_line\/5/account_analytic_line\/$three/" $four.xml;
	sed -i "s/account_analytic_line\/6/account_analytic_line\/$four/" $four.xml;

done



