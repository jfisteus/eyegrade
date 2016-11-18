# -*- mode: python -*-
a = Analysis(['../../bin/eyegrade-create'],
             pathex=['.'],
             hiddenimports=['six', 'packaging', 'packaging.version',
                            'packaging.specifiers', 'packaging.requirements'],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          exclude_binaries=False,
          name='eyegrade-create',
          debug=False,
          strip=None,
          upx=True,
          console=True)
## coll = COLLECT(exe,
##                a.binaries,
##                a.zipfiles,
##                a.datas,
##                strip=None,
##                upx=True,
##                name='eyegrade')
