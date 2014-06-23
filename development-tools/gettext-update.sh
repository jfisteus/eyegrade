#!/bin/bash

srcfiles="eyegrade/eyegrade.py eyegrade/qtgui/gui.py eyegrade/qtgui/export.py"

languages=$*
if [ "x$languages" == "x" ]
then
    languages="es gl ca"
fi

for lang in $languages
do
    echo "Language: $lang"
    xgettext -o eyegrade/data/locale/$lang/LC_MESSAGES/eyegrade.po.new $srcfiles
    msgmerge -U eyegrade/data/locale/$lang/LC_MESSAGES/eyegrade.po \
                eyegrade/data/locale/$lang/LC_MESSAGES/eyegrade.po.new
done
