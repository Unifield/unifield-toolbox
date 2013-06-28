#!/bin/bash

NB_PRODUCTS=7000
DATA_TARGET=data_target

rm -rf $DATA_TARGET
mkdir $DATA_TARGET

for (( i=1; i<=$NB_PRODUCTS; i++ ))
do
        sed s/@@LOOPI@@/$i/g 1.xml > $DATA_TARGET/$i.xml
done
