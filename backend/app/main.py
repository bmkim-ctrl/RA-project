from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.worklist import router as worklist_router
from .services.worklist_service import worklist_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    worklist_service.start()
    try:
        yield
    finally:
        worklist_service.stop()


app = FastAPI(title="RA PACS Worklist", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(worklist_router)
