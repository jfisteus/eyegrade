This directory contains the files needed to build a Windows installer.

You need to install pywin32 from its website, pyinstaller through pip,
and NSIS version 2.X.

Use a 32-bit version of python 2.7 for maximum portability of the produced files.

Create the files from the main eyegrade directory with:

python installers\windows\build.py

The output installer is created in the dist directory your main eyegrade directory.
