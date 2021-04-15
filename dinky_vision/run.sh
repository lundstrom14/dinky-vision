#!/bin/bash

for pid in $(ps -ef | grep "python" | grep -v "grep" |awk '{print $2}'); 
    do kill -9 $pid; 
done;

cd /home/pi/dinky-vision/dinky_vision
uvicorn --host 0.0.0.0 main:app --reload --port 8080
