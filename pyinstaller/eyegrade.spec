# -*- mode: python -*-
a = Analysis(['bin\\eyegrade'],
             pathex=['C:\\eyegrade'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
a.datas += Tree('eyegrade\\data', prefix='data')
a.datas = list({tuple(map(str.upper, t)) for t in a.datas})
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='eyegrade.exe',
          debug=False,
          strip=None,
          upx=True,
          console=False,
          icon='eyegrade\\data\\eyegrade.ico')
