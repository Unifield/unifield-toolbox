#!/bin/bash

original_path=`pwd`

if [ "$1" = "-h" ]; then
    echo "KEY_FETCH=<the key> ./fetch.sh"
    exit 1
fi

set -e

echo "Clean up data"
[[ -e .tmp ]] && rm -rf .tmp
mkdir .tmp
[[ -e testfield_data ]] && rm -rf testfield_data
mkdir -p testfield_data/testfield
rm -rf instances testfield.zip

KEY_FETCH=${KEY_FETCH-tSrHBNFemfKIVuY}

echo "Download the zip file"
out=`date +test_%Y%m%d-%H%M.zip`
wget -q -O $out https://cloud.msf.org/index.php/s/${KEY_FETCH}/download
DIRNAME=$(unzip -qql $out | head -n1 | tr -s ' ' | cut -d' ' -f5-)

mv $out .tmp/tests.zip
cd .tmp

echo "Unzip"
unzip tests.zip testfield/instances/*

echo "Get meta_feature and files from testing"
cp -R $DIRNAME/instances ../testfield_data/testfield/
cp -R /home/testing/testfield/meta_features ../testfield_data/testfield/
cp -R /home/testing/testfield/files ../testfield_data/testfield/
cd ..

rm -rf .tmp

cd testfield_data
echo "Rebuild a new zip file"
zip -r testfield.zip testfield
mv testfield.zip $original_path
cd $original_path
rm -rf testfield_data
