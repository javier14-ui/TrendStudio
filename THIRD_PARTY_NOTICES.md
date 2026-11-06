# Licencias y atribuciones

El código propio de TrendStudio se entrega bajo MIT (LICENSE). Los contenidos de RSS y plataformas pertenecen a sus respectivos titulares y no se relicencian. Las fuentes se enlazan desde los registros e informes. La distribución no incluye artículos ni videos de muestra.

Dependencias de ejecución:

- **Python 3.14**: Python Software Foundation License y licencias incluidas de terceros. https://www.python.org/downloads/source/
- **PySide6 Essentials / Shiboken6 6.12.0**: LGPL-3.0 / GPL según componentes, o licencia comercial; se utiliza Qt Widgets bajo la opción LGPL. https://doc.qt.io/qtforpython-6/licenses.html
- **Qt 6.12** y componentes terceros incorporados: licencias distribuidas en `licenses/`; código fuente correspondiente disponible en https://download.qt.io/official_releases/qt/ y https://download.qt.io/official_releases/QtForPython/ .
- **feedparser 6.0.14**: BSD-2-Clause. https://github.com/kurtmckee/feedparser
- **feedparser-sgmllib 2.1.0**: licencia incluida por el paquete. https://pypi.org/project/feedparser-sgmllib/
- **defusedxml 0.7.1**: PSF License. https://github.com/tiran/defusedxml
- **PyInstaller 6.22.3**: GPL con excepción para distribución de ejecutables generados; el bootloader se incluye sin modificaciones. https://pyinstaller.org/en/stable/license.html

Se conservan los textos y metadatos originales mediante `scripts/collect_licenses.py`. PySide/Qt se distribuyen como bibliotecas dinámicas dentro de `_internal`; no se modificaron sus fuentes. El usuario puede reemplazarlas por versiones compatibles y reconstruir la aplicación con los scripts y código entregados. No se impide la ingeniería inversa necesaria para depurar modificaciones de las bibliotecas LGPL. Mantén estos avisos y las licencias al redistribuir; revisa las obligaciones aplicables antes de publicar versiones modificadas.

Fuentes y documentación consultada:

- BBC Mundo: https://feeds.bbci.co.uk/mundo/rss.xml
- NASA: https://www.nasa.gov/feed/
- PlayStation Blog: https://blog.playstation.com/feed/
- Agencia Andina: https://andina.pe/agencia/rss/noticia.aspx
- Google Trends, exportación autorizada: https://support.google.com/trends/answer/4365538?hl=es
- YouTube Data API: https://developers.google.com/youtube/v3/getting-started

Google Trends: «Fuente de datos: Google Trends». TrendStudio no es un producto de Google, YouTube, TikTok, Instagram ni de los medios consultados. Añadir una fuente no concede derechos de republicación: usa los enlaces y verifica las condiciones del proveedor.


Integraciones locales y públicas de beta 1.1:

- Ollama: https://github.com/ollama/ollama (MIT). No se distribuye su ejecutable ni ningún modelo; se usa la instalación local existente. El usuario mantiene las licencias del modelo instalado. API estructurada: https://docs.ollama.com/capabilities/structured-outputs .
- TikTok oEmbed: https://developers.tiktok.com/docs/en/embed-videos . El endpoint puede omitir metadatos y está sujeto a cambios del proveedor. No se incorpora ni ejecuta el HTML de inserción.
- YouTube Atom: https://developers.google.com/youtube/data/guides/push_notifications . Se consulta el feed de un canal bajo demanda, sin servidor ni suscripciones push.

Las DLL de ICU ajenas a Qt detectadas en herramientas del entorno de compilación se excluyen; Windows 11 suministra ICU del sistema. No se redistribuyen bibliotecas de otros proyectos del usuario.
