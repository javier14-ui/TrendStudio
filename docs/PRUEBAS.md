# Informe de pruebas · 1.1.0-beta.1

Fecha local de ejecución: **5 de noviembre de 2026, America/Lima**. Los registros técnicos usan UTC y algunas marcas corresponden al 6 de noviembre UTC. Plataforma: Windows 11 x64, Python 3.14.4, Qt/PySide 6.12.0, PyInstaller 6.22.3. No se prueba ni entrega una variante para laptop.

## Automatizadas: 39 aprobadas

Comando ejecutado: `python -m pytest -q`. Resultado final: **39 passed in 4.15s**.

- Lectura RSS y Atom, fechas y zonas horarias, rechazo de XML inseguro y fuentes inválidas.
- Duplicados por URL/titular, filtros por tema, categoría, país, periodo y fecha ausente.
- Guardado/reapertura, validación de proyectos y configuración, CSV manual, CSV de Trends, HTML escapado y protección frente a fórmulas CSV.
- Fórmula y desglose de oportunidades; rechazo de pesos inválidos y valores no finitos.
- Cifrado/lectura de un secreto de prueba con DPAPI, sin clave real ni secretos en entregables.
- Caché HTTP, cancelación, desconexión y errores HTTP/cuota mediante respuestas controladas.
- YouTube sin clave y procesamiento de respuestas API controladas. **Esto no equivale a una prueba API real.**
- Referencias IA inexistentes, citas no respaldadas, cifras nuevas y repeticiones; etiquetas de procedencia y alternativas editoriales.
- Bloqueo de una tarea IA, modelo ausente, dos etapas, caché, reapertura con análisis y paquete para guion.
- Ollama desconectado mediante puerto local no disponible; cancelación contra servidor local lento.
- Frecuencia/duración/antigüedad de canales con datos controlados, agrupación de acontecimientos y oEmbed sin ejecutar HTML.
- Interfaz Qt: apertura sin credenciales, selección, filtros, guardado, edición de oportunidades con ID estable, historial de investigaciones recientes y temporizador activo durante una tarea en segundo plano.

## Pruebas reales de servicios

Ejecutado `scripts/verify_services.py --ollama`; ver [registro](pruebas/servicios.json).

| Servicio | Resultado observado |
|---|---|
| RSS BBC Mundo, NASA, PlayStation Blog y Andina | 74 entradas en total, sin errores en la consulta final de servicios |
| RSS público de YouTube | Endpoint documentado accesible, pero **0 videos** para el canal probado; funcionalidad de recopilación real de videos no confirmada |
| YouTube oEmbed | Un enlace público devolvió metadatos, sin clave |
| TikTok oEmbed | El enlace público de ejemplo oficial devolvió metadatos, sin sesión |
| Ollama instalado | `llama3.2:1b`, 1.321.098.329 bytes ya existentes; ninguna descarga de modelos |
| Generación Ollama | Dos etapas completadas; tres títulos y tres ganchos estructurados; 8,44 s en la prueba final de servicios |
| Caché IA real | Reutilización en 0,017 s |
| Cancelación IA real | Interrupción en 0,42 s; sin guardar respuesta parcial |

El endpoint antiguo de RSS YouTube respondió HTTP 404 durante diagnóstico. Se utiliza el endpoint documentado `/xml/feeds/videos.xml`; que responda no garantiza entradas. No se sorteó el bloqueo ni se recurrió a scraping.

## Ejecutable Windows actualizado

Ejecutado realmente `TrendStudio.exe --verify-install … --live --ollama`, con Python eliminado de PATH y sin PYTHONHOME/PYTHONPATH. Se inspeccionaron los módulos cargados: Python y Qt procedían de la distribución, no del entorno de desarrollo. Ver [registro del ejecutable](pruebas/ejecutable.json).

- Código de salida: **0**.
- Ventana Qt visible y capturas reales a 1120 × 740.
- RSS real desde el binario: **74 entradas**, sin errores.
- IA local desde el binario: **8.33 s**, 3 títulos, 3 ganchos y avisos de calidad conservados.
- JSON guardado y reabierto, CSV, HTML, paquete para guion y DPAPI comprobados desde el binario.
- Pico observado del proceso TrendStudio: **96.2 MiB** durante RSS + IA. Esta cifra no incluye el servidor Ollama ni memoria GPU.
- Creación de ventana medida dentro de la aplicación: **0.229 s**; no es un benchmark general de arranque.
- Al finalizar, `ollama ps` no mostraba un modelo cargado. No se midió un pico aislado de RAM/GPU del modelo; no se presenta un valor inventado.

Corrección del empaquetado: una DLL ICU incompatible procedente de Poppler en PATH impedía cargar QtCore. La especificación de compilación excluye esas bibliotecas ajenas y utiliza ICU de Windows 11. No se modificó Windows ni se instalaron paquetes globales.

## Revisión visual y de seguridad

Capturas reales de [Radar](capturas/radar.png), [Configuración](capturas/configuracion.png) e [IA local](capturas/ia-local.png). También se revisó la interfaz a 1024 × 680. Se conservan modo oscuro, campos legibles, detalles desplazables y estado de tarea. La prueba UI controlada comprobó que el bucle de eventos seguía respondiendo durante trabajo en segundo plano.

Antes de publicar se inspeccionaron los archivos seleccionados para Git: sin credenciales, rutas personales incrustadas, cachés, investigaciones del usuario, entornos, ejecutables ni modelos. Los binarios se entregan como adjunto de Release, fuera del historial de código. Los textos y enlaces exportados se escapan; los enlaces admiten HTTP/HTTPS. Los archivos no son una zona de ejecución de código.

## Límites y pendientes

- **YouTube Data API real pendiente:** no se proporcionó una clave. Cuotas y errores se probaron con respuestas controladas, no como acceso real autorizado.
- **RSS YouTube parcial:** respuesta válida pero sin videos en la muestra probada. Usa API opcional o importación si el canal no expone datos.
- **Calidad de llama3.2:1b:** la estructura final se validó, pero se observaron paráfrasis sin citas literales, errores de interpretación y repetición durante ajustes. Se descartan o sustituyen los campos que no pasan controles y se informa su procedencia. La semántica no está garantizada: revisar antes de publicar.
- Las contradicciones son candidatos para revisión humana. Ni citas correctas ni JSON válido prueban la verdad de una afirmación.
- TikTok oEmbed es metadato de un enlace; no descubre tendencias globales ni entrega métricas privadas. Instagram usa importación manual.
- Sin internet se verificó la apertura y exportación de datos guardados; no se simuló una consulta remota exitosa.
- No hay firma digital, prueba en una instalación limpia distinta, ensayo prolongado de carga ni medición de GPU independiente. No se declara compatibilidad universal ni estabilidad de producción.

Esta entrega se publica como **beta**, no como una predicción validada de rendimiento o viralidad.
