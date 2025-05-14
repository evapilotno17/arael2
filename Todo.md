# Arael2

This is meant to be an evolution of my initial arael undertaking, transforming my initital keylogger into a cross platform application.


Current status:
 - I'm trying to get it working on linux
 - The core linux keylogger is at /linux
 - compile command: gcc -O2 -std=c11 -DDEBUG -lsqlite3 keylog.c -o keylog.exe
 - run command: sudo ./keylog.exe /dev/input/event3 

What I want to do:
 - fix ./keylogger/keylog.py cli - it doesn't work as of now
 - develop tooling around this thing after getting the basic cli working
 - the core linux process is indeed working, but the cli seems broken