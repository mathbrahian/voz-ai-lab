#!/bin/sh
# Descarga a ./modelos los archivos del modelo que falten y ejecuta lo que se le pase (si se le pasa algo)
set -e

NOMBRE="faster-whisper-${MODELO_WHISPER:-base}"
CARPETA="modelos/$NOMBRE"
URL="https://huggingface.co/Systran/$NOMBRE/resolve/main"

mkdir -p "$CARPETA"
for archivo in config.json model.bin tokenizer.json vocabulary.txt; do
  if [ ! -f "$CARPETA/$archivo" ]; then
    echo "Descargando $NOMBRE/$archivo"
    # Primero a .tmp: si la descarga se corta, no queda un archivo a medias
    curl -fL --retry 3 -o "$CARPETA/$archivo.tmp" "$URL/$archivo"
    mv "$CARPETA/$archivo.tmp" "$CARPETA/$archivo"
  fi
done

exec "$@"
