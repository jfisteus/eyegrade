# -*- mode: python -*-
import platform
import os.path
import glob

a = Analysis(['eyegrade-launcher.py'],
             pathex=['.'],
             hookspath=None,
             runtime_hooks=None)
a.datas += Tree('eyegrade/data', prefix='data')
a.datas += [('data/default.cfg', 'installers/pyinstaller/default.cfg', 'DATA')]
if platform.system() == 'Windows':
    a.datas = list({tuple(map(str.upper, t)) for t in a.datas})
    if int(platform.version().split('.')[0]) >= 10:
        # Issue when building from Windows 10 regarding redistributable DLLs
        # Install Windows 10 SDK so that the DLL files get installed
        # See https://github.com/pyinstaller/pyinstaller/issues/1566
        crt_path = 'C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x86'
        for dll_file in glob.iglob(os.path.join(crt_path, 'api-ms-win-crt-*.dll')):
            a.binaries.append((os.path.basename(dll_file), dll_file, 'BINARY'))
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          exclude_binaries=False,
          name='eyegrade',
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon='../../eyegrade/data/eyegrade.ico')
