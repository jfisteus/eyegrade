#!/bin/sh

if [ ! $# -eq 1 ]
then
    echo "Image file name is expected as a command-line parameter" >&2
else
    curl --data-binary @$1 -H "Content-Type: application/x-eyegrade-bitmap"  http://localhost:8080/process
fi
