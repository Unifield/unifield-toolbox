#! /bin/bash

ps auwwx | grep '/home/.*/.*server' | grep python | awk '{print $12}' | cut -f3 -d/
