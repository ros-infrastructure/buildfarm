#!/usr/bin/env bash

# test subprocess_reaper.py

# launch subprocess_reaper.py with my PID
sudo python ../scripts/subprocess_reaper.py $$ &

# new child process
sleep 550 & 
# new shell with child process
sudo sh -c "sleep 551" &
# nested shells with a child process
sudo sh -c "sh -c \"sleep 552\"" &

# note that if a process is forked, its parent will be PID 1
# and subprocess_reaper.py won't find it:
# sh -c "sleep 500 &"

# need to sleep a bit
# else subprocess_reaper.py is not yet started before this script has ended
sleep 2
