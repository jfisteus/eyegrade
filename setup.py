import os
import sys
import setuptools

if sys.version_info[0] < 3 or (sys.version[0] == 3 and sys.version[1] < 5):
    print('eyegrade does not run in legacy python versions: '
          'use python 3.5 or later.')
    sys.exit(1)

# read the contents of the README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

requirements = [
    'opencv-python==4.0.0.21',
    'openpyxl==2.6.0',
    'PyQt5==5.12',
]


setuptools.setup(
    name='eyegrade',
    version='0.8.1',
    description='Grade MCQ exams with a webcam',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
        'eyegrade': [
            'data/*',
            'data/svm/*',
            'data/locale/*/LC_MESSAGES/eyegrade.mo',
        ]
    },
    python_requires='>=3.5',
    install_requires=requirements,
    test_suite='tests.get_tests',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Education',
        'License :: OSI Approved :: '
            'GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: Spanish',
        'Natural Language :: English',
        'Natural Language :: Galician',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
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
