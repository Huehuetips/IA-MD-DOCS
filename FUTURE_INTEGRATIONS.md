# Future Integrations

Documento técnico para extensiones futuras del proyecto `docs-md-pipeline`.

## Estado actual

El proyecto ya funciona para:

- documentación HTML clásica
- páginas con navegación interna simple
- sitios con sitemaps
- servicios SOAP/ASMX con `?WSDL`, `?disco` y `?op=...`

## Integraciones futuras propuestas

### 1. Perfiles por sitio

Objetivo:

- aplicar reglas distintas por dominio o patrón de URL
- evitar heurísticas globales para todos los sitios

Capacidades:

- canonicalización por perfil
- selectores de contenido por perfil
- umbrales de descarte por perfil
- scoring por perfil
- render mode por perfil

### 2. Descubrimiento automático de tipo de sitio

Objetivo:

- inferir el tipo de sitio sin configuración manual obligatoria

Señales posibles:

- `.asmx`, `.wsdl`, `?op=` -> SOAP/ASMX
- `/api/`, `/v1/`, `/reference/` -> API
- `main`, `article`, `.prose` -> docs HTML
- páginas sin HTML útil y con mucha interacción -> JS-heavy

### 3. Soporte de más formatos

Objetivo:

- exportar recursos no-HTML de manera especializada

Formatos candidatos:

- XML
- WSDL
- OpenAPI
- JSON
- Markdown remoto

### 4. Mejor manejo de autenticación

Objetivo:

- navegar documentación protegida sin hardcodes

Integraciones posibles:

- headers personalizados
- cookies persistentes
- bearer tokens
- basic auth
- sesión autenticada por login

### 5. Estrategia de reintentos y robustez

Objetivo:

- tolerar mejor errores transitorios de red y parseo

Mejoras:

- backoff exponencial
- retries configurables
- circuit breaker simple
- timeouts por tipo de recurso

### 6. Extracción semántica avanzada

Objetivo:

- mejorar la calidad del Markdown exportado

Ideas:

- detectar ejemplo de request/response
- preservar bloques de código con mayor fidelidad
- extraer tablas complejas
- normalizar listas de operaciones y endpoints

### 7. Salida estructurada adicional

Objetivo:

- complementar Markdown con metadatos de más alto nivel

Formatos posibles:

- JSON index expandido
- YAML por documento
- graph export
- manifest de relaciones entre páginas

### 8. Integración con validación de enlaces

Objetivo:

- evitar publicar documentación con referencias rotas

Funciones:

- check de links internos
- check de anchors
- reporte de 404
- reporte de redirecciones

### 9. Integración con análisis de cobertura

Objetivo:

- medir qué tan completo quedó el crawl

Métricas:

- páginas descubiertas vs exportadas
- ratio de descarte
- ratio de cache hits
- profundidad máxima alcanzada
- cobertura por sección o prefijo

### 10. Sistema de plugins

Objetivo:

- permitir extensiones sin modificar el núcleo

Posibles plugins:

- extractor plugin
- canonicalizer plugin
- output writer plugin
- sitemap plugin
- doc type classifier plugin

## Prioridad sugerida

1. perfiles por sitio
2. detección automática de tipo de sitio
3. soporte de formatos no-HTML
4. autenticación
5. validación de enlaces
6. métricas de cobertura

## Criterio para aceptar una integración

Una integración nueva solo debe entrar si cumple al menos uno de estos puntos:

- corrige una limitación funcional real
- mejora la robustez del crawl
- reduce configuración manual repetitiva
- mejora la calidad del Markdown exportado
- evita pérdida de información técnica
