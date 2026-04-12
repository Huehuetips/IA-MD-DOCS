# Docs to Markdown Pipeline

MVP para descubrir páginas de documentación, extraer contenido principal y guardarlo como archivos `.md` locales con metadatos.

## Qué incluye

- Descubrimiento de URLs internas desde una URL raíz
- Descubrimiento adicional desde `sitemap.xml`, `sitemap_index.xml` y `robots.txt` cuando existan
- Filtros básicos por prefijos y paths excluidos
- Fetch HTML con `requests`
- Fallback opcional con `Playwright` para páginas renderizadas con JS
- Extracción del contenido principal por selectores comunes
- Conversión de HTML limpio a Markdown
- Frontmatter YAML
- `index.json` con metadatos de salida
- Caché por hash en `_meta/cache_manifest.json`
- Paso opcional para limpieza IA mediante comando externo, desactivado por defecto

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Uso

```bash
docs-md crawl https://example.com/docs --output ./docs-local
```

Modo de renderizado:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --render-mode auto
```

Si vas a usar `Playwright`, instala el navegador:

```bash
python -m playwright install chromium
```

Con filtros:

```bash
docs-md crawl https://example.com/docs ^
  --include-prefix /docs ^
  --exclude-path /blog ^
  --exclude-path /changelog
```

Con limpieza IA desactivada explícitamente:

```bash
docs-md crawl https://example.com/docs --ai-mode off
```

Con sitemap explícito:

```bash
docs-md crawl https://example.com/docs ^
  --sitemap-url https://example.com/sitemap.xml
```

Con IA vía comando externo:

```bash
docs-md crawl https://example.com/docs ^
  --ai-mode rewrite ^
  --ai-model claude-sonnet-4.5 ^
  --ai-command "copilot"
```

La plantilla `--ai-command` recibe el prompt por `stdin` y puede usar:

- `{model}`
- `{title}`
- `{url}`

Si no pasas `--ai-command`, el valor por defecto es:

```bash
copilot
```

Con logs visibles durante la ejecucion:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --log-level INFO
```

Si necesitas mas detalle tecnico:

```bash
docs-md crawl https://example.com/docs --output ./docs-local --log-level DEBUG
```

## Caché

El archivo `_meta/cache_manifest.json` guarda hashes del contenido extraído por URL.

Si una página no cambió:

- se evita reprocesarla
- se conserva el `.md` existente
- se reutiliza su metadata para ranking e índice

## Estado

Este scaffold está preparado para crecer hacia:

- selectores específicos por dominio
- clasificación semántica
- chunking
- integración más profunda con modelos para pulido editorial
