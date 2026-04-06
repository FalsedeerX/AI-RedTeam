import asyncio
import websockets
import httpx
import json

RELAY_URL = "ws://your-relay-server:8000/ws"
OLLAMA_URL = "http://127.0.0.1:11434"


async def handle():
    async with websockets.connect(RELAY_URL) as ws:
        print("[+] Connected to relay")

        async for msg in ws:
            data = json.loads(msg)

            req_id = data["id"]
            method = data["method"]
            path = data["path"]
            headers = data["headers"]
            body = data["body"]

            try:
                async with httpx.AsyncClient(timeout=300) as client:
                    resp = await client.request(
                        method,
                        OLLAMA_URL + path,
                        headers=headers,
                        content=body.encode(),
                    )

                await ws.send(json.dumps({
                    "id": req_id,
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text,
                }))

            except Exception as e:
                await ws.send(json.dumps({
                    "id": req_id,
                    "status": 500,
                    "headers": {},
                    "body": str(e),
                }))


asyncio.run(handle())
