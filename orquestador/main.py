import asyncio
import json
import os

import httpx
import websockets
from fastapi import FastAPI, WebSocket

app = FastAPI()

URL_VOZ = os.environ.get("URL_VOZ", "ws://127.0.0.1:8766/transcribir")
URL_OLLAMA = os.environ.get("URL_OLLAMA", "http://127.0.0.1:11434")
MODELO_LLM = os.environ.get("MODELO_LLM", "qwen2.5:3b")


# --- Ollama: responde por HTTP, una línea de JSON por cada parte del texto ---
async def preguntar_a_ollama(historial: list[dict]):
    cuerpo = {"model": MODELO_LLM, "messages": historial, "stream": True}
    # Sin límite de lectura: la primera pregunta espera a que el modelo cargue en memoria
    async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5)) as cliente:
        async with cliente.stream("POST", f"{URL_OLLAMA}/api/chat", json=cuerpo) as respuesta:
            respuesta.raise_for_status()
            async for linea in respuesta.aiter_lines():
                yield json.loads(linea)["message"]["content"]


@app.websocket("/conversar")
async def conversar(pagina: WebSocket):
    await pagina.accept()
    preguntas = asyncio.Queue()  # si hablas mientras responde, la frase espera su turno
    historial = []  # dura lo que dura esta conexión

    # De la página a Voz. Devuelve True si la página pidió terminar y False si se desconectó
    async def subir_audio(voz):
        while True:
            mensaje = await pagina.receive()
            if mensaje["type"] == "websocket.disconnect":
                return False
            if mensaje.get("bytes"):
                await voz.send(mensaje["bytes"])
            elif mensaje.get("text") == "fin":
                await voz.send("fin")
                return True

    # De Voz a la página, separando las preguntas
    async def bajar_texto(voz):
        pregunta = ""
        numero = 0

        async def enviar_pregunta():
            nonlocal pregunta, numero
            await pagina.send_json({"tipo": "pregunta", "numero": numero, "texto": pregunta.strip()})
            await preguntas.put((numero, pregunta.strip()))
            pregunta = ""
            numero += 1

        async for mensaje in voz:
            datos = json.loads(mensaje)
            pregunta += datos["fijo"]
            await pagina.send_json({"tipo": "transcripcion", "fijo": datos["fijo"], "parcial": datos["parcial"]})
            # Voz solo fija un texto tras 1,5 s de silencio: fijo y sin provisional es que terminaste la frase
            if pregunta.strip() and not datos["parcial"]:
                await enviar_pregunta()
        if pregunta.strip():
            await enviar_pregunta()

    async def responder():
        while (siguiente := await preguntas.get()) is not None:  # None: no vendrán más preguntas
            numero, pregunta = siguiente
            historial.append({"role": "user", "content": pregunta})
            respuesta = ""
            try:
                async for parte in preguntar_a_ollama(historial):
                    respuesta += parte
                    await pagina.send_json({"tipo": "respuesta", "numero": numero, "texto": parte})
                historial.append({"role": "assistant", "content": respuesta})
            except (httpx.HTTPError, KeyError) as error:
                historial.pop()  # una pregunta sin respuesta no debe quedar en el historial
                await pagina.send_json({"tipo": "error", "texto": f"Sin respuesta de Ollama: {error!r}"})

    tareas = []
    try:
        async with websockets.connect(URL_VOZ) as voz:
            subida = asyncio.create_task(subir_audio(voz))
            bajada = asyncio.create_task(bajar_texto(voz))
            respuestas = asyncio.create_task(responder())
            tareas = [subida, bajada, respuestas]

            await asyncio.wait({subida, bajada}, return_when=asyncio.FIRST_COMPLETED)
            if subida.done() and not subida.result():
                return  # se cerró la página: no hay a quién responderle
            if not subida.done():
                bajada.result()
                raise OSError("Voz cerró la conexión sin que se lo pidieran")

            await bajada  # el último texto de Voz
            await preguntas.put(None)
            await respuestas  # y las respuestas pendientes
            await pagina.close()
    except (OSError, websockets.WebSocketException) as error:
        print(f"Sin conexión con Voz: {error!r}")
        await pagina.send_json({"tipo": "error", "texto": "Sin conexión con el servicio de voz."})
        await pagina.close()
    finally:
        for tarea in tareas:
            tarea.cancel()
