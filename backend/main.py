from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from routes.patients import router as patients_router
from services.storage import storage
from watcher import watcher


@asynccontextmanager
async def lifespan(_: FastAPI):
    watcher.start()
    try:
        yield
    finally:
        watcher.stop()


app = FastAPI(title="RA PACS AI Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(patients_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ra-pacs-backend"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = storage.register_connection()
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        storage.unregister_connection(queue)
