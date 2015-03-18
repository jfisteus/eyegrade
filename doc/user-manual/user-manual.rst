Eyegrade User Manual
====================

:Author: Jesús Arias Fisteus

.. contents::
.. section-numbering::

This user manual refers to Eyegrade 0.5 and later versions. For the
0.3 and 0.4 series see `this other user manual <../user-manual-0.3/>`_.

Installing Eyegrade
-------------------

Eyegrade depends on the following free-software projects:

- Python_: the run-time environment and standard library for the
  execution Python programs. Eyegrade is known to work with Python
  2.6.

- Opencv_: a widely used computer-vision library. Version 2.0 or later
  is needed. Not only the OpenCV library, but also the python bindings
  distributed with it are needed.

- Qt_: a multi-platform library for developing graphical user interfaces.

- PyQt_: Python bindings to Qt.

- Tre_: a library for regular expressions. Install version 0.8.0 or
  later.  Both the library and python bindings are needed.

.. _Python: http://www.python.org/
.. _Opencv: http://opencv.willowgarage.com/wiki/
.. _Qt: http://qt.digia.com/
.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/
.. _Tre: http://laurikari.net/tre/


Upgrading from Eyegrade 0.2.x, 0.3.x and 0.4.x to Eyegrade 0.5
................................................................

In order to upgrade from Eyegrade 0.2.x, 0.3.x and 0.4.x to Eyegrade 0.5,
follow the instructions at `Updating Eyegrade`_.

Be aware that Eyegrade 0.5 uses an updated session database schema.
Although Eyegrade 0.5 is able to work with sessions created
by the previous versions of Eyegrade,
those previous versions don't work
with sessions created by Eyegrade 0.5.

The main changes of the most recent versions are described in the following
blog posts:

- `Eyegrade 0.5 released
  <http://www.eyegrade.org/blog/posts/eyegrade-05-released.html>`_

- `Eyegrade 0.4 released
  <http://www.eyegrade.org/blog/posts/eyegrade-04-released.html>`_

- `Eyegrade 0.3 released
  <http://www.eyegrade.org/blog/posts/eyegrade-03-released.html>`_


Installation on GNU/Linux
.........................

If your Linux distribution is not very old, it should provide most of
the needed software packages. Specific instructions for Debian
GNU/Linux and Ubuntu are provided below.


Installation on Debian and Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Almost all the required software packages are already available in
recent versions of `Debian GNU/Linux <http://www.debian.org/>`_ and
`Ubuntu <http://www.ubuntu.com/>`_. The only exception are the Python
bindings for Tre, which have to be installed manually.

Using your favorite package manager (``apt-get``, ``aptitude``,
``synaptic``, etc.), install the following packages:

- ``python`` (check that the version is 2.7.)

- ``python-dev``

- ``python-qt4``

- ``python-opencv``

- ``python-numpy``

- ``libtre5``

- ``libtre-dev``

- ``git``

For example, with ``apt-get`` you would run from a command line terminal::

  sudo apt-get install python python-dev python-qt4 python-opencv python-numpy libtre5 libtre-dev git

Then, you have to install the Python bindings for Tre.  In order to do
that, download, compile and install the Python bindings. You can do
that from a command line terminal::

  wget http://laurikari.net/tre/tre-0.8.0.tar.gz
  tar xzvf tre-0.8.0.tar.gz
  cd tre-0.8.0/python/
  python setup.py build
  sudo python setup.py install

Now, you only need to download Eyegrade using the git source code
revision system::

  cd $DIR
  git clone -b master git://github.com/jfisteus/eyegrade.git

Note: replace $DIR above with the directory in which you
want Eyegrade to be installed.

Finally, add the ``$DIR/eyegrade`` directory to your ``PYTHONPATH`` and
check that Eyegrade works::

  export PYTHONPATH=$DIR/eyegrade
  python -m eyegrade.eyegrade

The export command works only in the current terminal. You can make it
permanent by adding it to your $HOME/.bashrc file (if you use the BASH
shell).

That's all! Eyegrade should now be installed. For further testing, go to
`Launching Eyegrade`_.


Installation on Microsoft Windows
.................................

You have to follow these steps, explained in the following sections,
in order to install Eyegrade in Windows:

1.- Install Python 2.6 (including Tre).

2.- Install PyQt.

3.- Install OpenCV 2.1.

4.- Install Eyegrade itself.


Installing Python
~~~~~~~~~~~~~~~~~

The easiest way to install Python, PyQt and Tre in Windows is
to download a ZIP file that contains all of them and extract it in
your file system.

1.- Download the ZIP file from:
`Python26.zip <https://www.dropbox.com/s/y7t4ov23h0gq2zj/Python26.zip>`_.

2.- Extract it somewhere in your file system (I recommend ``C:\``). A
directory named ``Python26`` will appear. Be aware that the full path
of the directory where you extract it *cannot contain* white-spaces.

3.- Add the main directory (``Python26``) of your Python installation
to your system PATH. For example, if you uncompressed Python at ``C:\``,
add ``C:\Python26`` to the system PATH variable.

You can test your installation by opening a new command line console
and launching the interactive Python interpreter in it::

    Python

If it does not start, you have probably not added it correctly to your
system PATH. Opening a new console is important because changes in the
system PATH apply only to newly-opened consoles.

Once in the Python interpreter, the following command should work::

    import tre

This command should not output any message. If it does, there is a
problem with the installation. If *tre* complains about a missing DLL,
the problem is probably that the installation directory of Python is
not in the system PATH.

If you already have a Python 2.6 installation and want to use it, you
must, on that installation of Python, download and install Tre
0.8.0. You will need Microsoft Visual Studio 2008 (the express version
is free and works) for this last step.


Installing PyQt4
~~~~~~~~~~~~~~~~

`Download PyQt
<http://www.riverbankcomputing.co.uk/software/pyqt/download>`_. Select
the Windows 32-bit installer for Python 2.6, event if you have a
64-bit version of Windows.  Alternatively, there is a copy of the file
you need at `PyQt-Py2.6-x86-gpl-4.9.6-1.exe
<https://www.dropbox.com/s/15xnbrj82n9tial/PyQt-Py2.6-x86-gpl-4.9.6-1.exe>`_.

Run the installer. From the optional software that the installer
suggests, you only need to select the *Qt runtime*.


Installing OpenCV
~~~~~~~~~~~~~~~~~

Download the EXE installer of OpenCV 2.1.0 for Windows platforms:
`OpenCV-2.1.0-win32-vs2008.exe
<http://sourceforge.net/projects/opencvlibrary/files/opencv-win/2.1/OpenCV-2.1.0-win32-vs2008.exe/download>`_. There
is a copy of the same file at `OpenCV21.exe
<https://www.dropbox.com/s/g1wxm3rcai2qojx/OpenCV21.exe>`_.

Execute the installer. Again, it is better to choose an installation
path which has no white-spaces in it. The installer will eventually
ask to put OpenCV in your system PATH. Answer *yes for this user* or
*yes for all the users*.

In order to test the installation, open a *new* command prompt window
(it must necessarily be a new window for the system path to be
updated). Run the python interpreter as explained in the previous
section and type in it::

    import cv

This command should not output any message. If it does, there is a
problem with the installation.


Installing Eyegrade
~~~~~~~~~~~~~~~~~~~

By now, the recommended way to install Eyegrade is through the `Git
version control system <http://git-scm.com/>`_. This way it will be
easier to update Eyegrade in the future, when new versions are
released (see `Updating Eyegrade`_).

In order to install Eyegrade through Git, follow these steps:

1.- Download and install Git if you do not have it installed. The
installer and installation instructions are available at
<http://git-scm.com/>.

2.- Open a command line prompt (for example, a Git shell), enter the
directory you want Eyegrade to be installed (again, with no
white-spaces in it), and type::

    git clone -b master git://github.com/jfisteus/eyegrade.git

If you prefer not to install Git:

1.- Download the ZIP file `eyegrade.zip
<https://www.dropbox.com/s/yn7zpekcxc1exsu/eyegrade.zip>`_. Extract
it in your file system, in a directory with no white-spaces in its
path.

Once you have Eyegrade installed (either with or without Git), test
it. For example, if you have installed both Python and Eyegrade at
``C:\``::

    set PYTHONPATH=C:\eyegrade
    C:\Python26\python -m eyegrade.eyegrade

It should dump a help message.

**Tip:** it may be convenient adding C:\Python26 to your system path
permanently, and adding PYTHONPATH to the system-wide environment
variables. There are plenty of resources in the Web that explain how
to do this. For example,
`<http://www.windows7hacker.com/index.php/2010/05/how-to-addedit-environment-variables-in-windows-7/>`_.

Eyegrade should now be installed. Nevertheless, it might be a good
idea to reboot now the computer, in order to guarantee that the
installation of OpenCV and PyQt has completed. After that, go to
`Launching Eyegrade`_.


Installation on Mac OS X
........................

Sorry, Eyegrade is not currently supported on that platform. Volunteers
to support the platform are welcome.


Updating Eyegrade
.................

From time to time, a new release of Eyegrade may appear. If you
installed Eyegrade using Git, updating is simple. Open a command
prompt window, enter the Eyegrade installation directory and type::

    git pull

This should work on any platform (Linux, Windows, etc.)

If you didn't use Git to install Eyegrade, `download the new version
<https://www.dropbox.com/s/yn7zpekcxc1exsu/eyegrade.zip>`_,
uncompress it and replace your ``eyegrade`` directory by the one you
have uncompressed.


Grading Exams
-------------

The main purpose of Eyegrade is grading exams. In order to grade exams,
you will need:

- The Eyegrade software installed in your computer.
- The exam configuration file, which specifies the number of questions
  in the exam, solutions, etc. It is normally named with the
  `.eye`extension, such as `exam.eye`.
- A compatible webcam, with resolution of at least 640x480. It is
  better if it is able to focus (manually or automatically) at short
  distances.
- The list of students in your class, if you want Eyegrade to
  detect student IDs.
- The exams to grade.


Launching Eyegrade
..................

This section explains how to run Eyegrade. If it is the first time you
use Eyegrade, you can try it with the sample file ``exam-A.pdf``
located inside the directory ``doc/sample-files`` of your installation
of Eyegrade. Print it. You'll find also in that directory the file
``exam.eye`` that contains the metadata for this exam. You'll need to
load this file later from Eyegrade.

Eyegrade can be launched from command line::

    python -m eyegrade.eyegrade

This command opens the user interface of Eyegrade:

.. image:: images/main-window.png
   :alt: Eyegrade main window

Before beginning to grade exams, especially the first time you run
Eyegrade, you can check that Eyegrade can access your webcam. In the
*Tools* menu select the *Select camera* entry:

.. image:: images/camera-selection.png
   :alt: Select camera dialog

The next step is creating a grading session. Select *New session* in
the menu *Session*. A multi-step dialog will ask for some data Eyegrade
needs for creating the session:

- Directory and exam configuration: you need to enter here the
  following information:

  - Directory: select or create a directory for this session. The
    directory must be empty.

  - Exam configuration file: select the ``.eye`` file associated to
    this exam. If you printed the sample exam distributed with
    Eyegrade, use the ``exam.eye`` file from the same directory.

- Student list files: select zero, one or more files that contain the
  list of students in the class. The files should be plain text and
  contain a line per student. See `Student list files`_ for more
  information on the format of these files.

- Scores for correct and incorrect answers: this step is optional. If
  you provide the scores awarded to correct answers (and optionally
  deducted from incorrect answers), Eyegrade will show the marks of
  each exam.

After you finish with this dialog, Eyegrade opens the session. It
shows the image from the webcam and starts scanning for the
exam. Point the camera to the exam until the image is locked. At this
point, Eyegrade should show the answers it has detected. Read the
following sections for further instructions.


Student list files
...................

The accuracy in the detection of the student identity
improves dramatically when you supply
the list of student ids of the class.
The student list can be provided as one or more plain text files
with one student per line.
Each line may have several tab-separated columns.
Eyegrade accepts lines with the following formats:

- Student id (1 column):
  just one column with the id number of the student::

    100000333
    100777777
    100999997

- Student id and full name (2 columns):
  the first column contains the student id number
  and the second one their full name.
  You are free to chose the last name - comma - first name
  order or the first name - last name order::

    100000333	Baggins, Frodo
    100777777	Bunny, Bugs
    100999997	Bux, Bastian

- Student id, full name and e-mail (3 columns):
  the first column contains the student id number,
  the second one their full name
  and the third one their e-mail address::

    100000333	Baggins, Frodo	frodo@shire.com
    100777777	Bunny, Bugs	bugs@cartoon.com
    100999997	Bux, Bastian	bux@fantastica.com

- Student id, first name and last name (3 columns):
  the first column contains the student id number,
  the second one their first (given) name
  and the third one their last (family) name::

    100000333	Frodo	Baggins
    100777777	Bugs	Bunny
    100999997	Bastian	Bux

- Student id, first name, last name and e-mail (4 columns):
  the first column contains the student id number,
  the second one their first (given) name,
  the third one their last (family) name
  and the fourth one their e-mail address::

    100000333	Frodo	Baggins	frodo@shire.com
    100777777	Bugs	Bunny	bugs@cartoon.com
    100999997	Bastian	Bux	bux@fantastica.com

The student id number must be composed just by digits.
The student name may contain non-ASCII characters.
In that case the file must be UTF-8 encoded.



The session directory
.....................

A grading session in Eyegrade represents the grading of a specific
exam for a group of students. For example, you would grade the exams
for the final exam of all your students in the subject *Computer
Networks* in just one session. Other exams, such as the re-sit exam of
the same subject, should go in separate sessions.

Grading sessions are associated to a directory in your computer. You
select or create this directory when you create a new session.
Eyegrade stores there all the data belonging to the grading session
(configuration file, student lists, grades, images of the already
graded exams, etc.)

You can open again later an existing session with the *Open session*
option of the *Session* menu. In the file selection dialog that
appears, select the ``session.eyedb`` file inside the directory of the
session you want to open. When you open the session, you can continue
grading new exams that belong to that session.



Scores
.......

Eyegrade can compute the scores of the exams.
When you create a new session, you can select
in the last page of the wizard one
of the following three options:

- No scores: Eyegrade shows the number of correct and incorrect questions,
  but does not compute scores.

- Same score for all the questions: all the questions
  are awarded the same score.
  You must specify the score for each correct question.
  Optionally, if you want incorrect or blank questions
  to have a penalty in the score,
  you can also specify a (negative) score for incorrect
  questions and for blank questions.

- Base score plus per-question weight:
  in this mode, not all the questions have the same score.
  You must define a *base score*
  (a reference score for correct, incorrect and blank questions)
  and, for each question, a relative *weight*.
  The final score for a question is computed as the multiplication
  of its weight and the base score.
  This mode can also be used for voiding questions:
  when you assign a weight of 0 to a question,
  that question is not graded.


Same score for all the questions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you select this option,
all the questions count the same in the grade of the exam.
Eyegrade counts the number of correct, incorrect and blank answers,
and multiplies each one by the score assigned
to each of those types of answers.

For example, suppose an exam with 10 questions,
in which correct answers add 1 point to the score
and incorrect answers subtract 1/3 points (one third of a point).
A student having 7 correct and 3 incorrect answers
will get 6 points (7 * 1 - 3 * 1/3).

You specify those scores in the last step of the session creation wizard:

.. image:: images/same-score-dialog.png
   :alt: Dialog for specifying the same score for all the questions

Giving a positive score for correct answers is mandatory in this mode.
The score for incorrect and blank answers is optional,
and defaults to 0 when you don't enter it.

Eyegrade can automatically compute the appropriate scores for you
if you specify the total score that a perfect exam would achieve.
In order to do that, press the *Compute default scores* button,
and the following dialog appears:

.. image:: images/compute-default-scores-dialog.png
   :alt: Dialog for computing the default scores

The dialog computes the score for correct answers
as the total score for a perfect exam divided by the number of questions.
If you select the *Penalize incorrect answers* option,
a score for incorrect answers is also computed
as the score for correct answers divided by
the number of choices of each question minus one.
This way, the expected score for an exam with random answers
(all the questions have the same probability of being marked by the student)
is zero.


Base score plus per-question weight
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you select this option for computing scores,
not all the questions are awarded the same score.
Important questions may get bigger scores than less important ones.
In order to do that, you define a base score
(e.g. 2 points for correct answers and -2/3 for incorrect ones)
and a relative *weight* for each question.
The *weight* of a question is a factor that multiplies the base score
in order to get the actual score of that question.
For example, for a question that you want to score double than the base score
(4 points for correct answers and -4/3 for incorrect ones)
you would set a weight of 2.
For a question you want to have exactly the base score,
you would set a weight of 1.
You can even decrease the score of a question with respect to he base score.
A weight of 1/2 would mean
1 point for correct answers and -1/3 for incorrect ones
in our example.

You need to edit the scores in the table at the center of the dialog:

.. figure:: images/weights-table.png
   :class: thumbnail
   :alt: View of the table for entering question weights

You can enter in each cell integer numbers (e.g. "2"),
fractions (e.g. "1/2")
or decimal numbers with fractional digits (e.g. "2.5").
If you have several exam models
(alternative orderings of the questions),
eyegrade will check that you enter the same weights
in all the models, possibly in a different order for each model:

.. figure:: images/error-different-weights.png
   :class: thumbnail
   :alt: Error message when the weights in some models are different

In addition, if your session configuration file
contains the permutations done to each model
(if you create the documents of your exams with eyegrade,
it will),
Eyegrade automatically updates the value in all the models
every time you change the weight of a question in one of them.
However, if the file does not contain the permutations,
you'll need to enter the weights for all the models yourself.

The *Compute default scores* button works as expected
in this mode also.
It takes into account the question weights you entered
in order to compute the base scores.
You should edit the question weights
*before* computing the default base scores.

Assigning weight 0 to a question voids it:

.. figure:: images/void-question-set-weight.png
   :class: thumbnail
   :alt: Set weight zero to void a question

The example above voids question 5 in model A,
which is also question 1 in model B, question 2 in model C
and question 3 in model D.
Void questions will be clearly displayed
in the capture of the exam,
and won't be considered either for the score
or the count of correct and incorrect questions:

.. figure:: images/void-question-capture.png
   :class: thumbnail
   :alt: Set weight zero to void a question


Application modes
.................

At a given instant, the application is in one of these modes:

- *No session mode*: no session is open. You can open an existing
  session or create a new session.

- *Session home mode*: a session is open. This is the entry point for
  starting grading and reviewing already graded exams.

- *Grading mode*: the application continually scans the input from the
  webcam, looking for a correct detection of an exam.

- *Review mode*: the application shows a still capture of an exam with
  the result of the grading, so that the user can review it and fix
  answers or the student id, if necessary.

- *Manual detection mode*: in the rare cases in which the system is
  not able to detect the geometry of the exam in the *grading mode*,
  you can enter this mode and mark the corners of the answer
  tables. Eyegrade will be able to detect the tables once you tell it
  where the corners are.

The application starts with no open session. Once you open or create a
session, it changes to the *session home mode*. From it, you can start
or continue grading (enter the *grading mode* with the *Start grading*
command) or review already graded exams (enter the *review mode* by
clicking on an exam at the right side of the main window).

When you are in the *grading mode*, the program is continually
analyzing the image of the webcam. When it detects an answer sheet
that it can read, it locks the capture and enters the *review
mode*. Once you confirm that capture (command *Continue to the next
exam*), Eyegrade automatically goes back to the *search mode* in order
to scan the next exam.

You can enter the *manual detection mode* by issuing the appropriate
command while in the other modes.

From the *grading mode* you can go back to the session home mode with
the *Stop grading* command. From any of the other modes, you can go
back to the *no session mode* with the *Close session* command in the
*Session* menu.


The grading mode
................

In the *grading mode*, you have to get the camera to point to the answer table
of the exam, including, if present, the id box above it and the small squares
at the bottom.

Eyegrade will continually scan the input of the webcam until the whole
exam is correctly detected. At that moment, Eyegrade will switch to the
*review mode*.

Sometimes, Eyegrade is able to detect the answer table but not the ID
table at the top of it. You can notice that because the detected
answers are temporary shown on top of the image. At this point, you
may try further until the ID box is also detected, or just use the
*Capture the current image* command of the *Grading* menu, which will
force the system to switch to the *review mode*, using the most recent
capture in which the answer table was detected. You will be able to
manually enter the missing student id in that mode.

In rare occasions, Eyegrade could fail event to detect the answer
table.  The *Manual detection* command of the *Grading menu* allows
you to help the system detect it.

These are the commands available in the *grading mode*, all of them at
the *Grading* menu:

- *Capture the current image* (shortcut 's'): forces the system to
  enter the *review mode* with the the most recent capture in which
  Eyegrade was able to detect the answer table. If there is no such
  capture, the system just uses the current capture.

- *Manual detection of answer tables* (shortcut 'm'): the system
  enters the *manual detection mode*, in which you can help the system
  detect the answer table by marking the corners of the answer
  tables. After that, the system will detect the answers of the
  student and automatically enter the *review mode*. See `The manual
  detection mode`_.


The review mode
...............

In the *review mode* you can review and, if necessary, fix the
information detected by Eyegrade in the current exam. You can do it on
both the answers given by the student to each question and the
student id. You enter the *review mode* in one of the following three
different situations:

- With the answers of the student and her id detected. This is the
  usual case.  Eyegrade was able to detect the whole exam, and you can
  review the information extracted from it.

- With the answers of the student, but without her id. This is the
  case when you use the *Capture the current image* command in the
  *grading mode* because Eyegrade detected the answer table in at least
  one capture, but not the student id box. In this case, you can
  review the answers given by the student and manually enter her id.

- With neither the answers of the student nor her id. This is the case
  when you use the *Capture the current image* command in the *grading
  mode* because Eyegrade was not able to detect anything from the
  exam. In this situation, you can switch to the *manual detection
  mode* to help the system to detect the answer tables, and manually
  enter the student id.

The user interface shows, in this mode, a capture of the exam augmented
with the detected information, as shown in the following image:

.. image:: images/review-mode-normal.png
   :alt: Eyegrade in the review mode

As you can see, the system shows:

- The answers of the student, with a green circle for correct answers
  and a red circle for the incorrect ones. When the student leaves a
  question unanswered, or provides a wrong answer for it, the correct
  answer for that question is marked with a small dot.

- The detected student id, at the bottom of the image, and his name
  (when the name is provided in the student list files).

- The total number of correct, incorrect and blank answers, at the
  bottom.  The total score of the exam is also shown if the session is
  configured with the scores for the answers.

- The model of the exam. The model is detected from the small black
  squares that are printed below the answer table.

- The sequence number of this exam. It is incremented with each graded
  exam.


In this mode, you can perform the following actions (see the *Grading*
menu):

- Modify the answers of the student, if there are mistakes in the
  automatically-detected answers, as explained in `Modifying student
  answers`_.

- Modify the student id, if the system did not recognize it or
  recognized a wrong id, as explained in `Modifying the
  student id`_.

- *Continue to the next exam* (shortcut 'Space-bar'): enters the
  *grading mode* in order to detect the next exam. **Tip:** before
  saving, it is better to remove the exam from the sight of the camera
  to avoid it from being captured again. You can even put the next
  exam under the camera before saving to speed up the process.

- *Discard capture* (shortcut 'Delete'): discards
  the current capture **without** saving it. It is useful, for
  example, when the capture is not good enough, or when you discover
  that the same exam has already been graded before.

- *Manual detection of answer tables* (shortcut 'm'): the system
  enters the *manual detection mode*, in which you can help the system
  detect the answer table by marking the corners of the answer
  tables. After that, the system will detect the answers of the
  student and automatically enter again the *review mode*. This
  command is allowed only when the system failed to recognize the
  geometry of the answer tables. See `The manual detection mode`_.


Modifying student answers
~~~~~~~~~~~~~~~~~~~~~~~~~

The optical recognition system of Eyegrade may fail sometimes, due to
its own limitations, or students filling their exams in messy ways.
Sometimes, Eyegrade shows a cell in the answer table as marked when it
is not, or a cell is not marked when it actually is. In addition, if
Eyegrade thinks that two cells of the same question are marked, it
will leave that question as blank.

You are able to fix those mistakes at the *review mode*. Click on a
cell of the answer table to change an answer of the student that was
not correctly detected by Eyegrade: when the student marked a given
cell, but the system detected the question as blank, or simply showed
other answer of that question as marked, just click on the cell the
student actually marked. When the student left a question blank but
the system did mark one of the cells as the answer, click on that cell
to clear it. In both cases, Eyegrade will compute the scores again and
immediately update the information on the screen.


Modifying the student id
~~~~~~~~~~~~~~~~~~~~~~~~

Normally, you should provide Eyegrade with the list of class, because
detection of student ids performs much better in that case. When
scanning the id in an exam, Eyegrade sorts ids of the students in
class according to the estimated probability of being the id in the
exam. The one with the most probability is shown.

In the *review mode*, you can enter the correct student id when
Eyegrade does not detect it, or detects a wrong one. When you select
the *Edit student id* command in the *Grading* menu, a dialog for
selecting the student id is shown:

.. image:: images/change-student-id.png
   :alt: Dialog for changing the student id

The dialog shows a drop-down menu with the students from the student
list sorted by their
probability (according to the OCR module) of being the student whose
id is in the exam. You just choose any student in the list.
In addition, you can filter students by writing part of their id number
or their name.

If the student is not in your list, you can also push the
*New student* button to create a new student.
It opens a dialog in which you can enter the data.
The only mandatory field is this dialog is the student id number:

.. image:: images/new-student-dialog.png
   :alt: Dialog for creating a new student


The manual detection mode
.........................

In some rare occasions, Eyegrade may not be able to detect the answer
tables. In those cases, you can enter the *manual detection mode* from
the *grading mode* (and also from the *review mode* if you entered that
mode using the *Capture the current image* command). When entering the
*manual detection mode*, the latest capture of the camera will be
shown.

In this mode, just click with the cursor in the four corners of each
answer table (a small circle will appear in every location you
click). The order in which you click on the corners does not
matter. After having done that, Eyegrade will infer the limits of each
cell, and based on them it will read the answers of the student and
the exam model. It will enter then the *review mode*.

The following two images show an example. In the first image, the user
has selected six corners (notice the small blue circles):

.. image:: images/manual-detection-mode.png
   :alt: Eyegrade in the review mode

After she selects the remaining two corners, the system detects the
answers and goes back to the *review mode*:

.. image:: images/manual-detection-mode-2.png
   :alt: Eyegrade in the review mode

Note, however, that the student id will not be detected when you use
this mode. When the system goes back to the *review mode*, set the id
as explained in `Modifying the student id`_.

At any point of the process, you can use the *Manual detection of
answer tables* command (shortcut 'm') to reset the selection of
corners and start again. If you think that the captured image is not
good enough, you can also use the *discard* command (shortcut
'Backspace') to go again to the *grading mode*.

**Tip:** in the *manual detection mode*, make sure that the captured
image shows all the answer tables as well as the exam model squares at
the bottom.


Processing Student Grades
-------------------------

The output produced by Eyegrade consists of:

- A file with the scores, named ``eyegrade-answers.csv``: it contains
  one line for each graded exam. Each line contains, among other
  things, the student id number, the number of correct and incorrect
  answers, and the answer to every question in the exam.  Student
  grades can be extracted from this file.  The file with the scores is
  stored in the session directory. Eyegrade updates its contents when
  you close the session. Remember to close it before using this file.

- One snapshot of each graded exam, in PNG format: snapshots can be
  used as an evidence to show students. They can be shown to students
  coming to your office to review the exam, or even emailed to every
  student. The default name for those images is the concatenation of
  the student id and exam sequence number, in order to facilitate the
  instructor to locate the snapshot for a specific student. The
  captures are stored in the session directory, inside its
  ``captures`` subdirectory. The captures are saved when the exam is
  captured, and updated every time you edit the exam.


The answers file
................

The file ``eyegrade-answers.csv`` produced by Eyegrade contains the
scores in CSV format (with tabulator instead of comma as a separator),
so that it can be easily imported from other programs such as
spreadsheets. This is an example of such a file::

    0	100999991	D	9	6	4.5	1/2/2/4/1/2/2/0/0/3/2/0/3/2/0/4/3/0/1/2
    1	100999997	C	15	1	15.0	2/4/4/3/1/0/1/2/1/1/0/1/0/4/3/0/1/4/3/4
    2	100800003	D	6	14	6.0	4/2/2/2/1/2/1/3/2/1/3/1/2/1/3/1/4/1/4/3
    3	100777777	A	7	13	7.0	3/2/3/2/3/3/2/4/3/1/3/1/4/1/4/2/2/3/4/2

The columns of this file represent:

1.- The exam sequence number (the same number the user interface shows
below the student id in the *review mode*).

2.- The student id (or '-1' if the student id is unknown).

3.- The exam model ('A', 'B', 'C', etc.)

4.- The number of correct answers.

5.- The number of incorrect answers.

6.- The score of the exam, if you configured the weight of correct and
incorrect answers for this session.

7.- The response of the student to each question in the exam, from the
first question in her model to the last. '0' means a blank
answer. '1', '2', etc. mean the first choice, second choice, etc., in
the order they were presented in her exam model.

Exams are in the same sequence they were graded. See `Exporting a
listing of scores`_ to know how to produce a listing of scores in the
order that best fits your needs.


Exporting a listing of scores
.............................

You will probably want to export your listing of scores in order to
import it into the grade-book, spreadsheet, etc. you use. Since
version 0.4 this can be done from the user interface (menu *Exams /
Export grades listing*).

First, the program shows a dialog like the following one:

.. image:: images/export-dialog.png
   :alt: Export dialog.

In this dialog you have to select:

- The format of the output file. The only option right now is a text
  file with one row per student and fields separated by tabulators.
  It is a usual data exchange format compatible with spreadsheet
  software (such as Microsoft Office and OpenOffice) and databases.
  Other formats might be added in future versions.

- The students to include in the listing: all the students in the
  student list or just the students whose exam has been graded in this
  session.

- The student groups to include in the listing: the grades for just a
  specific group of students or the grades for all the groups. This
  option is hidden if there is just one student group in the current
  session. Each student-list file you import in the session is treated
  as a distinct group. This option is useful when, for example, you
  teach the course in several separate classes. In that case you can
  export a separate grades listing for each class.

- How the grades are sorted: according to the order in the student
  list you imported or according to the order in which you graded the
  exams.

- Which fields to include in the listing: student id number, student
  name, grading sequence number, exam model letter, number of correct
  and incorrect answers, score and full list of answers. Only the
  fields you check are exported (as columns of the exported file). The
  order of these fields in the exported file is the same you see in
  the dialog (first the student id number, then her name, etc.)

Once you complete the selection of options and press the *OK* button,
a new dialog allows you to select the location and name with which the
file will be saved.  The `.csv` filename extension is recommended in
order to improve compatibility with external programs in which you
might want to open the grades. This extension is automatically set if
you type a name without extension.


Editing exams
-------------

Although you can use any software of your preference to typeset the
exams, Eyegrade provides a module for doing that
in combination with the LaTeX document preparation system.

The procedure consists of four steps,
which are described in the next sections:

#. Edit an XML file with the questions themselves.

#. Edit a LaTeX template for your exam
   with your institution's look and feel,
   instructions to students, etc.
   This template is reusable for other exams in the future.

#. Automatically generate the LaTeX source files
   from the XML file and the template.

#. Generate the PDF files from the LaTeX source files.

The example files used in the following explanations
are provided with Eyegrade
inside its `doc/sample-files` directory
(also `accessible at GitHub
<https://github.com/jfisteus/eyegrade/tree/development/doc/sample-files>`_).

This guide assumes that you have a LaTeX system installed.
If you don't have it in your system,
follow the instructions in `Installing the LaTeX system`_.


Editing the questions of the exam
..................................

You need to typeset your questions in an XML document.
You may use your favorite text editor for that.

At the beginning of the file
you should provide some basic data about the exam,
such as:
the name of the course/subject,
the name of the degree,
the name of the exam,
the date
and the duration of the exam.
You don't need to provide all those values,
just the ones you want printed in the exam.

Then, write the questions one by one.
For each question, you have to provide:

- The statement of the question.

- An optional picture to be displayed with the question.

- An optional block of code (for programming exams and the like)
  to be formatted with a fixed-width font
  and preserving spacing.

- The text of the correct choice.

- The text of the incorrect choices.

The XML markup must be like shown in the following example:

.. include:: ../sample-files/exam-questions.xml
   :literal:

You can insert LaTeX markup
within the text of the statement and the choices
if you need, for example,
to insert a math equation
or format a piece of text in italics, boldface
or typewriter font::

    <question>
      <text>
        Text in \emph{italics}, \textbf{boldface}
        and \texttt{typewriter} font style.
      </text>
      <choices>
        <correct>A LaTeX equation: $x^2 - 1$</correct>
        <incorrect>Nothing</incorrect>
      </choices>
    </question>


Inserting pictures
~~~~~~~~~~~~~~~~~~~

For inserting a picture in the statement of the question,
you use the `<figure>` tag.
Its file name must be provided within
the `<figure>` and `</figure>` tags.
It takes the following configuration attributes:

- `eye:width`: width of the picture relative to
  paragraph width
  (1.0 means the full width, 0.5 means half width, etc.)
  The picture will be scaled up or down accordingly.
  This attribute is mandatory.

- `eye:position`: position of the picture.
  Use `center` for placing it just below the statement of the question
  and above the choices.
  Use `right` for laying out the question in two columns:
  the statement of the question and the choices at the left
  and the picture at the right.
  The default value is `center`.

This is an example::

  <question>
    <text>
      Is the thing in the right a logo?
    </text>
    <figure eye:width="0.16" eye:position="right">sample-logo.eps</figure>
    <choices>
      <correct>Well, it tries to be a logo, to be honest.</correct>
      <incorrect>No, it's a tree.</incorrect>
      <incorrect>No, it's a perfect square.</incorrect>
      <incorrect>Who knows!</incorrect>
    </choices>
  </question>

Pictures can also be used inside a choice.
It that case, the choice can only contain the picture
and the `eye:position` attribute must not be used::

  <correct>
    <figure eye:width="0.2">sample-logo.eps</figure>
  </correct>


Inserting blocks of code
~~~~~~~~~~~~~~~~~~~~~~~~~

For inserting a block of code in the statement of the question,
you use the `<code>` tag.
The code itself is given within the `<code>` and `</code>` tags.
White space and end-of-line characters
are displayed as you provide them.
It takes the following configuration attributes:

- `eye:position`: position of the block of code.
  Use `center` for placing it just below the statement of the question
  and above the choices.
  Use `right` for laying out the question in two columns:
  the statement of the question and the choices at the left
  and the piece of code at the right.
  The default value is `center`.

- `eye:width`: only if you select the two column layout
  (position `right`),
  provide the width of the right column relative to
  paragraph width
  (0.5 means half width, etc.)
  Remember to leave enough place for the left side.
  This attribute is mandatory for the `right` position
  and forbidden for the `center` position.

This is an example::

    <code eye:position="right" eye:width="0.4">for letter in ['a', 'b', 'c']:
        print letter</code>

Blocks of code can also be used inside a choice.
It that case, the choice can only contain the block of code
and neither attribute can be used::

    <incorrect>
    <code>class MyClass:
        pass
    </code>
    </incorrect>


Editing the LaTeX template
...........................

In addition to the questions of the exam,
you'll need a LaTeX template.
It allows you to design the front page of the exam
and other aspects (fonts, margins, etc.)
This is an example:

.. include:: ../sample-files/template.tex
   :literal:

In the template, notice that there are some marks within {{ and }}
that are intended to be replaced by the script with data from the
exam:

- `{{declarations}}`: the script will put there some LaTeX declarations
  it needs.
- `{{subject}}`, `{{degree}}`: name of the subject and degree it
  belongs to. Taken from the XML file with the questions.
- `{{title}}`: the title of the exam. Taken from the XML file with the
  questions.
- `{{duration}}`: duration of the exam. Taken from the XML file with
  the questions.
- `{{model}}`: a letter representing the model of the exam. Each model
  has a different ordering for questions and choices within questions.
- `{{id-box(9,ID}}`: replaced by a box for students to fill in their IDs.
  The number of digits and the text to be put at the left of the box are
  specified within the parenthesis.
- `{{answer-table}}`: replaced by the table in which students mark out
  their answers.
- `{{questions}}`: replaced by the questions of the exam.

Note that a template is highly reusable for different exams and
subjects.


Creating the LaTeX source files
................................

Once the exam file and the template have been created, the script
`create_exam.py` parses them and generates the exam in LaTeX format::

  python -m eyegrade.create_exam -e exam-questions.xml -m 0AB template.tex -o exam

The previous command will create models 0, A and B of the exam with
names `exam-0.tex`, `exam-A.tex` and `exam-B.tex`. The exam model 0 is a
special exam in which questions are not reordered.
The correct answer is always the first choice in the model 0.
The model 0 is convenient while editing the questions,
but you must remember not to use it in the exam itself.

In addition, Eyegrade will automatically create the ``exam.eye`` file
needed to grade the exams, or update it if it already exists.

The script `create_exam.py` has other features, like creating just the
front page of the exam (no questions needed). They can be explored with
the command-line help of the program::

  python -m eyegrade.create_exam -h

The answer table can be enlarged or reduced with respect to its
default size, using the `-S` option and passing a scale factor
(between 0.1 and 1.0 to reduce it, or greater than 1.0 to enlarge it).
The following command enlarges the default size in a 50% (factor 1.5)::

  python -m eyegrade.create_exam -e exam-questions.xml -m A template.tex -o exam -S 1.5


Creating the PDF files
.......................

Once the `.tex` files have been created,
you have to use LaTeX to produce the PDF files.
For each file, run the following command::

  pdflatex exam-A.tex

If you have several exam models,
running that command for each one may be tedious.
On Linux systems you can produce all of them
with just a couple of commands::

  find -name "exam-*.tex" -exec pdflatex \{\} \;

That's it! Now you can print the PDF files of your exams.


Installing the LaTeX system
.............................

LaTeX is included in the repositories of the major Linux distributions.
In Debian and Ubuntu you can simply
install the package `texlive-latex-recommended`::

  sudo apt-get install texlive-latex-recommended

For MS Windows there are some LaTeX distributions
that provide a graphical installer,
such as `ProText <https://www.tug.org/protext/>`_:

#. Download the ProText installer
   (be aware that the size of the download is about 1.7 GB).

#. From the installer, choose to install MiKTex.
   When you are offered a minimal or full installation,
   the minimal one is enough.

#. You probably won't need to install TeXstudio,
   which is also offered by the installer.



Advanced features
-----------------

Webcam selection
................

If your computer has more than one camera (e.g. the internal camera of
the laptop and an external camera you use to grade the exams),
Eyegrade will select one of them by default. If the selected camera is
not the camera you want to use to grade the exams, use the ``-c
<camera-number>`` option when invoking Eyegrade. Cameras are numbered
0, 1, 2, 3, etc. Invoke Eyegrade with a different camera number until
the interface displays the one you want. For example, to select the
camera numbered as 2::

    python -m eyegrade.eyegrade exam.eye -c 2 -l student-list.csv

When the number is -1, eyegrade will automatically test different
camera numbers until it finds one that works. When you select a camera
number that does not exist or does not work, Eyegrade will also look
automatically for other camera that works.

You can configure Eyegrade to always use a specific camera number by
inserting the option ``camera-dev`` in the ``default`` section of
the configuration file::

    ## Sample configuration file. Save it as $HOME/.eyegrade.cfg
    [default]

    ## Default camera device to use (int); -1 for automatic selection.
    camera-dev: 1

Save it in your user account with name ``.eyegrade.cfg``. In Windows systems,
your account is at ``C:\Documents and Settings\<your_user_name>``.


Creating the exams in a word processor
........................................

The current prototype of Eyegrade require users to know LaTex in order
to personalize exam templates. This section explains an alternative
way to create exams compatible with Eyegrade in a word processor such
as Microsoft Word. If you create your own exams with a word processor,
you'll need also to edit the `.eye` file manually. See
`Manually editing the .eye file`_.

The objective is emulating the tables that Eyegrade creates so that
the program can read them. This is an example:

.. image:: images/example-table.png
   :alt: Example answer tables.

You can use as a template this `example MS Word document
<samples/sample-exam.doc>`_. It shows an answer table for 20 questions,
which you can edit in order to customize if for your
needs. Nevertheless, you should read the rest of this section if you
are planning to customize the answer table.

An *answer table* is a table in which rows represent the questions and
columns represent the choices. There can be more than one answer
table, but they have to be side by side (they cannot be placed one
above the other). The example above show two answer tables. A few
restrictions have to be taken into account:

- If there are more than one table, they must be horizontally
  aligned. That is, their top and bottom must be in the same line, and
  their rows must have exactly the same height (see the example above).

- All the rows should have the same height.

- In order to improve the detection process, the length of the
  vertical lines and the length of the horizontal lines should be more
  or less proportionate (e.g. one of them should not be more than a
  30% larger than the other). If there are more than one answer table,
  consider the added length of the horizontal lines of every
  table. The following image illustrates this. The red vertical line
  is not much smaller than the sum of the two horizontal lines.

.. image:: images/example-table-lengths.png
   :alt: Example answer tables.

- If an answer table has less rows than the others, it is better to
  keep the horizontal lines, as shown in the image below:

.. image:: images/example-table-2.png
   :alt: Example answer tables.

The boxes for the student ID number should be above the answer tables,
not too close but not too far away either (see the example below).
The width of the student ID table should be comparable to the sum of
the width of the answer tables (approximately no less than 2/3 of that
sum, and no more than 3/2). Student IDs with just a few digits (two,
three, four) can potentially be problematic for wide answer tables.

.. image:: images/example-table-id.png
   :alt: Example answer tables with student ID box.

At the bottom of the answer boxes there must be some black
squares. They encode the exam model (permutation). In addition, they
help the system to know whether the detection of the answer tables was
correct.

Imagine that there are two more rows at the end of each answer table,
with the same height as the other rows.  Squares will be either in the
one above or in the one below, and there must be a square per
column. Squares should be centered in those imaginary cells. The
position (above/below) of a square conveys the information read by
Eyegrade as binary information.

The exam model is encoded with three squares. Therefore, there can be
eight different models. The fourth square is a redundancy code for the
previous three squares. This 4-square pattern is repeated from left to
right as long as there are columns. The table to which a column
belongs is not taken into account. For example, if there are two
answer tables with three columns each, the fourth square (the
redundancy square) is placed at the first column of the second
table. The other two columns of the second answer table would contain
the same squares as the first two columns of the first table.

The following table show the 4-square pattern for each exam model, as
they should be placed from left to right:

+-------+---------------------------+
| Model |                           |
+-------+------+------+------+------+
|   A   | Down | Down | Down |  Up  |
+-------+------+------+------+------+
|   B   |  Up  | Down | Down | Down |
+-------+------+------+------+------+
|   C   | Down |  Up  | Down | Down |
+-------+------+------+------+------+
|   D   |  Up  |  Up  | Down |  Up  |
+-------+------+------+------+------+
|   E   | Down | Down |  Up  | Down |
+-------+------+------+------+------+
|   F   |  Up  | Down |  Up  |  Up  |
+-------+------+------+------+------+
|   G   | Down |  Up  |  Up  |  Up  |
+-------+------+------+------+------+
|   H   |  Up  |  Up  |  Up  | Down |
+-------+------+------+------+------+


Manually editing the .eye file
........................................

The files that store the configuration of an exam and the correct
answer for each question are stored with a `.eye` extension. An example
is shown below:

    .. include:: ../sample-files/exam.eye
       :literal:

The file is just plain text and can be edited with any text editor. It
has several sections: *exam*, *solutions* and *permutations*.

The fields of the *exam* section are:

- `dimensions`: here the number of answer tables and the number of
  columns and rows in each answer table are configured. For example,
  "4,6;4,6" means that there are two answer tables, both of them with
  geometry "4,6".  The "4" is the number of columns of the table. The
  "6" is the number of rows. Tables are specified from left to right
  (i.e. the first table geometry corresponds to the left-most table in
  the exam).

- `id-num-digits`: number of cells of the table for the student id
  number.  Putting a 0 here means that the id number needs not to be
  read.

- `correct-weight`: a number, such as 1.75, that represents the score
  assigned to a correct answer.

- `incorrect-weight`: a number that represents the score to be
  substracted for failed answers. Blank answers are not affected by
  this.

The fields `correct-weight` and `incorrect-weight` are optional. If
they appear in the file, the program will show the total score in the
user interface.

The *solutions* section specifies the correct answers for each model
(permutation) of the exam. Models are identified by letters ("A", "B",
etc.). For example::

    model-A: 4/1/2/1/1/1/2/4/1/2/3/1
    model-B: 3/2/1/4/4/2/2/1/4/2/3/3

In the example above, in the model A, the correct answer for the first
question is the 4th choice, for the second question is the 1st choice,
for the third question is the 2nd choice, etc.

The *permutations* section has information that allows to know how
questions and choices have been shuffled with respect to the original
order. They are used only for extracting statistics or fixing grades
after the exam if the solutions used for grading are found to have an
error in some questions. If you create the `.eye` manually, you
probably want to just remove this section from the file, unless you
need some of the above-mentioned functions.


Automatic detection of exam removal
...................................

If the camera in your setup is fixed, that is, you place an exam below
the camera, review it, remove it and place the next exam, you may want
Eyegrade to detect that you have removed the exam instead of having to
click on the *Save and capture next exam command*.

You can activate this experimental feature in the *Tools* menu,
*Experimental* submenu, option *Continue on exam removal*. When this
option is checked, Eyegrade saves the current capture and enters the
*search mode* automatically, after a few seconds of not detecting an
exam. Before placing the new exam, wait for the system to actually
enter the *search mode*: if you are too quick, Eyegrade might not
detect the removal of the exam.

**Tip:** don't use this option if the camera is not fixed, because
just moving it a little bit may cause Eyegrade to think that the exam
has been removed.
