"""Descarga avisos públicos de Qt; solo se ejecuta al preparar una distribución."""
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parents[1]/'licenses'/'Qt'
root.mkdir(parents=True,exist_ok=True)
urls={
 'LGPL-3.0.txt':'https://raw.githubusercontent.com/qt/qtbase/dev/LICENSES/LGPL-3.0-only.txt',
 'GPL-3.0.txt':'https://raw.githubusercontent.com/qt/qtbase/dev/LICENSES/GPL-3.0-only.txt',
 'Qt-GPL-exception-1.0.txt':'https://raw.githubusercontent.com/qt/qtbase/dev/LICENSES/Qt-GPL-exception-1.0.txt',
 'Qt-third-party-notices.html':'https://doc.qt.io/qt-6/licenses-used-in-qt.html',
 'PySide-licenses.html':'https://doc.qt.io/qtforpython-6/licenses.html',
}
for name,url in urls.items():
    with urlopen(Request(url,headers={'User-Agent':'TrendStudio-build/1.0'}),timeout=25) as response:(root/name).write_bytes(response.read())
(root/'SOURCES.txt').write_text('\n'.join(f'{name}: {url}' for name,url in urls.items()),encoding='utf-8')

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=set()
    def handle_starttag(self,tag,attrs):
        href=dict(attrs).get('href','')
        if tag=='a' and '-attribution-' in href and href.startswith(('qtcore-','qtgui-','qtnetwork-','qtwidgets-','qtsvg-')):self.links.add(href)
parser=Links();parser.feed((root/'Qt-third-party-notices.html').read_text(encoding='utf-8'))
def fetch(href):
    url=urljoin('https://doc.qt.io/qt-6/',href)
    with urlopen(Request(url,headers={'User-Agent':'TrendStudio-build/1.0'}),timeout=25) as response:(root/Path(href).name).write_bytes(response.read())
with ThreadPoolExecutor(max_workers=3) as executor:list(executor.map(fetch,sorted(parser.links)))
