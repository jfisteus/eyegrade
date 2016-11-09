#!/usr/bin/env python

from setuptools import setup

setup(name='eyegrade',
      version='0.7.dev1',
      description='Grading multiple choice questions with a webcam',
      author='Jesus Arias Fisteus',
      author_email='jfisteus@gmail.com',
      url='http://www.eyegrade.org/',
      packages=['eyegrade', 'eyegrade.qtgui', 'eyegrade.ocr'],
      package_data={'eyegrade': ['data/*']},
      scripts=['bin/eyegrade', 'bin/eyegrade-create'],
    )
