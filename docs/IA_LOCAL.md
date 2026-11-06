# IA local y revisión de fuentes

1. Abre Ollama en Windows si no está ejecutándose. TrendStudio no lo inicia ni lo instala.
2. En IA local, pulsa Detectar modelos instalados y elige `llama3.2:1b` u otro modelo que ya tengas.
3. Selecciona una noticia en Radar. Vuelve a IA local y pulsa Analizar resultado seleccionado, o analiza hasta seis resultados visibles.
4. Espera las dos etapas: análisis de fuentes y generación de ideas. Puedes seguir leyendo la investigación o cancelar desde la barra inferior.
5. Revisa el resultado, sus advertencias, la procedencia de cada sección y los documentos enlazados. Crea una oportunidad si resulta útil.

## Qué se envía y a dónde

Solo al servidor local `127.0.0.1:11434`: hasta seis títulos (220 caracteres), extractos (650 caracteres), URLs, fechas, categorías y observaciones públicas. No se envía la clave API. No hay endpoint cloud configurable ni descarga automática de modelos. Dos solicitudes se ejecutan secuencialmente bajo un bloqueo entre ventanas de TrendStudio. Contexto 4096, límite 1600 tokens por etapa, cuatro hilos de CPU configurados; Ollama decide la aceleración disponible. Se solicita liberar el modelo tras cada etapa. Un servidor compartido con otra aplicación puede mantener cargas propias.

## Calidad y procedencia

El formato JSON exige campos concretos y referencias pertenecientes a la lista de documentos. Referencias inexistentes o insuficientes se descartan y se informa. Una afirmación solo se presenta como cita de fuente si su texto literal aparece en el extracto entregado; si ninguna pasa ese control, se muestran los titulares originales. «Hecho reportado» significa que la fuente lo afirma, no que TrendStudio lo haya demostrado.

Se distinguen hechos reportados, rumores, interpretaciones y propuestas. Las posibles contradicciones son sugerencias del modelo y requieren comparar los textos originales; no identificarlas no demuestra ausencia de contradicciones. El filtro de cifras y URLs no comprueba equivalencias, porcentajes, causalidad ni nombres propios. El modelo pequeño puede cometer errores de idioma y de interpretación incluso con JSON válido.

Los campos marcados `ollama_borrador` son propuestas del modelo. `categoria_fuente` conserva la categoría del registro; `titulares_originales_no_IA` identifica evidencia textual original. `plantilla_editorial_no_IA` identifica alternativas basadas en el título cuando la IA repite frases, produce verificaciones poco concretas o incluye cifras nuevas. Las plantillas pueden conservar el título en su idioma original. Nunca se presentan como una respuesta generada por IA.

## Caché, cancelación y ausencia de Ollama

La caché depende de modelo, versión del prompt y contenido; dura 24 horas y conserva la fecha de generación. Desmarca Reutilizar análisis para pedir uno nuevo. Se guardan como máximo 40 entradas; no se borran investigaciones. Los análisis ya guardados pueden leerse sin Ollama y sin internet.

Cancelar interrumpe la lectura local mediante comprobaciones frecuentes, cierra la conexión y no guarda un análisis parcial. Si Ollama no está abierto, se informa sin impedir RSS, importación, lectura, evaluación, guardado o exportación. Una respuesta mal formada tampoco reemplaza un análisis válido existente.

La aplicación es una ayuda de investigación. Antes de publicar, contrasta fuentes primarias, confirma fechas y cifras, revisa derechos y separa la interpretación del hecho reportado. No hay modelo estadístico validado de viralidad.
