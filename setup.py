#!/usr/bin/env python

import os
import sys
import setuptools

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if sys.version_info[0] != 2 or sys.version_info[1] not in [7]:
    print('ztreamy needs Python 2.7')
    sys.exit(1)

setuptools.setup(name='eyegrade',
      version='0.7.dev1',
      description='Grade MCQ exams with a webcam',
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
