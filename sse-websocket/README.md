# sse-websocket

Servidor FastAPI mínimo para comparar tres formas de comunicación entre cliente y servidor:

| Ruta      | Tipo         | Qué hace                                                    |
|-----------|--------------|-------------------------------------------------------------|
| `/`       | HTTP         | Sirve `index.html`, la página de prueba para el navegador   |
| `/health` | HTTP         | Una petición, una respuesta: `{"status": "ok"}`             |
| `/sse`    | SSE          | Envía una respuesta simulada palabra por palabra            |
| `/ws`     | WebSocket    | Canal abierto: devuelve cada mensaje como `Recibí: <texto>` |

## Requisitos

Python 3.12 (es la versión con la que se probó).

## Instalación

Desde esta carpeta:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Levantar el servidor

Desde esta carpeta, porque `index.html` se busca con una ruta relativa:

```bash
uvicorn main:app --port 8765
```

Usa el puerto 8765: `probar.py` lo tiene fijo en el código y el puerto por defecto de uvicorn es otro (8000).

Deja esta terminal abierta y usa otra para las pruebas, con el entorno activado (`source .venv/bin/activate`). Para detener el servidor, pulsa `Ctrl+C`.

## Probar

### Opción 1: script automático

```bash
python probar.py
```

Prueba las tres rutas de API y tarda unos 2 segundos. La salida esperada es:

```text
HTTP: {'status': 'ok'}
SSE content-type: text/event-stream; charset=utf-8
SSE: data: Respuesta
SSE: data: simulada
SSE: data: a:
SSE: data: qué
SSE: data: es
SSE: data: SSE
SSE: event: fin
SSE: data: listo
WS: Recibí: uno
WS: Recibí: dos
```

El script solo imprime lo que recibe, no comprueba nada: compara tú la salida con la de arriba.

### Opción 2: navegador

Abre <http://127.0.0.1:8765/>.

- **SSE:** pulsa **Preguntar**. La respuesta debe aparecer palabra por palabra, no de golpe.
- **WebSocket:** debe mostrar `Conectado` al cargar la página. Pulsa **Enviar** y debe aparecer `Recibí: hola`. Si detienes el servidor, debe mostrar `Desconectado`.

### Opción 3: curl

```bash
curl http://127.0.0.1:8765/health
curl -N "http://127.0.0.1:8765/sse?pregunta=hola"
```

`-N` desactiva el búfer de curl para ver los eventos a medida que llegan. curl no sirve aquí para probar `/ws`; usa `probar.py` o el navegador.

## Problemas comunes

| Síntoma                                           | Causa probable                                             |
|---------------------------------------------------|------------------------------------------------------------|
| `probar.py` falla con `httpx.ConnectError`        | El servidor no está levantado o no está en el puerto 8765  |
| `ModuleNotFoundError`                             | El entorno virtual no está activado                        |
| `/` da error 500, pero `/health` funciona         | Iniciaste uvicorn desde otra carpeta y no halla `index.html` |
