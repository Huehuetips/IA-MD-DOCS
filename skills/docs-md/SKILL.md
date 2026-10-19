---
name: docs-md
description: Usar cuando haga falta convertir la documentación de un sitio web (sitio de docs, sitemap, portal de una API) en archivos Markdown locales para consultarla sin depender de internet, o cuando haya que modificar, probar o publicar el propio pipeline `docs-md` de este repositorio. Triggers: "descarga la documentación de", "pásame esta doc a markdown", "crawlea este sitio de docs", "docs-md", "actualiza la documentación local de".
---

# docs-md

Herramienta que descubre las páginas de una documentación, extrae el contenido principal y las exporta como `.md` con frontmatter YAML y un `index.json`. Su salida sirve como insumo local para agentes (por ejemplo, `researcher`), en vez de consumir tokens buscando en la web cada vez.

## Requisitos

- Python 3.11 o superior, gestionado con `uv` (ya instalado en esta máquina).
- La herramienta `docs-md` instalada globalmente:

```bash
uv tool install --editable "<ruta-de-este-repo>"
docs-md --help
```

- Opcional, solo si el sitio necesita JavaScript para renderizar: `python -m playwright install chromium`.

## Uso básico

```bash
docs-md crawl https://example.com/docs --output ./docs-local --ai-mode off
```

Usa siempre `--ai-mode off` salvo que el usuario pida explícitamente la limpieza por IA. Por defecto `--ai-command` invoca `copilot`, que puede no estar instalado en la máquina.

## Opciones que más se usan

- `--max-pages N`: cantidad máxima de documentos finales (default 100). Empieza con un número bajo para validar la salida antes de un crawl grande.
- `--include-prefix /docs`: limita el crawl a esos prefijos de ruta.
- `--exclude-path /blog`: excluye prefijos (repetible).
- `--sitemap-url URL`: agrega un sitemap manual cuando el automático no alcanza.
- `--render-mode auto|requests|playwright`: `auto` (default) reintenta con navegador solo si el HTML sale pobre. Usa `playwright` si el sitio es una SPA.
- `--no-cache`: ignora `_meta/cache_manifest.json` y reescribe todo.

## Verificación de la salida

Después de cada crawl, revisa antes de darlo por bueno:

1. `index.json` existe y tiene entradas.
2. Abre dos o tres `.md` al azar y confirma que el contenido es el de la documentación, no menús ni pies de página.
3. Confirma que el frontmatter tiene `title` y `url`.

Si el resultado sale vacío o con ruido, prueba `--render-mode playwright` o ajusta `--include-prefix`.

## Modificar o mejorar el pipeline

Este repositorio es público y el agente puede mejorarlo. Antes de tocar nada:

1. Lee `README.md` y `FUTURE_INTEGRATIONS.md` para conocer el alcance acordado.
2. Corre los tests: `uv run --with pytest --python 3.12 python -m pytest -q`. Deben pasar todos (13 al día de hoy).
3. Añade un test por cada cambio de comportamiento.
4. Repite los tests tras el cambio.

## Publicar cambios

Decide cómo publicar **comprobando quién está autenticado**, nunca asumiéndolo:

```bash
OPERADOR=$(gh api user --jq .login)
DUENO=$(gh repo view --json owner --jq .owner.login)
```

- **Si `OPERADOR == DUENO`** (el propietario del repo): puedes hacer commit y push directo a `main`.
- **Si no coinciden**: NUNCA hagas push a `main`. Crea una rama, haz push de esa rama y pide al usuario que abra el pull request:

```bash
git checkout -b mejora/<tema-corto>
git add -A && git commit -m "<mensaje>"
git push -u origin mejora/<tema-corto>
```

Luego informa: "Rama `mejora/<tema-corto>` subida; abre el PR desde GitHub para revisarla."

En cualquiera de los dos casos, antes del commit confirma que no se suben archivos generados (`.venv/`, `docs-local/`, `_meta/`); el `.gitignore` ya cubre cachés y entornos.

## Reglas

- No hagas commit de contenido descargado de sitios de terceros dentro de este repo; el output va a una carpeta fuera del repositorio.
- No cambies la licencia ni elimines tests para hacer pasar una prueba.
- Respeta `robots.txt` y los límites de velocidad del sitio; no crawlees sitios sin permiso del usuario cuando sea un sitio ajeno con uso comercial.
