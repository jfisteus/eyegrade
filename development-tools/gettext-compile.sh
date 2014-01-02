#!/bin/bash

languages=$*
if [ "x$languages" == "x" ]
then
    languages="es gl ca"
fi

for lang in $languages
do
    echo "Language: $lang"
    msgfmt -o eyegrade/data/locale/$lang/LC_MESSAGES/eyegrade.mo \
              eyegrade/data/locale/$lang/LC_MESSAGES/eyegrade.po
done
