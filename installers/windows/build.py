from __future__ import print_function

import os
import os.path
import sys
import subprocess

eyegrade_dir = os.path.join(os.path.dirname( \
                                os.path.dirname(os.path.dirname( \
                                    os.path.realpath(__file__)))))
python_dir = os.path.join(os.path.dirname(sys.executable))
pyi_spec_file = os.path.join(eyegrade_dir, 'installers', 'windows',
                             'eyegrade.spec')
nsis_file = os.path.join(eyegrade_dir, 'installers', 'windows', 'eyegrade.nsi')

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def which(program):
    for path in os.environ['PATH'].split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, program)
        if is_exe(exe_file):
            return exe_file
    return None

def get_pyi_path():
    path = which('pyi-build.exe')
    if not path:
        # Try in the current Python's installation
        path = os.path.join(python_dir, 'Scripts', 'pyi-build.exe')
        if not is_exe(path):
            path = None
    return path

def get_nsis_path():
    path = which('makensis.exe')
    if not path:
        # Try in the current Python's installation
        path = os.path.join('C:\\', 'Program Files (x86)', 'NSIS',
                            'makensis.exe')
        if not is_exe(path):
            path = os.path.join('C:\\', 'Program Files', 'NSIS',
                                'makensis.exe')
            if not is_exe(path):
                path = None
    return path

prev_cwd = os.getcwd()
os.chdir(eyegrade_dir)

pyi_path = get_pyi_path()
if not pyi_path:
    print('Error: PyInstaller executable pyi_build.exe not found.')
    sys.exit(1)
result = subprocess.call([pyi_path, pyi_spec_file])
if result != 0:
    print('Error: PyInstaller build failed.')
    sys.exit(1)

nsis_path = get_nsis_path()
if not nsis_path:
    print('Error: NSIS executable makensis.exe not found.')
    sys.exit(1)
result = subprocess.call([nsis_path, nsis_file])
if result != 0:
    print('Error: NSIS build failed.')
    sys.exit(1)

os.chdir(prev_cwd)
