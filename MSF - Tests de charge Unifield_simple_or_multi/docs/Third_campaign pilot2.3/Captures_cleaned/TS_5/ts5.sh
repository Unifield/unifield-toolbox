#!/bin/bash

# Number of POs per instance
NBPO=4

rm -rf data_target message_target
mkdir data_target message_target

for (( po=1; po<=$NBPO; po++ ))
do
        file_one=$((($po-1)*3+1))
        file_two=$(($file_one+1))
        file_three=$(($file_one+2))
        cp data/1.xml data_target/$file_one.xml
        cp data/2.xml data_target/$file_two.xml
        cp data/3.xml data_target/$file_three.xml

        sed -i s/@@ID@@/$po/g data_target/$file_one.xml
        sed -i s/@@ID@@/$po/g data_target/$file_two.xml
        sed -i s/@@ID@@/$po/g data_target/$file_three.xml

        sed s/@@ID@@/$po/g message/1.xml > message_target/$po.xml
done
