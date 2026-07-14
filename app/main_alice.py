"""
FastAPI entrypoint: навык Алисы.
"""
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.api.common_routes import router as common_router
from app.platforms.alice.routes import router as alice_router

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(log_dir / "alice.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

app = FastAPI(title="Robot Panda Alice API", version="1.0.0")
app.include_router(common_router)
app.include_router(alice_router)


@app.get("/v1/", include_in_schema=False)
async def alice_root():
    return {"status": "ok", "message": "Alice API is running"}


if __name__ == "__main__":
    uvicorn.run("app.main_alice:app", host="0.0.0.0", port=8000, reload=True)
