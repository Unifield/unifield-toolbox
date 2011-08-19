#! /bin/bash

RUNNING_PATH=$1

if [ -z "$RUNNING_PATH" ]; then
    RUNNING_PATH=/running
fi
kill `ps aux | grep $RUNNING_PATH  | awk '{print $2}'`
