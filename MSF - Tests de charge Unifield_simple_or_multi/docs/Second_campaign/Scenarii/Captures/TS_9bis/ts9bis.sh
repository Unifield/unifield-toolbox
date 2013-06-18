#!/bin/bash

REGLINES=22
RULE_ID_1=21
RULE_ID_2=23
RULE_ID_3=32
RULE_ID_4=36
RULE_ID_5=38
RULE_ID_6=40
RULE_ID_7=43
RULE_ID_8=45

rm -rf data_target
mkdir data_target

sed -i s/23adf5823ecb11e2869ed4ae52a5e4b6/#uuid#/g *.xml

for (( line=1; line<=$REGLINES; line++ ))
do
	file_nb=$((($line-1)*8+1))
	file_two=$(($file_nb+1))
	file_three=$(($file_nb+2))
	file_four=$(($file_nb+3))
	file_five=$(($file_nb+4))
	file_six=$(($file_nb+5))
	file_seven=$(($file_nb+6))
	file_eight=$(($file_nb+7))

	cp 1.xml data_target/$file_nb.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_1/g data_target/$file_nb.xml

	cp 2.xml data_target/$file_two.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_2/g data_target/$file_two.xml

	sed s/@@ACC_BANK_STA_ID@@/$file_nb/g 3.xml > data_target/$file_three.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_3/g data_target/$file_three.xml

	sed s/@@ACC_MOV_REC_ID@@/$file_nb/g 4.xml > data_target/$file_four.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_4/g data_target/$file_four.xml
	
	sed s/@@AC_MOVE_ID1@@/$file_nb/g 5.xml > data_target/$file_five.xml
	sed -i s/@@AC_MOVE_ID2@@/$file_two/g data_target/$file_five.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_5/g data_target/$file_five.xml
	
	sed s/@@AC_MOVE_ID2@@/$file_two/g 6.xml > data_target/$file_six.xml
	sed -i s/@@ACC_MOV_REC_ID1@@/$file_nb/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_LINE_ID3@@/$file_three/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_ID2@@/$file_two/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_LINE_ID4@@/$file_four/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_LINE_ID1@@/$file_nb/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_ID1@@/$file_nb/g data_target/$file_six.xml
	sed -i s/@@ACC_MOV_LINE_ID2@@/$file_two/g data_target/$file_six.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_6/g data_target/$file_six.xml

	sed s/@@ACC_MOV_ID2@@/$file_two/g 7.xml > data_target/$file_seven.xml
	sed -i s/@@ACC_MOV_ID1@@/$file_nb/g data_target/$file_seven.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_7/g data_target/$file_seven.xml
	
	sed s/@@ACC_MOV_LINE_ID1@@/$file_nb/g 8.xml > data_target/$file_eight.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_8/g data_target/$file_eight.xml
		
done
sed -i s/OCA_Coordo1_Project1/#instance_name#/g data_target/*.xml
