#! /bin/bash

f='/tmp/'$$
ps auwwx | grep '/home/.*/.*server' | grep python | awk '{print $12}' | cut -f3 -d/ > $f
echo $f
