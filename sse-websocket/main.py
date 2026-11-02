import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI()


# --- Página para probar SSE y WebSocket desde el navegador ---
@app.get("/")
def inicio():
    return FileResponse("index.html")


# --- HTTP normal: una petición, una respuesta ---
@app.get("/health")
def health():
    return {"status": "ok"}


# --- SSE: el cliente pide una vez, el servidor envía muchos eventos ---
async def generar_tokens(pregunta: str):
    for palabra in f"Respuesta simulada a: {pregunta}".split():
        yield f"data: {palabra}\n\n"  # formato SSE: "data: ...\n\n"
        await asyncio.sleep(0.3)
    yield "event: fin\ndata: listo\n\n"


@app.get("/sse")
async def sse(pregunta: str = "hola"):
    return StreamingResponse(generar_tokens(pregunta), media_type="text/event-stream")


# --- WebSocket: canal abierto, ambos lados envían cuando quieran ---
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            mensaje = await websocket.receive_text()
            await websocket.send_text(f"Recibí: {mensaje}")
    except WebSocketDisconnect:
        print("Cliente desconectado")
