#!/bin/bash

NB_REGISTERS=6
RULE_ID_1=27
RULE_ID_2=28
RULE_ID_3=31
RULE_ID_4=34


rm -rf data_target
mkdir data_target

cp *.xml data_target/

for (( reg=1; reg<=$NB_REGISTERS; reg++ ))
do
	file_nb=$((($reg-1)*4+1))
	file_two=$(($file_nb+1))
	file_three=$(($file_nb+2))
	file_four=$(($file_nb+3))

	sed s/@@ID@@/$reg/g 1.xml > data_target/$file_nb.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_1/g data_target/$file_nb.xml

	sed s/@@ID@@/$reg/g 2.xml > data_target/$file_two.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_2/g data_target/$file_two.xml

	sed s/@@ID@@/$reg/g 3.xml > data_target/$file_three.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_3/g data_target/$file_three.xml

	sed s/@@ID@@/$reg/g 4.xml > data_target/$file_four.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_4/g data_target/$file_four.xml
done

sed -i s/23adf5823ecb11e2869ed4ae52a5e4b6/#uuid#/g data_target/*.xml
sed -i s/OCA_Coordo1_Project1/#instance_name#/g data_target/*.xml
