import os
import sys
import setuptools

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if sys.version_info[0] < 3:
    print('eyegrade does not run in legacy python versions: use python 3')
    sys.exit(1)

long_description = """
Eyegrade
(`<https://www.eyegrade.org/>`_)
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
`<https://www.eyegrade.org/documentation.html>`_

Requirements:
--------------

Eyegrade runs on Python 3 only.
Support for legacy Python versions has been dropped.
Requirements will be automatically installed from PyPI.

"""

requirements = [
    'opencv-python==4.0.0.21',
    'openpyxl==2.6.0',
    'PyQt5==5.12',
]


setuptools.setup(
    name='eyegrade',
    version='0.8rc1',
    description='Grade MCQ exams with a webcam',
    long_description=long_description,
    author='Jesus Arias Fisteus',
    author_email='jfisteus@gmail.com',
    url='https://www.eyegrade.org/',
    packages=[
        'eyegrade',
        'eyegrade.qtgui',
        'eyegrade.ocr',
        'eyegrade.tools'
    ],
    package_data={
        'eyegrade': ['data/*', 'data/svm/*']
    },
    scripts=[
        'bin/eyegrade',
        'bin/eyegrade-create'
    ],
    install_requires=requirements,
    test_suite='tests.get_tests',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Education',
        'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: Spanish',
        'Natural Language :: English',
        'Natural Language :: Galician',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Topic :: Education',
    ],
    options={
        'app': {
            'formal_name': 'eyegrade',
            'bundle': 'org.eyegrade',
        },
        # Desktop/laptop deployments
        'macos': {
            'app_requires': requirements,
        },
        'linux': {
            'app_requires': requirements,
        },
        'windows': {
            'app_requires': requirements,
            'icon': 'eyegrade/data/eyegrade',
        },
    },
    entry_points={
        'gui_scripts': [
            'eyegrade = eyegrade.eyegrade:main',
        ],
        'console_scripts': [
            'eyegrade-create = eyegrade.create_exam:main',
        ]
    }
)
