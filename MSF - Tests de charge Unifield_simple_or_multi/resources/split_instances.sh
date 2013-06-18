#!/bin/bash

OCFILE=operationCenters.csv
COORDOFILE=coordinations.csv
MISSIONFILE=missions.csv
PROJFILE=projects.csv

for oc in {"OCA","OCB","OCG","OCP","OCBA"}; do
	grep "$oc," $OCFILE > $OCFILE.$oc
	grep "$oc"_ $COORDOFILE > $COORDOFILE.$oc
	grep "$oc"_ $MISSIONFILE > $MISSIONFILE.$oc
	grep "$oc"_ $PROJFILE > $PROJFILE.$oc
done
