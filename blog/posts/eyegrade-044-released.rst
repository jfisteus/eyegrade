.. title: Eyegrade 0.4.4 released
.. slug: eyegrade-044-released
.. date: 2014-11-28 17:46:54+00:00
.. tags: eyegrade, release, bugfix
.. link:
.. description:
.. type: text

I've just released Eyegrade 0.4.4.
This version fixes a bug introduced by
`the bugfix of version 0.4.3 <eyegrade-043-released.html>`_.
Version 0.4.3 solved the problem for
the older versions of Python,
but inadvertently introduced exactly the same problem
for the newer versions,
which were previously unaffected.
I've reverted the erroneous fix
and solved the problem
`in a better way <https://github.com/jfisteus/eyegrade/commit/e03da3762e748913db89e6470b3fe85b02f367df>`_.
This new version should be able to export grades
in any 2.6 and 2.7 version of Python,
both Windows and Linux.

This is the only change with respect to version 0.4.3.

As always, if you have installed Eyegrade through *git*,
you can easily update the program by executing the command
*git pull* from inside the directory in which Eyegrade is installed.

