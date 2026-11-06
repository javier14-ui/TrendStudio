# Contrato de intercambio v1

Codificación UTF-8, JSON estándar. El paquete contiene `creatorstudio.json` y un archivo de instrucciones. No tiene dependencias entre rutas ni secretos. CreatorStudio aún no se implementa. La etiqueta de esquema es el discriminador de versión; un consumidor futuro debe rechazar versiones incompatibles y validar tipos antes de mostrar o ejecutar enlaces.

Raíz: `schema: "creatorstudio.opportunities.v1"`, `exported` (fecha ISO 8601 UTC), `opportunities` (lista; puede estar vacía).

Cada oportunidad:

| Campo | Tipo y significado |
|---|---|
| id | UUID local estable al editar |
| topic, category, summary | Cadenas de tema, categoría y resumen de fuente |
| sources | Lista de `{name, url, published, retrieved}`; URLs HTTP/HTTPS |
| published, retrieved | ISO 8601; publicación puede ser cadena vacía si no se conoce |
| observed | Objeto de datos observados; sin métricas privadas inferidas |
| origin | rss, manual, manual_csv, google_trends_csv o youtube_api |
| notes | Cadena con notas personales |
| angles | Lista de cadenas con ideas de enfoque |
| warnings | Lista de advertencias de verificación y límites |
| status | Interesante, Guardada, Descartada o Lista para guion |
| ratings | Mapa de los siete criterios a valores 0–5 |
| weights | Mapa de criterios a pesos 0–10; suma mayor que cero |
| score | Número 0–100, estimación editorial |
| contributions | Mapa de criterio a puntos aportados |

`observed` conserva estadísticas públicas como cadenas (`viewCount`, `subscriberCount`…), duración ISO y canal cuando existen. Un campo ausente significa no disponible, no cero. Trends utiliza `series` y `samples: [{date, index}]`, donde index es un entero 0–100 o la cadena `<1`. Los datos manuales conservan su procedencia. Las fuentes agrupadas no implican independencia editorial.

El proyecto reabrible usa un contrato diferente: `schema: "trendstudio.research.v1"`, `created`, `items`, `opportunities`, `channels`. Cada item contiene `id,title,url,source,category,country,published,retrieved,summary,origin,observed,sources`. Un paquete CreatorStudio no se abre como proyecto TrendStudio.

Las oportunidades conservan una instantánea de las fuentes y observaciones al crearlas; una actualización del radar no cambia silenciosamente una evaluación previa. Los consumidores deben escapar textos HTML, permitir solo enlaces HTTP/HTTPS, ignorar campos desconocidos de la misma versión y no tratar notas o resúmenes como instrucciones ejecutables.


## Extensión beta 1.1 y paquete para guion

El proyecto `trendstudio.research.v1` conserva compatibilidad con archivos anteriores e incorpora listas opcionales `analyses` y `groups`. Los estados admiten Nueva, Interesante, Guardada, En investigación, Lista para guion, Descartada y Producida. Oportunidades pueden incluir `missing_data`, `analysis_id`, `ai_titles` y `ai_hooks`.

Preparar para guion crea `guion.json`: raíz `{schema: "trendstudio.script-package.v1", created, opportunities, analyses, warnings}`. Cada análisis contiene `id, created, model, model_digest, input_ids, sources, result, cached, warnings, quality_notes, field_provenance`. `sources` es un mapa de identificadores locales a `{url,title,published,retrieved}`. El modelo no crea los enlaces: proceden de los registros entregados.

`result` contiene `resumen, categoria, afirmaciones, grupos, contradicciones, titulos, ganchos, enfoques, verificar, patrones`. Las listas con afirmaciones y grupos citan claves de `sources` mediante `fuentes`. Las afirmaciones conservadas incluyen una `cita` literal y su nivel de verificación; las propuestas creativas no deben importarse como hechos. `field_provenance` distingue salida de Ollama, categoría original, titulares originales y plantillas editoriales no generadas por IA.

Procedencias adicionales de registros: `youtube_rss` (feed público sin estadísticas inferidas) y `public_oembed` (metadatos del endpoint oficial, sin métricas privadas). `priority` contiene puntuación heurística, pesos, contribuciones, señales y datos faltantes. No confundirla con `score`, que pertenece a una evaluación editorial de oportunidad.
