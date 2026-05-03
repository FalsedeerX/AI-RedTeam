import uuid
import asyncio
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response

app = FastAPI()

# Store active agent connection
agent_ws: WebSocket | None = None

# Pending requests (id -> future)
pending = {}


@app.websocket("/relay")
async def agent_socket(ws: WebSocket):
    global agent_ws
    await ws.accept()
    agent_ws = ws
    print("[+] Agent connected")

    try:
        while True:
            data = await ws.receive_json()
            req_id = data["id"]

            if req_id in pending:
                pending[req_id].set_result(data)
    except:
        print("[-] Agent disconnected")
        agent_ws = None


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    global agent_ws

    if agent_ws is None:
        return Response("No agent connected", status_code=503)

    body = await request.body()

    req_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    fut = loop.create_future()

    pending[req_id] = fut

    await agent_ws.send_json({
        "id": req_id,
        "method": request.method,
        "path": "/" + path,
        "headers": dict(request.headers),
        "body": body.decode("utf-8", errors="ignore"),
    })

    result = await fut
    del pending[req_id]

    return Response(
        content=result["body"].encode(),
        status_code=result["status"],
        headers=result["headers"],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "relay:app",
        host="127.0.0.1",
        port=5000,
        reload=True   # optional (auto-restart on changes)
    )
