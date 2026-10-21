#!/bin/bash
# XB Content Studio · arranque automático para Mac
# Uso: abrir Terminal, escribir "bash " (con espacio), arrastrar este archivo a la ventana y apretar Enter.

clear
echo ""
echo "  ◼▣  XB ARCHITECTURE · CONTENT STUDIO"
echo "  ------------------------------------"
echo ""

# 1) Encontrar la carpeta del proyecto
HERE="$(cd "$(dirname "$0")" && pwd)"
for d in "$HERE" "$HOME/Desktop/xb-content-studio" "$HOME/Downloads/xb-content-studio" \
         "$HOME/Escritorio/xb-content-studio" "$HOME/Descargas/xb-content-studio"; do
  if [ -f "$d/app.py" ]; then PROJECT="$d"; break; fi
done
if [ -z "$PROJECT" ]; then
  echo "  ✗ No encuentro la carpeta xb-content-studio."
  echo "    Poné este archivo ADENTRO de la carpeta xb-content-studio y probá de nuevo."
  exit 1
fi
cd "$PROJECT" || exit 1
echo "  ✓ Carpeta del proyecto: $PROJECT"

# 2) Revisar que Python esté instalado
if ! command -v python3 >/dev/null 2>&1; then
  echo "  ✗ No encuentro Python. Instalalo desde python.org/downloads y volvé a correr esto."
  exit 1
fi
echo "  ✓ Python: $(python3 --version)"

# 3) Preparar el entorno (solo tarda la primera vez)
if [ ! -d ".venv" ]; then
  echo "  … Preparando todo por primera vez (puede tardar 1-3 minutos)…"
  python3 -m venv .venv || { echo "  ✗ No pude crear el entorno de Python."; exit 1; }
fi
source .venv/bin/activate
pip install -q --disable-pip-version-check -r requirements.txt || {
  echo "  ✗ Falló la instalación. Revisá tu conexión a internet y probá de nuevo."; exit 1; }
echo "  ✓ Todo instalado"

# 4) Clave de la IA (solo la primera vez)
if [ ! -f ".streamlit/secrets.toml" ]; then
  echo ""
  echo "  Pegá tu clave gratis de Google Gemini (empieza con AQ. o AIza) y apretá Enter."
  echo "  Si todavía no la tenés, apretá Enter igual: la app anda, solo sin la IA."
  printf "  Clave: "
  read -r KEY
  mkdir -p .streamlit
  {
    echo "# Archivo de claves local (NO subir a GitHub)"
    echo "GEMINI_API_KEY = \"$KEY\""
  } > .streamlit/secrets.toml
  echo "  ✓ Guardado. Para cambiar la clave después: borrá el archivo .streamlit/secrets.toml y corré esto de nuevo."
fi

# 5) Abrir la app (sin la pregunta de email de Streamlit)
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
  mkdir -p "$HOME/.streamlit"
  printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi
echo ""
echo "  ✓ Abriendo la app en tu navegador…"
echo "  (Para apagarla: volvé a esta ventana y apretá Control + C)"
echo ""
python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
