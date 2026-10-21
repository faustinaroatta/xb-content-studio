# XB Architecture · Content Studio

App interna para planificar y medir el contenido de **Instagram XB**, **LinkedIn XB**, **LinkedIn John** y **LinkedIn Ximena**.

### 🌐 Idioma / Language
- La app está **en inglés por defecto**. Cada persona puede pasarla a **español** con el selector **🌐 Language / Idioma** (en la pantalla de login y en la barra lateral). La elección **queda guardada por usuario**: John puede usarla en inglés y el resto del equipo en español al mismo tiempo, sobre los mismos datos.
- El idioma de la app y el idioma de **los copys que escribe la IA** son independientes: en cada pantalla de IA hay un selector *Caption language / Idioma del copy* (English, Spanish o Bilingual). Por defecto los copys salen **en inglés**, porque el público de XB está en Florida.
- Las ideas generadas por IA salen en el idioma que tengas elegido en la app (se puede cambiar en el mismo formulario).

| Sección | Qué hace |
|---|---|
| **Home** (Inicio) | Posts de la semana, pendientes de revisión, pipeline por estado, mejor post del mes |
| **Calendar** (Calendario) | Vista de 1 o 2 semanas por cuenta. Crear, editar, duplicar y borrar posts. **✨ Plan with AI** arma la semana entera |
| **Ideas** | Banco compartido con votos ★, generador de ideas con IA inspirado en estudios famosos (ArchDaily, AD, STRANG, Olson Kundig…), pasar idea → calendario |
| **AI Captions** (Copys IA) | Copy para una cuenta, **adaptar un tema a las 4 cuentas** con su voz, o reescribir un copy |
| **Reports** (Reportes) | Likes, comentarios, visualizaciones y engagement por post y por cuenta, rendimiento por pilar. **Se actualizan solos** |
| **Accounts** (Cuentas) | Estado de conexión y la "voz" de cada cuenta (la edita el equipo y la usa la IA) |

Stack: Python · Streamlit · SQLAlchemy (SQLite local / Postgres en la nube) · Claude API · Instagram Graph API · LinkedIn API.

---

## Paso 1 · Cuenta de GitHub y repositorio

1. Creá una cuenta en **github.com** (ideal con un mail de la empresa, ej. `marketing@…`).
2. Arriba a la derecha **+ → New repository** → nombre `xb-content-studio` → marcá **Private** → **Create repository**.
3. En el repo vacío: **uploading an existing file** → arrastrá **todo el contenido** de esta carpeta (incluidas `.streamlit` y `.github`; en Mac mostrá los archivos ocultos con `Cmd + Shift + .`) → **Commit changes**.
   - ⚠️ Nunca subas `secrets.toml` (el `.gitignore` ya lo evita si usás git).
4. Para sumar al equipo: repo → **Settings → Collaborators → Add people** (solo hace falta para quien vaya a tocar código; para usar la app no).

## Paso 2 · Probarlo en tu compu (15 min)

Necesitás Python 3.11 o superior (`python3 --version`). En Mac, si no lo tenés: python.org/downloads.

```bash
cd xb-content-studio
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Abrí `.streamlit/secrets.toml` y para la primera prueba:
- poné tu `GEMINI_API_KEY` (paso 3, gratis),
- **borrá o comentá la línea `DATABASE_URL`** (así usa una base local),
- cambiá las contraseñas de `[users]`.

```bash
streamlit run app.py
```
Se abre en `http://localhost:8501`.

### Checklist de prueba
- [ ] Entrar con un usuario de `[users]`. Con usuario o clave mal tiene que dar error.
- [ ] Cambiar **🌐 Language / Idioma** a Español: toda la app cambia y, al salir y volver a entrar, recuerda tu idioma. Otro usuario sigue viéndola en inglés.
- [ ] **Calendar → ＋ New**: crear un post, escribir un tema y tocar **✨ Write caption with AI**. Guardar. Aparece en el día correcto con el color de su cuenta.
- [ ] Abrirlo, cambiar estado a "En revisión", **Duplicate for another account**, después **Delete** el duplicado.
- [ ] Cambiar la vista a **2 wk** y filtrar por una sola cuenta.
- [ ] **✨ Plan with AI** → **Generate plan** → editar una fila → **Add … posts to the calendar**.
- [ ] **Ideas → ✨ Generate with AI** → guardar 2 ideas → votarlas ★ → **→ Calendar**.
- [ ] **AI Captions → Adapt to all 4 accounts** → guardar en el calendario.
- [ ] **Reports → Add metrics manually**: cargar 2 posts falsos y ver gráficos y tabla. Pegar ese mismo link en un post del calendario → aparece "Rendimiento por pilar".
- [ ] **Accounts**: editar la voz de John con su rol real → **Save voice** → generar un copy para John y ver que la respeta.
- [ ] Abrir la app en otra pestaña con otro usuario y ver los mismos datos.

## Paso 3 · Clave de IA gratis (Google Gemini)

1. Entrá a **aistudio.google.com** con una cuenta de Google (Gmail).
2. Aceptá los términos → botón **Get API key** → **Create API key**.
3. Copiala (empieza con `AQ.` o `AIza`) y pegala en `GEMINI_API_KEY`.

El nivel gratuito de Gemini alcanza de sobra para un equipo chico. No pide tarjeta. Si algún día quieren usar Claude (pago), se completa `ANTHROPIC_API_KEY` en su lugar.

## Paso 4 · Base de datos compartida (Supabase, gratis)

Para que todos vean lo mismo desde la nube hace falta una base compartida:
1. supabase.com → **New project** (región US East, guardá la contraseña).
2. **Connect** (arriba) → **Session pooler** → copiá la URI y reemplazá `[YOUR-PASSWORD]`.
3. Esa URI va en `DATABASE_URL`. Las tablas se crean solas la primera vez que abre la app.

## Paso 5 · Publicarla para el equipo (Streamlit Community Cloud, gratis)

1. share.streamlit.io → **Continue with GitHub** → autorizá el acceso al repo privado.
2. **Create app** → repo `xb-content-studio`, branch `main`, archivo `app.py`.
3. **Advanced settings → Secrets**: pegá el contenido completo de tu `secrets.toml` (con `DATABASE_URL` de Supabase).
4. **Deploy**. Te da un link tipo `xb-content-studio.streamlit.app`.
5. Compartí el link y a cada persona su usuario/clave de `[users]`. Para sumar a alguien: Settings → Secrets → agregar línea en `[users]`.

## Paso 6 · Vincular las cuentas para los reportes automáticos

La app detecta sola qué cuentas tienen credenciales y las sincroniza **cada 6 horas al abrirla** y **todos los días a las 7:17 (Miami)** vía GitHub Actions, sin que nadie tenga que pedirlo.

### Instagram XB (el más fácil)
1. La cuenta @xb.architecture tiene que ser **profesional** (Empresa o Creador).
2. developers.facebook.com → **Create app** → caso de uso **"Manage messaging & content on Instagram"** (API de Instagram con inicio de sesión de Instagram).
3. En **API setup with Instagram login** → **Add account** → loguear @xb.architecture → **Generate token**. Permisos: `instagram_business_basic` e `instagram_business_manage_insights`.
4. Copiá el **token** y el **Instagram user ID** a `IG_ACCESS_TOKEN` / `IG_USER_ID`, y poné `IG_GRAPH_HOST = "https://graph.instagram.com/v23.0"`.
5. El token dura 60 días: anotá en el calendario renovarlo (se regenera en el mismo lugar).

### LinkedIn página XB
1. linkedin.com/developers → **Create app** → asociala a la página de XB Architecture (un admin de la página tiene que aprobar).
2. **Products → Community Management API** → solicitar acceso (LinkedIn revisa el pedido; puede tardar días o semanas).
3. Con el acceso: generá un token con `r_organization_social` y `rw_organization_admin` (Auth → OAuth 2.0 tools).
4. `LI_ORG_ID` = el número que aparece en la URL de admin de la página (`linkedin.com/company/12345678/admin`).

### LinkedIn John y Ximena (perfiles personales)
LinkedIn **restringe** leer métricas de perfiles personales por API (solo apps aprobadas para Community Management). Mientras tanto:
- En LinkedIn: **Yo → Posts y actividad → Analytics → Exportar** → armá un CSV con `account, published_at, permalink, caption, likes, comments, views` (account = `li_john` o `li_ximena`) y subilo en **Reports → Add metrics manually or via CSV**. Toma 2 minutos por semana.
- Si les aprueban el acceso, cargan `LI_JOHN_PERSON_ID` / `LI_JOHN_TOKEN` y pasa a ser automático.

### Sincronización diaria con GitHub Actions
Repo → **Settings → Secrets and variables → Actions → New repository secret**: cargá `DATABASE_URL` y las credenciales de las cuentas (mismos nombres). Probalo en **Actions → Sync métricas redes → Run workflow**.

---

## Personalizar
- **Logo**: está dibujado en `config.py` (`LOGO_SVG`). Podés reemplazarlo por el SVG oficial.
- **Pilares, formatos, estados, cuentas de inspiración**: listas en `config.py` (valores en inglés); sus traducciones al español están en `i18n.py`. Si agregás uno, sumá su traducción ahí.
- **Textos de la app**: cada texto está escrito como `t("English", "Español")` en `app.py`.
- **Frecuencia de auto-sync**: variable `SYNC_EVERY_HOURS` (por defecto 6).

## Problemas comunes
| Síntoma | Solución |
|---|---|
| "Falta la clave de IA" | Revisar secrets (local: `.streamlit/secrets.toml`; nube: Settings → Secrets) |
| Los datos se borran en la nube | Falta `DATABASE_URL` → está usando SQLite temporal |
| Instagram "error: 400/190" en Accounts | Token vencido o host incorrecto (`graph.instagram.com` vs `graph.facebook.com`) |
| LinkedIn "error: 403" | La app todavía no tiene aprobado Community Management API |
| La app "se duerme" | Streamlit Cloud gratuito la pausa sin uso; se despierta con un clic |
