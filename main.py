import asyncio
import os

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

app = FastAPI()

MUESTRAS_POR_SEGUNDO = 16000
BYTES_POR_MUESTRA = 2  # PCM de 16 bits
SEGUNDOS_ENTRE_PASADAS = 1.0
MARGEN_PARA_FIJAR = 1.5  # un segmento se fija si termina al menos este tiempo antes del final
SEGUNDOS_MAXIMOS = 20.0  # con más audio que esto se fija todo, para que cada pasada no tarde más

nombre_modelo = os.environ.get("MODELO_WHISPER", "base")
# "auto" usa la GPU NVIDIA si el contenedor la ve y si no, la CPU. int8 funciona en ambas (y en GPU Pascal)
dispositivo = os.environ.get("DISPOSITIVO", "auto")
modelo = WhisperModel(f"modelos/faster-whisper-{nombre_modelo}", device=dispositivo, compute_type="int8")
print(f"Modelo {nombre_modelo} cargado en {modelo.model.device}")


# --- Transcripción: Whisper no es continuo, así que se repasa el audio reciente cada segundo ---
def transcribir(muestras: bytes):
    audio = np.frombuffer(muestras, dtype=np.int16).astype(np.float32) / 32768
    segmentos, _ = modelo.transcribe(
        audio,
        language="es",
        beam_size=1,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    return list(segmentos)


def separar(segmentos, duracion: float, terminar: bool):
    """Devuelve el texto fijo, el provisional y los segundos de audio que ya se pueden descartar."""
    if terminar or duracion >= SEGUNDOS_MAXIMOS:
        fijos, parciales = segmentos, []
        corte = duracion
    else:
        fijos = [s for s in segmentos if s.end <= duracion - MARGEN_PARA_FIJAR]
        parciales = segmentos[len(fijos):]
        corte = fijos[-1].end if fijos else 0.0
        if not segmentos:  # solo silencio: se conserva lo último por si empieza una palabra
            corte = max(0.0, duracion - MARGEN_PARA_FIJAR)
    return "".join(s.text for s in fijos), "".join(s.text for s in parciales), corte


@app.websocket("/transcribir")
async def transcribir_ws(websocket: WebSocket):
    await websocket.accept()
    audio = bytearray()

    # Devuelve True si el cliente pidió terminar y False si se desconectó
    async def recibir():
        while True:
            mensaje = await websocket.receive()
            if mensaje["type"] == "websocket.disconnect":
                return False
            if mensaje.get("bytes"):
                audio.extend(mensaje["bytes"])
            elif mensaje.get("text") == "fin":
                return True

    async def pasada(terminar: bool = False):
        muestras = bytes(audio)
        duracion = len(muestras) / BYTES_POR_MUESTRA / MUESTRAS_POR_SEGUNDO
        # En un hilo aparte, para seguir recibiendo audio mientras Whisper trabaja
        segmentos = await asyncio.to_thread(transcribir, muestras)
        fijo, parcial, corte = separar(segmentos, duracion, terminar)
        del audio[: int(corte * MUESTRAS_POR_SEGUNDO) * BYTES_POR_MUESTRA]
        await websocket.send_json({"fijo": fijo, "parcial": parcial})

    receptor = asyncio.create_task(recibir())
    try:
        while True:
            await asyncio.wait({receptor}, timeout=SEGUNDOS_ENTRE_PASADAS)
            if receptor.done():
                break
            if audio:
                await pasada()
        if receptor.result():
            await pasada(terminar=True)
            await websocket.close()
    except WebSocketDisconnect:
        print("Cliente desconectado")
    finally:
        receptor.cancel()
