# Radar Laboral

Un buscador de avisos de trabajo que **corre solo una vez por día**, revisa varios
portales de empleo argentinos, tira a la basura lo que no te sirve según reglas
que vos elegís, y arma una **página web** con lo que queda y un link a cada aviso.

Pensado para búsquedas de **community manager, social media, marketing y contenido**
en CABA, GBA norte y remoto, pero se cambia a lo que necesites editando dos archivos.

Lo que trae de fábrica (community manager / marketing) es **solo un ejemplo**:
cada persona lo adapta a su rubro editando dos archivos de texto. No se toca código.

Ejemplo funcionando: <https://portelachaindaniela-collab.github.io/scraper-busquedas-laborales/>

Hay **dos formas de usarlo**. Elegí una:

| | Opción A — en la web | Opción B — en tu compu |
|---|---|---|
| Instalar algo | No | Sí, Python (una vez) |
| Cuenta de GitHub | Sí (gratis) | No |
| Resultado | Una página online que se actualiza sola cada día | Una página local que ves cuando corrés el programa |
| Privacidad | El repo es público | Todo queda en tu máquina |

---

## Opción A — en la web (no instalás nada)

### 1. Creá tu copia

En la página del repo, botón verde **“Use this template” → “Create a new repository”**.
Poné un nombre, dejalo **público** (si es privado, GitHub Pages se paga), y creá.

> El botón “Download ZIP” también existe, pero con el ZIP tenés que armar todo a
> mano; para la web conviene el template.

### 2. Decí qué querés buscar

Editá **`config/busquedas.yml`** (clic en el archivo → ícono del lápiz):

```yaml
terminos:
  - community manager
  - analista de marketing digital
  # agregá o sacá los que quieras

ventana_horas: 48        # avisos publicados en las últimas 48 h

portales:
  bumeran: true
  computrabajo: true
  weremoto: true
  linkedin: true
```

Abajo, **“Commit changes”** para guardar.

### 3. Decí qué querés descartar

Editá **`config/filtros.yml`**. Es una lista de frases: si el aviso menciona
alguna, se descarta. Está en minúsculas y sin acentos a propósito (`"ingles"`,
no `"inglés"`).

```yaml
frases_excluyentes:
  ingles_alto:
    - "ingles avanzado"
    - "ingles c1"
    - "bilingue"
  ventas:
    - "ventas"
    - "generacion de leads"

ubicaciones_permitidas:      # si la ubicación no coincide y no es remoto, se descarta
  - capital federal
  - caba
  - remoto
  - san isidro
```

(El archivo ya viene con un ejemplo completo y comentado.)

### 4. Prendé la página web

En tu repo: **Settings → Pages**. En *Source* elegí **“Deploy from a branch”**,
rama **`main`**, carpeta **`/docs`**, y **Save**.

### 5. Prendé el robot y hacé la primera corrida

- **Settings → Actions → General** → abajo, *Workflow permissions* → marcá
  **“Read and write permissions”** → **Save**.
- **Settings → Actions → General** → arriba → **“Allow all actions”** si te lo pide.
- Andá a la pestaña **Actions**, entrá en **“scraper-diario”**, botón
  **“Run workflow”**. En 5–8 minutos termina.

### 6. Listo

Tu página queda en `https://TU-USUARIO.github.io/TU-REPO/` y se actualiza sola
todos los días alrededor de las 8 de la mañana (hora Argentina).

Para mirar los avisos que se descartaron y por qué (sirve para afinar el filtro):
archivo **`data/descartados.json`** en tu repo.

---

## Opción B — en tu compu (más privado, sin cuentas)

1. **Instalá Python** desde <https://www.python.org/downloads/>.
   En el instalador, marcá la casilla **“Add Python to PATH”**.
2. **Descargá el proyecto**: botón verde **“Code” → “Download ZIP”**, y descomprimilo
   donde quieras (por ejemplo el Escritorio).
3. **Editá tus búsquedas y filtros**: abrí `config/busquedas.yml` y `config/filtros.yml`
   con el **Bloc de notas** (clic derecho → Abrir con) y guardá.
4. **Doble clic en `correr.bat`**. Va a instalar lo que falta, buscar los avisos
   (tarda unos minutos) y abrir la página en el navegador.
5. Cuando termines de mirar, cerrá la ventana negra.

Cada vez que quieras avisos frescos, volvés a hacer doble clic en `correr.bat`.
Nada sale de tu computadora.

---

## Qué mira y qué tan confiable es cada portal

| Portal | Cómo lo lee | Nota |
|---|---|---|
| **Bumeran** | API interna del sitio (JSON) | Estable. Con términos muy específicos trae pocos por día. |
| **Computrabajo** | Lee el HTML + datos estructurados | Tiene Cloudflare. Hoy anda; si algún día empieza a bloquear, esa corrida lo marca en rojo y sigue con los demás. |
| **WeRemoto** | Lee el HTML | Casi todo pide inglés C1/C2 → el filtro de inglés descarta la mayoría, queda lo poco apto. |
| **LinkedIn** | Endpoint público sin login | Frágil: puede empezar a bloquear por IP. Si pasa, poné `linkedin: false`. Los avisos vienen sin descripción, así que ahí el filtro solo mira título y ubicación. |

**Upwork** se evaluó y quedó afuera: sacaron el RSS, la API pide OAuth, y bloquea
servidores. Además pide inglés casi siempre, igual que WeRemoto.

---

## Detalle del filtro (`config/filtros.yml`)

| Bloque | Qué hace |
|---|---|
| `frases_excluyentes` | Si el aviso menciona alguna frase, se descarta. Agrupadas por etiqueta (aparece como motivo en `data/descartados.json`). |
| `frases_perdon` | Si aparecen **cerca** de una frase excluyente (±70 caracteres), anulan el descarte. Ej: *"inglés no excluyente"*. |
| `ubicaciones_permitidas` | Si la ubicación no coincide con ninguna y el aviso no es remoto, se descarta. Incluye términos amplios (`argentina`, `buenos aires`) para no perder avisos mal geolocalizados. |
| `ubicaciones_excluidas` | Ganan sobre lo anterior: filtran el interior y GBA sur/oeste aunque el aviso diga *"Argentina"*. |
| `indicadores_remoto` | Marcan un aviso como remoto aunque la ubicación diga otra cosa. |

Los avisos ya publicados no se re-filtran: los cambios valen para las corridas
siguientes.

---

## Desde la terminal (avanzado)

```bash
git clone https://github.com/TU-USUARIO/TU-REPO
cd TU-REPO
pip install -r requirements.txt
python -m scraper.main        # corre el scraper
pytest                        # pruebas del filtro
python -m http.server 8000 --directory docs   # ver la página en localhost:8000
```

Estructura: `scraper/portales/` un archivo por portal (cada uno expone
`buscar(termino, desde) -> list[Aviso]`); `scraper/filtros.py` el motor de
descarte; `scraper/main.py` el orquestador. Si un portal falla, se registra en
`data/ultima_corrida.json` y la corrida sigue con los demás.

**Reglas del proyecto:** no se inventan datos (campo ausente → `null`); los
avisos vistos se guardan en `data/vistos.json` (60 días) para no repetirlos.

---

## Licencia

MIT — usalo, copialo y modificalo libremente. Ver [LICENSE](LICENSE).
