from __future__ import print_function

import os
import os.path
import sys
import subprocess

eyegrade_dir = os.path.join(os.path.dirname( \
                                os.path.dirname(os.path.dirname( \
                                    os.path.realpath(__file__)))))
build_dir = os.path.join(eyegrade_dir, 'build')
dist_files_dir = os.path.join(eyegrade_dir, 'dist', 'eyegrade')
python_dir = os.path.join(os.path.dirname(sys.executable))
pyi_spec_file = os.path.join(eyegrade_dir, 'installers', 'windows',
                             'eyegrade.spec')
nsis_file = os.path.join(eyegrade_dir, 'installers', 'windows', 'eyegrade.nsi')

if os.path.exists(build_dir):
    if not os.path.isdir(build_dir):
        raise ValueError('build should be a directory: ' + build_dir)
else:
    os.mkdir(build_dir)

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
    path = which('pyinstaller.exe')
    if not path:
        # Try in the current Python's installation
        path = os.path.join(python_dir, 'Scripts', 'pyinstaller.exe')
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

def build_install_file_list():
    with open(os.path.join(build_dir, 'install_files.nsh'), 'w') as f:
        for root, dirs, files in os.walk(dist_files_dir):
            root_rel_path = os.path.relpath(root, dist_files_dir)
            if root_rel_path == '.':
                for file in files:
                    f.write('File "${{SOURCE_DIR}}\{}"\n'.format(file))
            else:
                f.write('\n')
                f.write('CreateDirectory "$INSTDIR\{}"\n'.format(root_rel_path))
                for file in files:
                    rel_path = os.path.join(root_rel_path, file)
                    f.write('File "/oname={}" "${{SOURCE_DIR}}\{}"\n'.format(rel_path, rel_path))

def build_uninstall_file_list():
    with open(os.path.join(build_dir, 'uninstall_files.nsh'), 'w') as f:
        for root, dirs, files in os.walk(dist_files_dir, topdown=False):
            root_rel_path = os.path.relpath(root, dist_files_dir)
            f.write('\n')
            if root_rel_path == '.':
                for file in files:
                    f.write('Delete "$INSTDIR\{}"\n'.format(file))
                f.write('RMDir "$INSTDIR"')
            else:
                for file in files:
                    rel_path = os.path.join(root_rel_path, file)
                    f.write('Delete "$INSTDIR\{}"\n'.format(rel_path))
                f.write('RMDir "$INSTDIR\{}"\n'.format(root_rel_path))

prev_cwd = os.getcwd()
os.chdir(eyegrade_dir)

pyi_path = get_pyi_path()
if not pyi_path:
    print('Error: PyInstaller executable pyinstaller.exe not found.')
    sys.exit(1)
result = subprocess.call([pyi_path, pyi_spec_file])
if result != 0:
    print('Error: PyInstaller build failed.')
    sys.exit(1)

build_install_file_list()
build_uninstall_file_list()

nsis_path = get_nsis_path()
if not nsis_path:
    print('Error: NSIS executable makensis.exe not found.')
    sys.exit(1)
result = subprocess.call([nsis_path, nsis_file])
if result != 0:
    print('Error: NSIS build failed.')
    sys.exit(1)

os.chdir(prev_cwd)
