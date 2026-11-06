"""Conserva los textos de licencias y metadatos de las dependencias instaladas."""
import importlib.metadata as md
import shutil
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'licenses'
root.mkdir(exist_ok=True)
packages=['PySide6-Essentials','shiboken6','feedparser','feedparser-sgmllib','defusedxml','pyinstaller']
for package in packages:
    d=md.distribution(package);dest=root/package;dest.mkdir(exist_ok=True)
    (dest/'METADATA.txt').write_text(d.read_text('METADATA') or '',encoding='utf-8')
    for p in d.files or []:
        if any(word in str(p).lower() for word in ('license','copying','copyright','notice')) and Path(d.locate_file(p)).is_file():
            target=dest/str(p).replace('../','').replace('..\\','');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(d.locate_file(p),target)
base=Path(sys.base_prefix)/'LICENSE.txt'
if base.exists():shutil.copy2(base,root/'PYTHON-LICENSE.txt')
