# -*- mode: python -*-
import sys

a = Analysis(['../../bin/eyegrade'],
             pathex=['.'],
             hiddenimports=['six', 'packaging', 'packaging.version',
                            'packaging.specifiers', 'packaging.requirements'],
             hookspath=None,
             runtime_hooks=None)
a.datas += Tree('eyegrade/data', prefix='data')
a.datas += [('data/default.cfg', 'installers/pyinstaller/default.cfg', 'DATA')]
if sys.platform.startswith("win32"):
    a.datas = list({tuple(map(str.upper, t)) for t in a.datas})
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
          icon='eyegrade/data/eyegrade.ico')
