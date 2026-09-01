# Scraper de búsquedas laborales

Corre **una vez por día** con GitHub Actions, consulta portales de empleo
argentinos, descarta lo que no sirve según reglas editables y publica el
resultado en una página estática (GitHub Pages).

## Cómo funciona

```
GitHub Actions (cron diario)
   └─ python -m scraper.main
        ├─ Bumeran        → API JSON interna (estable)
        ├─ Computrabajo   → scraping de HTML + JSON-LD (Cloudflare: ver más abajo)
        ├─ WeRemoto       → scraping de HTML (SSR, remoto LATAM)
        └─ LinkedIn       → endpoint "guest", best-effort (frágil)
   └─ escribe data/ y docs/  →  commit + push  →  GitHub Pages actualiza la web
```

- **No inventa datos**: si un campo no está en el aviso, queda `null`.
- **No repite**: cada aviso visto se guarda en `data/vistos.json` (60 días) y no
  vuelve a aparecer.
- **Tolerante a fallos**: si un portal se cae, se registra en el log y en
  `data/ultima_corrida.json`, y la corrida sigue con los demás.
- **Ventana de 48 h + dedupe**: se corre 1×/día; 48 h evita perder avisos que un
  portal datea sólo como "ayer".

## Puesta en marcha (una sola vez)

1. Subí este repo a GitHub (**público**, para que Pages sea gratis).
2. **Settings → Pages** → *Source: Deploy from a branch* → rama `main`, carpeta `/docs`.
3. **Settings → Actions → General** → *Workflow permissions* → *Read and write*.
4. **Actions** → *scraper-diario* → *Run workflow* para la primera corrida.
5. La web queda en `https://<usuario>.github.io/<repo>/`.

## Configuración (sin tocar código)

### `config/busquedas.yml`
Términos a buscar, ventana horaria, qué portales están activos y qué categorías
de WeRemoto traer.

### `config/filtros.yml`
El filtro de descarte. Todo en minúsculas y sin acentos (`"ingles"`, no `"inglés"`).

| Bloque | Qué hace |
|---|---|
| `frases_excluyentes` | si el aviso menciona alguna, se descarta. Agrupadas por etiqueta (aparece como motivo). |
| `frases_perdon` | si aparecen **cerca** (±70 caracteres) de una frase excluyente, anulan el descarte (ej. "inglés no excluyente"). |
| `ubicaciones_permitidas` | si la ubicación no coincide con ninguna y el aviso no es remoto, se descarta. |
| `indicadores_remoto` | marcan un aviso como remoto aunque la ubicación diga otra cosa. |

Los avisos descartados quedan en `data/descartados.json` **con el motivo**, para
que puedas afinar las listas viendo qué se filtró de más o de menos.

## Salidas

| Archivo | Contenido |
|---|---|
| `data/avisos.json` / `docs/avisos.json` | avisos que pasaron el filtro (últimos 14 días) |
| `data/descartados.json` | avisos rechazados + `motivos_descarte` |
| `data/vistos.json` | IDs ya procesados (para no repetir) |
| `data/ultima_corrida.json` | estado por portal, conteos, errores |

Esquema de cada aviso: `id`, `portal`, `titulo`, `empresa`, `ubicacion`,
`modalidad` (`remoto`/`presencial`/`hibrido`/`null`), `salario`,
`fecha_publicacion` (ISO o `null`), `url`, `descripcion`, `capturado`.

## Correr local

```bash
pip install -r requirements.txt
python -m scraper.main
pytest            # pruebas del filtro
```

Para ver la página con los datos locales sin subir nada:

```bash
python -m http.server 8000 --directory docs
```

y abrir `http://localhost:8000`.

## Notas por portal

- **Bumeran** — usa la API interna `POST /api/avisos/searchV2` con el header
  `x-site-id: BMAR`. Trae la descripción completa en el listado.
- **Computrabajo** — sin API ni RSS. Está detrás de **Cloudflare**: se usa
  `curl_cffi` imitando el TLS de Chrome, que hoy alcanza. Si empezara a
  bloquear desde las IP de GitHub Actions, la corrida no se rompe (queda
  `estado: error` para ese portal en el log). Plan B: correr el scraper desde
  otra IP o sumar un proxy.
- **WeRemoto** — la mayoría de los avisos son de clientes de EE.UU. que piden
  inglés C1/C2: el filtro `ingles_alto` descarta casi todo y deja los pocos
  aptos (típicamente los marcados 🇦🇷).
- **LinkedIn** — endpoint `jobs-guest` sin login. Funciona hoy pero es frágil
  (429/999 por IP). Viene sin descripción, así que ahí el filtro sólo mira
  título y ubicación. Si bloquea de forma persistente, poné `linkedin: false`
  en `config/busquedas.yml`.

## Portales que se evaluaron y quedaron afuera

- **Upwork** — sin RSS público (lo sacaron en 2023) y la API oficial exige
  OAuth2 con app aprobada y token de usuario. El HTML está detrás de Cloudflare
  + PerimeterX y bloquea IPs de datacenter. No es viable sin login y va contra
  sus términos. Además el perfil es casi idéntico a WeRemoto (clientes de EE.UU.,
  inglés obligatorio). No se incluyó.

## Ajustes que quizá quieras hacer

- **Términos**: tus términos exactos son angostos en Bumeran (devuelve 0–3 por
  día). Si querés más volumen, agregá `marketing digital` y `redes sociales`
  a `terminos` en `config/busquedas.yml`.
- **Ubicaciones amplias**: `ubicaciones_permitidas` incluye `argentina` y
  `provincia de buenos aires` para no perder avisos de LinkedIn mal geolocalizados.
  Si ves demasiado ruido del interior, sacá esos términos.
