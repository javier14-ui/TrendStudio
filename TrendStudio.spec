# Compilación Windows 11 x64. No incluir ICU ajeno encontrado en PATH (Poppler).
from pathlib import Path
root=Path(SPECPATH)
a=Analysis([str(root/'run.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'LICENSE'),'.'),(str(root/'THIRD_PARTY_NOTICES.md'),'.'),(str(root/'licenses'),'licenses')],
    hiddenimports=[],hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
# Windows 11 proporciona ICU. Una DLL homónima de Poppler exporta símbolos distintos.
a.binaries=[entry for entry in a.binaries if not any(token in str(entry[1]).lower() for token in ('poppler','codexprimaryruntime'))]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='TrendStudio',debug=False,bootloader_ignore_signals=False,
    strip=False,upx=False,console=False,disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='TrendStudio')
