# voz-ai-lab

Escribe lo que dices mientras hablas, con `faster-whisper` en la CPU y sin enviar el audio fuera de tu equipo.

El primer experimento, de HTTP, SSE y WebSocket, está en [sse-websocket/](sse-websocket/README.md).

## Requisitos

- Python 3.12 (es la versión con la que se probó)
- `curl`, para descargar el modelo

## Instalación

Desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sh entrypoint.sh
```

`entrypoint.sh` descarga con `curl` los archivos del modelo que falten en `modelos/faster-whisper-base`. Si ya están, no hace nada.

También puedes descargarlo a mano:

```bash
mkdir -p modelos/faster-whisper-base && cd modelos/faster-whisper-base
for archivo in config.json model.bin tokenizer.json vocabulary.txt; do
  curl -fL -o "$archivo" "https://huggingface.co/Systran/faster-whisper-base/resolve/main/$archivo"
done
```

## Levantar el proyecto

Son dos partes independientes, cada una en su terminal: la página no sabe de FastAPI, y FastAPI solo ofrece el WebSocket `/transcribir`.

**Backend**, desde la raíz del proyecto, porque el modelo se busca con una ruta relativa:

```bash
source .venv/bin/activate
uvicorn main:app --port 8766
```

**Frontend**: cualquier servidor de archivos estáticos sirve. Por ejemplo, el que trae Python, que no necesita el entorno virtual:

```bash
python3 -m http.server 8767 --bind 127.0.0.1 --directory frontend
```

Abre <http://127.0.0.1:8767/>, pulsa **Empezar** y permite el micrófono. El texto en gris es provisional y puede cambiar; el negro ya queda fijo. La barra debe moverse cuando hablas.

Usa esa dirección tal cual: el navegador solo da acceso al micrófono sin HTTPS en `127.0.0.1` o `localhost`.

La dirección del backend está en la constante `URL_BACKEND` de `frontend/index.html`. Cámbiala si lo mueves a otro puerto o a otra máquina.

La página carga React desde un CDN (`esm.sh`), así que necesita internet para abrirse. El audio no sale de tu equipo: la transcripción sigue siendo local.

Para detener cada parte, pulsa `Ctrl+C` en su terminal.

## Usar otro modelo

Los modelos se guardan en `modelos/`, cada uno en una carpeta con su nombre. Para usar otro (`tiny`, `small`, `medium`...):

```bash
export MODELO_WHISPER=small
sh entrypoint.sh
uvicorn main:app --port 8766
```

Un modelo más grande es más preciso, pero más lento.

## Con Docker (opcional)

No hace falta Python ni `.venv`. Crea la carpeta antes de arrancar: si no existe, Docker la crea como root y la descarga falla por permisos. No lo levantes a la vez que los comandos de arriba, porque usan los mismos puertos.

```bash
mkdir -p modelos
docker compose up -d --build   # los dos: voz (backend) y web (frontend)
docker compose up -d voz       # solo uno de ellos
docker compose logs -f         # ver qué está pasando
docker compose down            # detenerlos (el modelo se conserva)
```

La página queda en <http://127.0.0.1:8767/>, servida por nginx.

El modelo se elige con `MODELO_WHISPER` en `compose.yaml`, y el `user: "1000:1000"` debe coincidir con tu usuario (compruébalo con `id -u` e `id -g`). Si cambias el código o el modelo, vuelve a ejecutar `docker compose up -d --build`.

## Problemas comunes

| Síntoma                                       | Causa probable                                                  |
|-----------------------------------------------|-----------------------------------------------------------------|
| `ModuleNotFoundError`                         | El entorno virtual no está activado                             |
| Error al cargar el modelo al arrancar         | Falta ejecutar `sh entrypoint.sh`, o no estás en la raíz        |
| `address already in use`                      | Ya hay algo en el puerto 8766 u 8767, quizá los contenedores    |
| "Sin conexión con el backend"                 | El backend no está levantado o sigue cargando el modelo         |
| La barra no se mueve                          | El navegador no tiene permiso o está usando otro micrófono      |
