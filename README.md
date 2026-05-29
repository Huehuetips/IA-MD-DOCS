# Docs to Markdown Pipeline

Pipeline para descubrir páginas de documentación, extraer el contenido principal y exportarlo como archivos `.md` locales con metadatos.

## Qué hace

- Descubre URLs internas desde una URL raíz
- Lee sitemaps automáticos desde `robots.txt`, `sitemap.xml`, `sitemap_index.xml` y `sitemap-index.xml` cuando existan
- Acepta sitemaps adicionales con `--sitemap-url`
- Filtra por prefijos permitidos y paths excluidos
- Canonicaliza URLs preservando query string funcional y eliminando solo parámetros de tracking conocidos
- Descarga HTML con `requests`
- Puede reintentar con `Playwright` si el contenido parece demasiado pobre
- Trata XML/WSDL como caso compatible y suprime el warning de parseo HTML sobre XML
- Convierte HTML limpio a Markdown
- Escribe frontmatter YAML en cada archivo
- Genera `index.json` con metadatos de salida
- Mantiene caché por hash en `_meta/cache_manifest.json`
- Puede aplicar una limpieza opcional mediante un comando externo de IA

## Cómo funciona

El proceso tiene dos etapas:

1. Descubrimiento de URLs candidatas.
2. Evaluación, limpieza y exportación de los documentos finales.

No todas las URLs descubiertas terminan como archivo final. El pipeline:

- visita URLs hasta `--max-visits`
- evalúa hasta `max(max-pages * 3, 20)` candidatas o menos, si hay menos descubiertas
- conserva como máximo `--max-pages` documentos finales
- descarta páginas de bajo valor según heurísticas de contenido
- deduplica por URL canónica, que conserva query funcional

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Uso básico

```bash
docs-md crawl https://example.com/docs --output ./docs-local
```

## Opciones de la CLI

### URL y salida

- `url`: URL raíz a partir de la cual se inicia el crawl
- `--output`: directorio de salida obligatorio

### Límites de procesamiento

- `--max-pages`: número máximo de documentos finales a escribir. Valor por defecto: `100`
- `--max-visits`: número máximo de páginas a visitar durante el descubrimiento. Si no lo defines, se calcula como `max(max-pages * 10, 200)`
- `--timeout`: tiempo de espera en segundos para requests, HEAD y lectura de sitemaps. Valor por defecto: `15`

### Filtros de crawl

- `--include-prefix`: limita el crawl a paths que empiecen con uno o más prefijos
- `--exclude-path`: excluye paths que empiecen con uno o más prefijos
- `--sitemap-url`: agrega uno o más sitemaps manuales al descubrimiento automático

### Renderizado HTML

- `--render-mode auto`: usa `requests` y reintenta con `Playwright` si el HTML parece demasiado corto o sin headings
- `--render-mode requests`: usa solo `requests`
- `--render-mode playwright`: usa `Playwright` siempre

En `auto`, el fallback a `Playwright` se activa si:

- el HTML extraído es corto
- no hay headings útiles
- o el contenido no alcanza la calidad esperada

Si vas a usar `Playwright`, instala Chromium:

```bash
python -m playwright install chromium
```

### Caché

- `--no-cache`: desactiva la reutilización por manifest
- La caché vive en `_meta/cache_manifest.json`
- Si una URL no cambió, se conserva el `.md` existente y se reutiliza su metadata

### Limpieza IA

- `--ai-mode off`: desactiva la limpieza IA
- `--ai-mode rewrite`: activa la limpieza IA con un comando externo
- `--ai-command`: plantilla del comando a ejecutar. Por defecto: `copilot`
- `--ai-model`: nombre de modelo que se inserta en la plantilla. Por defecto: `claude-sonnet-4.5`
- `--ai-timeout`: tiempo límite para la ejecución del comando de IA en segundos. Por defecto: `120`

La plantilla de `--ai-command` recibe el prompt por `stdin` y puede usar:

- `{model}`
- `{title}`
- `{url}`

Si el comando empieza por `copilot`, el sistema intenta completar automáticamente flags útiles como modelo, prompt, modo silencioso y permisos ampliados.

### Logs

- `--log-level DEBUG`
- `--log-level INFO`
- `--log-level WARNING`
- `--log-level ERROR`

## Ejemplos

Con renderizado automático:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --render-mode auto
```

Con filtros:

```bash
docs-md crawl https://example.com/docs \
  --output ./docs-local \
  --include-prefix /docs \
  --exclude-path /blog \
  --exclude-path /changelog
```

Con sitemap explícito:

```bash
docs-md crawl https://example.com/docs \
  --output ./docs-local \
  --sitemap-url https://example.com/sitemap.xml
```

Con limpieza IA desactivada explícitamente:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --ai-mode off
```

Con IA vía comando externo:

```bash
docs-md crawl https://example.com/docs \
  --output ./docs-local \
  --ai-mode rewrite \
  --ai-model claude-sonnet-4.5 \
  --ai-command "copilot"
```

Con logs detallados:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --log-level DEBUG
```

## Salida

Cada documento se escribe con:

- frontmatter YAML
- contenido Markdown limpio

El nombre del archivo se deriva de la ruta de la URL, no del título.
Si la URL incluye query funcional, la query se transforma en un sufijo estable para evitar colisiones entre documentos distintos.

Además se generan:

- `_meta/index.json`: lista de documentos exportados con sus metadatos
- `_meta/cache_manifest.json`: estado de caché por URL

## Reglas de descubrimiento

- Solo se visitan URLs del mismo dominio que la URL raíz
- Se excluyen automáticamente imágenes, PDFs y ZIPs
- Se ignoran URLs de búsqueda o con patrones tipo `?query=`, `?search=` y `/search`
- Las URLs se normalizan quitando fragmentos y preservando query string funcional
- La query se conserva salvo parámetros de tracking conocidos como `utm_*`, `gclid`, `fbclid`, `mkt_tok`, `mc_*`
- El `trailing slash` final se colapsa

Importante: esa normalización ya no colapsa recursos funcionales como `?op=...` o `?WSDL`; estos se conservan como recursos distintos.

## Selección de documentos

El pipeline no guarda todas las páginas descubiertas. Usa heurísticas para decidir qué conservar:

- descarta páginas con poco texto
- descarta páginas con demasiados enlaces y poco contenido real
- favorece páginas con más texto, headings y bloques de código
- ordena candidatos por puntuación antes de escribir los archivos finales
- eleva la prioridad de rutas tipo `asmx`, `wsdl`, `soap` y `endpoint`

## Limpieza de contenido

Antes de exportar, el contenido pasa por estas etapas:

1. Extracción del bloque principal por selectores comunes como `main`, `article`, `.content`, `.prose`, etc.
2. Eliminación de ruido como navegación, footer, TOC, breadcrumbs y scripts.
3. Conversión a Markdown.
4. Limpieza determinista de boilerplate.
5. Limpieza IA opcional si está activada.
6. Parseo compatible con XML/WSDL sin depender de `lxml`

## Notas

- El user-agent HTTP por defecto es `docs-md-pipeline/0.1`
- El pipeline usa Playwright en modo headless
- El descubrimiento de sitemaps usa el origen real de la URL raíz, incluyendo esquema y puerto
- El crawler sigue enlaces en `a[href]`, `link[href]`, `area[href]` y `form[action]`
- El fallback a Playwright en `auto` se activa cuando el HTML resultante parece demasiado corto o sin headings
- Si la caché está habilitada y el contenido no cambia, se reutiliza el Markdown existente

## Estado

Este scaffold está preparado para crecer hacia:

- selectores específicos por dominio
- clasificación semántica
- chunking
- integración más profunda con modelos para pulido editorial
