# Manual de usuario · beta 1.1

**Primeros pasos:** abre el ejecutable, pulsa Buscar oportunidades de hoy, revisa un resultado, analízalo opcionalmente desde IA local y guarda la investigación. Lee [IA local](IA_LOCAL.md) antes de utilizar borradores generados.

## Buscar y revisar

Abre Radar, escribe palabras clave y pulsa Buscar tendencias. Se consultan los RSS configurados, hasta 150 artículos por fuente y 30 fuentes. La búsqueda filtra títulos y resúmenes de lo recibido; no busca el archivo histórico completo de un medio. Todas las palabras deben aparecer, sin distinguir mayúsculas ni tildes.

Puedes filtrar categoría, país ISO (PE, US…) y periodo. El país es la cobertura configurada de la fuente; vacío significa desconocido o global. El periodo excluye registros sin fecha publicada, incluidos enlaces manuales sin fecha. **Todo el periodo** muestra también registros sin fecha. Los filtros no eliminan datos del proyecto ni limitan lo exportado.

Selecciona una fila para ver resumen, fechas, procedencia, datos observados y todas las fuentes agrupadas. Abrir fuente usa tu navegador. El texto procede de la fuente; no se generan resúmenes con IA ni se validan automáticamente afirmaciones.

Buscar nuevamente actualiza los enlaces coincidentes y conserva el resto de la investigación. Para empezar sin datos previos, utiliza Nueva. Las consultas guardadas conservan el texto de búsqueda. Solo favoritas limita qué RSS se consulta. Cancelar detiene nuevas solicitudes; la activa tiene timeout de 12 segundos. Si una fuente falla, las demás continúan y se muestra la incidencia.

## Configurar fuentes

En Configuración avanzada, añade nombre, URL de RSS/Atom, categoría y país opcional. Usa canales publicados por el proveedor y respeta sus condiciones. Quita una fuente o marca favoritas seleccionando una fila. Categorías personalizadas aparecen en el filtro. No todas las páginas web son RSS: si una dirección no es válida, la aplicación lo indica.

La caché conserva respuestas por 30 minutos de forma predeterminada; cambia a 0 para desactivarla o usa Limpiar caché e historial. Las fechas de consulta de resultados cacheados permanecen originales. La configuración no inicia consultas automáticas. El historial opcional guarda solo texto y fecha en `history.json`; no existe un visor de historial separado. Las consultas guardadas sí se recuperan desde Radar.

## YouTube

En tu propio proyecto de Google Cloud, habilita YouTube Data API v3 y crea una clave autorizada. Consulta las instrucciones oficiales: https://developers.google.com/youtube/v3/getting-started . No se necesita una clave de OpenAI. Pega tu clave en Configuración avanzada y guarda. El campo se vacía y Windows cifra el secreto localmente. Eliminar clave borra el archivo cifrado.

En YouTube y canales, introduce un tema, un ID de canal UC… o un @usuario. Selecciona periodo y consulta. Se recuperan como máximo 25 resultados, ordenados por fecha; no es un ranking exhaustivo de rendimiento. El registro muestra vistas, duración ISO 8601 (por ejemplo PT3M = 3 minutos), fechas y canal. Selecciona un video para más estadísticas y la comparación vistas/suscriptores, cuando esté disponible. Los suscriptores son actuales, pueden estar redondeados u ocultos y no describen la audiencia histórica de cada video. No se estiman ingresos, CTR ni retención.

Las cuotas y restricciones se administran en Google Cloud. La aplicación informa límites o acceso denegado sin reintentar en bucle. No calcula un saldo exacto de cuota. Los resultados llegan también a Radar: puedes crear una oportunidad desde allí. Guarda canales para volver a consultarlos con un clic sobre la lista.

## Importar sin API

**Añadir enlace** permite registrar información de cualquier plataforma. Introduce título, URL HTTP/HTTPS, fuente, categoría, país opcional, fecha ISO opcional y resumen. Se marca como manual; registrar un enlace no consulta ni descarga su contenido.

**Importar CSV** acepta UTF-8, columnas `title,url` obligatorias y las siguientes opcionales: `source,category,country,published,summary,viewCount,likeCount,subscriberCount,duration,channel`. Las cifras deben ser enteros no negativos y las fechas ISO, por ejemplo `2026-11-04T09:00:00-05:00`. Máximo 2000 filas y 4 MB. Hay una plantilla vacía en `plantilla-importacion.csv`. La importación completa se rechaza si una fila no es válida. Los datos se identifican como manual_csv, incluso si se copian de una plataforma.

**Importar Trends** acepta el CSV de «Interés a lo largo del tiempo» descargado desde Google Trends. Indica tema, URL exacta de la consulta y país. Conserva la primera serie del archivo, incluidas fechas e índices `<1`. El índice 100 es el máximo relativo de esa consulta, no cien búsquedas. Para comparar temas, exporta consultas comparables; TrendStudio no convierte índices en tráfico. Otras tablas de Trends no se aceptan en este importador.

## Evaluar oportunidades

Selecciona un resultado de Radar y crea una oportunidad. Evalúa actualidad, público, evidencia, fuentes, originalidad, facilidad de producción y baja competencia observable de 0 a 5. Ajusta los pesos de 0 a 10. Un valor alto de facilidad o baja competencia suma a favor. Si no tienes evidencia, usa 0 y explica la incertidumbre en las notas.

Cada contribución es `valor / 5 × peso / suma de pesos × 100`. Se muestra el total y se conserva el desglose. Las siete valoraciones son tuyas; la aplicación no finge medir competencia, originalidad o interés. Añade una justificación con datos observables, un enfoque y el estado: Nueva, Interesante, Guardada, En investigación, Lista para guion, Descartada o Producida. Puedes editar posteriormente la evaluación completa.

## Guardar, exportar y transferir

Guardar investigación crea JSON completo; Abrir lo recupera con oportunidades, datos y canales. La aplicación pregunta por cambios pendientes antes de cerrar o reemplazar una investigación. Los proyectos usan URLs, no rutas absolutas a otros archivos.

En Informes, exporta JSON, CSV o HTML. El informe HTML se abre localmente en un navegador y no carga bibliotecas ni servicios externos. Puedes imprimirlo desde el navegador si necesitas PDF. Los videos se ordenan por vistas observadas dentro de la muestra, sin corrección por edad; revisa su procedencia. Se muestran palabras repetidas, canales guardados y oportunidades con sus referencias.

Enviar a CreatorStudio crea una subcarpeta con `creatorstudio.json` y `LEEME.txt`. No envía archivos a nadie ni abre otra aplicación. Solo incluye las oportunidades que ya has creado.

## Resolver problemas

- Sin resultados: borra palabras clave, selecciona Todo el periodo y desactiva Solo favoritas.
- Fuente caída: revisa el enlace en el navegador o elimina la fuente; las demás siguen operativas.
- Acceso YouTube denegado: comprueba API habilitada, clave y restricciones del proyecto.
- Cuota agotada: espera al restablecimiento indicado por Google o utiliza los datos guardados.
- Error al guardar: selecciona una carpeta en la que tengas permisos; no uses carpetas del sistema.
- En otra computadora la clave no se abre: introdúcela de nuevo en ese equipo.


## Buscar oportunidades de hoy

El botón consulta las fuentes seleccionadas y cambia el periodo a las últimas 24 horas. Conserva los filtros de palabra, país y categoría que hayas elegido. La prioridad combina actualidad en una ventana de siete días, dominios citados e interés observable. En Configuración avanzada puedes cambiar sus pesos; una columna muestra el resultado y el detalle explica cada contribución y dato faltante.

Una fuente RSS aislada no acredita popularidad. La comparación de titulares puede agrupar acontecimientos relacionados, pero no sustituye la lectura de las fuentes ni demuestra que sean independientes.

## Canales y metadatos públicos sin clave

RSS del canal acepta un ID público UC… de 24 caracteres; no resuelve @usuarios sin API. Un canal puede entregar un feed vacío o inaccesible. La aplicación informa esa situación sin evadirla. Obtener metadatos de enlace usa oEmbed oficial para enlaces de YouTube o TikTok; cuando el proveedor no da título o autor, se indica que no está disponible. No se ejecuta el HTML embebido ni se descargan videos. Para Instagram y cualquier fuente no compatible, usa el formulario o CSV.

Comparar canales y antigüedad muestra frecuencia media entre fechas observadas, duración media cuando existe y vistas acumuladas divididas por la antigüedad (mínimo un día). No mide velocidad reciente. Un muestreo de 25 videos no describe toda la historia del canal. Todos los datos faltantes se conservan como desconocidos.

## Investigaciones recientes y guion

En Informes, el selector Investigaciones guardadas permite reabrir las diez rutas locales más recientes, sin conectar a internet. Guardar investigación conserva también análisis de IA y agrupaciones. Preparar para guion exporta `guion.json` con esquema `trendstudio.script-package.v1`; incluye oportunidades, análisis, fuentes, fechas, procedencias y advertencias. No envía información a otra aplicación.

Los siete estados organizan el proceso completo: Nueva → Interesante → Guardada → En investigación → Lista para guion → Producida; Descartada permite separar ideas que no continuarás. Los estados son etiquetas editables, no acciones automáticas.
