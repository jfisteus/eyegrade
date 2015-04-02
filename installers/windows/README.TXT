This directory contains the files needed to build a single Windows executable
file (install pywin32 from its website and then pyinstaller through pip)
and a Windows installer (install NSIS version 2.X).

Use a 32-bit version of python 2.7 for maximum portability of the produced files.

Eyegrade must be at C:\Eyegrade. From there, run:

cd C:\Eyegrade
C:\python27_32\Scripts\pyi-build.exe installers\windows\eyegrade.spec
"C:\Program Files (x86)\NSIS\makensis.exe" installers\windows\eyegrade.nsi
