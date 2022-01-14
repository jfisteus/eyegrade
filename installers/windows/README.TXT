Building the EXE files with PyInstaller and the installer with NSIS
---------------------------------------------------------------------

You need to install pyinstaller through pip, and NSIS version 2.X.

Use a 32-bit version of python 3.x for maximum portability of the produced files.

Create the files from the main eyegrade directory with:

python installers\windows\build_pyinstaller.py

The output installer is created in the dist directory your main
eyegrade directory.



--- Older notes (they don't apply now) ---

Building the installer with briefcase
---------------------------------------

1.- Install briefcase through pip (tested with briefcase==0.2.8).

https://github.com/pybee/briefcase
https://briefcase.readthedocs.io/

2.- Install the WiX toolset (tested with 3.11.1):

http://wixtoolset.org/
https://github.com/wixtoolset/wix3

3.- Run from the main eyegrade directory:

python installers\windows\build_briefcase_wix.py

The installer will appear in the windows subdirectory that will be created.

Users might also need to install Visual C++ Redistributable
for Visual Studio 2015 (up to Python 3.7):

https://www.microsoft.com/en-us/download/details.aspx?id=48145


Signing the installer
-----------------------

Assuming you have a code signing key in a file named EyegradeKey.pfx,
sign the installer with the command:

signtool sign /fd SHA512 /a /f EyegradeKey.pfx /p key-password /tr http://tsa.safecreative.org eyegrade-setup-XXX.exe
