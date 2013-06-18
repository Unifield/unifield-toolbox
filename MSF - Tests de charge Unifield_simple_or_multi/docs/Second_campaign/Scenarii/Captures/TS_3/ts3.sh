#!/bin/bash

RULE_ID_1=7
RULE_ID_2=9

rm -rf target
mkdir target

i=1
more data.csv | while read line;
do

	cursymb=$(echo $line | awk -F "," '{gsub(/["]+/,"",$1); print $1}')
	curname=$(echo $line | awk -F "," '{gsub(/["]+/,"",$2); print $2}')
	curid=$(echo $line | awk -F "," '{gsub(/["]+/,"",$3); print $3}')

	file_nb=$((($i-1)*2+1))
	file_two=$(($file_nb+1))

#	echo $cursymb
#	echo $curname
#	echo $curid


	sed s/@@CURSYMB@@/$cursymb/g 1.xml > target/$file_nb.xml
	sed -i "s/@@CURNAME@@/$curname/g" target/$file_nb.xml
	sed -i s/@@CURID@@/$curid/g target/$file_nb.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_1/g target/$file_nb.xml

	sed s/@@CURSYMB@@/$cursymb/g 2.xml > target/$file_two.xml
	sed -i s/@@CURID@@/$curid/g target/$file_two.xml
	sed -i s/@@VALUE@@/$(($i+44))/g target/$file_two.xml
	sed -i s/@@RULE_ID@@/$RULE_ID_2/g target/$file_two.xml
	let i++
done
