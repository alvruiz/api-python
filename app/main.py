import sys
import types
from pathlib import Path

# Ensure 'app' is recognized as a package whether running from project root or inside container (/code)
_current_dir = Path(__file__).resolve().parent
if _current_dir.name != "app" and "app" not in sys.modules:
    _app_module = types.ModuleType("app")
    _app_module.__path__ = [str(_current_dir)]
    sys.modules["app"] = _app_module

import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from app.adapters.in_memory_repo import InMemoryRequestRepository
from app.adapters.http_ai_client import HttpAiClient
from app.adapters.http_notify_client import HttpNotificationSender
from app.application.request_service import RequestService
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes shared connection pool and wires dependencies (Composition Root).
    """
    logger.info("Initializing application dependencies and connection pool...")
    http_client = httpx.AsyncClient(timeout=10.0)

    repo = InMemoryRequestRepository()
    ai_extractor = HttpAiClient(client=http_client)
    notification_sender = HttpNotificationSender(client=http_client)

    app.state.request_service = RequestService(
        repository=repo,
        ai_extractor=ai_extractor,
        notification_sender=notification_sender,
    )

    yield

    logger.info("Closing application connection pool...")
    await http_client.aclose()


app = FastAPI(
    title="Notification Service (Technical Test)",
    description="Intelligent Notification Service extracting natural language intents with defensive guardrails.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
