#!/usr/bin/env python

import os
import sys
import setuptools

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if sys.version_info[0] != 2 or sys.version_info[1] not in [7]:
    print('ztreamy needs Python 2.7')
    sys.exit(1)

long_description = """
Eyegrade
(`<http://www.eyegrade.org/>`_)
uses a webcam to grade multiple choice question exams.
Needing just a cheap low-end webcam, it aims to be a low-cost
and portable alternative to other solutions based on scanners.

The main features of Eyegrade are:

- Grading the exams: By using a webcam, the graphical user interface
  of Eyegrade allows you to grade your exams. Eyegrade is able to
  recognize not only the answers to the questions, but also the
  identity of the student by using its hand-written digit recognition
  module. The whole process is supervised by the user in order to
  detect and fix potential detection errors.

- Exporting grades: Grades can be exported in CSV format, compatible
  with other programs such as spreadsheets.

- Typesetting the exams: Although you can create your exams with other
  tools, Eyegrade integrates an utility to creating MCQ exams. It is
  able to create your exams in PDF format. Eyegrade can automatically
  build several versions of the exam by shuffling questions and the
  choices within the questions.

The user manual can be found at
`<http://www.eyegrade.org/documentation.html>`_

Requirements:
--------------

Eyegrade runs on Python 2.7 only.
In addition, it requires `OpenCV version 2.4 <http://opencv.org/>`_
and `PyQt4 <https://www.riverbankcomputing.com/software/pyqt/download>`_
to work properly:

- For GNU/Linux systems install those packages from your distribution.
  For example, in Debian (Stretch and previous versions) and Ubuntu
  (16.10 and previous versions) just install the packages
  `python-opencv` and `python-qt4`.
  Note that `a bug in OpenCV 3 <https://github.com/opencv/opencv/issues/4969>`_
  makes Eyegrade fail with
  that version, and some distributions ship already OpenCV 3.

- For Windows platforms you can download OpenCV and PyQt4 from their
  official websites.

- For Mac OS/X I haven't tested the program.
  I believe it should be possible to install these dependencies
  and make Eyegrade work,
  but I'm not sure because I don't own a Mac computer.
  Feedback on this would be much appreciated.
"""

setuptools.setup(name='eyegrade',
      version='0.7.dev2',
      description='Grade MCQ exams with a webcam',
      long_description=long_description,
      author='Jesus Arias Fisteus',
      author_email='jfisteus@gmail.com',
      url='http://www.eyegrade.org/',
      packages=['eyegrade', 'eyegrade.qtgui', 'eyegrade.ocr'],
      package_data={'eyegrade': ['data/*']},
      scripts=['bin/eyegrade', 'bin/eyegrade-create'],
      test_suite ="tests.get_tests",
      classifiers= [
          'Development Status :: 4 - Beta',
          'Environment :: X11 Applications :: Qt',
          'Intended Audience :: Education',
          'License :: OSI Approved :: '
              'GNU Lesser General Public License v3 or later (LGPLv3+)',
          'Natural Language :: Spanish',
          'Natural Language :: English',
          'Natural Language :: Galician',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Microsoft :: Windows',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Topic :: Education',
      ],
)
