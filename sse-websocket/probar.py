import asyncio
import httpx
import websockets


async def main():
    async with httpx.AsyncClient() as c:
        print("HTTP:", (await c.get("http://127.0.0.1:8765/health")).json())
        async with c.stream("GET", "http://127.0.0.1:8765/sse", params={"pregunta": "qué es SSE"}) as r:
            print("SSE content-type:", r.headers["content-type"])
            async for linea in r.aiter_lines():
                if linea:
                    print("SSE:", linea)
    async with websockets.connect("ws://127.0.0.1:8765/ws") as ws:
        for m in ["uno", "dos"]:
            await ws.send(m)
            print("WS:", await ws.recv())


asyncio.run(main())
