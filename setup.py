#!/usr/bin/env python

from distutils.core import setup

setup(name='eyegrade',
      version='0.2.6',
      description='Grading multiple choice questions with a webcam',
      author='Jesus Arias Fisteus',
      author_email='jfisteus@gmail.com',
      url='http://www.it.uc3m.es/jaf/eyegrade/',
      packages=['eyegrade', 'eyegrade.qtgui'],
      package_data={'eyegrade': ['data/*']},
    )
