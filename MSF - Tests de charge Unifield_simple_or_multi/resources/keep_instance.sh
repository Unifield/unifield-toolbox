#!/bin/bash

OC_TO_KEEP=OCB

OCFILE=operationCenters.csv
COORDOFILE=coordinations.csv
MISSIONFILE=missions.csv
PROJFILE=projects.csv

mkdir backup_ocfiles
mv $OCFILE* $COORDOFILE* $MISSIONFILE* $PROJFILE* backup_ocfiles

for f in {$OCFILE,$COORDOFILE,$MISSIONFILE,$PROJFILE}; do
	mv backup_ocfiles/$f.$OC_TO_KEEP $f
done
