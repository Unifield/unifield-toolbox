#!/bin/bash

REGLINES=22

rm -rf data_target
mkdir data_target

for (( line=1; line<=$REGLINES; line++ ))
do
        file_one=$((($line-1)*10+1))
        file_two=$(($file_one+1))
        file_three=$(($file_one+2))
        file_four=$(($file_one+3))
        file_five=$(($file_one+4))
        file_six=$(($file_one+5))
        file_seven=$(($file_one+6))
        file_eight=$(($file_one+7))	
        file_nine=$(($file_one+8))
        file_ten=$(($file_one+9))


        cp 1.xml data_target/$file_one.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_one.xml
	sed -i s/@@VALTHREE@@/$file_three/g data_target/$file_one.xml

        cp 2.xml data_target/$file_two.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_two.xml
	sed -i s/@@VALTHREE@@/$file_three/g data_target/$file_two.xml

        cp 3.xml data_target/$file_three.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_three.xml
	sed -i s/@@VALTHREE@@/$file_three/g data_target/$file_three.xml

        cp 4.xml data_target/$file_four.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_four.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_four.xml


        cp 5.xml data_target/$file_five.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_five.xml

        cp 6.xml data_target/$file_six.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_six.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_six.xml
	sed -i s/@@VALTHREE@@/$file_three/g data_target/$file_six.xml

        cp 7.xml data_target/$file_seven.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_seven.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_seven.xml

        cp 8.xml data_target/$file_eight.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_eight.xml
	sed -i s/@@VALTWO@@/$file_two/g data_target/$file_eight.xml

        cp 9.xml data_target/$file_nine.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_nine.xml

        cp 10.xml data_target/$file_ten.xml
	sed -i s/@@VALONE@@/$file_one/g data_target/$file_ten.xml
	sed -i s/@@VALTHREE@@/$file_three/g data_target/$file_ten.xml

done


