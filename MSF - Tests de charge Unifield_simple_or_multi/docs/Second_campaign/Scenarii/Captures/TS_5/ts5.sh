#!/bin/bash

# Number of POs per instance
NBPO=4
RULE_ID_1=21
RULE_ID_2=22
RULE_ID_3=23

rm -rf data_target message_target
mkdir data_target message_target

for (( po=1; po<=$NBPO; po++ ))
do
	file_nb=$((($po-1)*3+1))
	file_two=$(($file_nb+1))
	file_three=$(($file_nb+2))
	cp data/1.xml data_target/$file_nb.xml
	cp data/2.xml data_target/$file_two.xml
	cp data/3.xml data_target/$file_three.xml

	sed -i s/@@ID@@/$po/g data_target/$file_nb.xml
	sed -i s/@@ID@@/$po/g data_target/$file_two.xml
	sed -i s/@@ID@@/$po/g data_target/$file_three.xml

	sed -i s/@@RULE_ID@@/$RULE_ID_1/g data_target/$file_nb.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_2/g data_target/$file_two.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_3/g data_target/$file_three.xml


	sed s/@@VALUE@@/$po/g message/1.xml > message_target/$po.xml
	sed -i s/OCA_Coordo1/#parent_instance#/g message_target/$po.xml
done


