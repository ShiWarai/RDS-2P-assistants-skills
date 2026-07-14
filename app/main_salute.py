"""
FastAPI entrypoint: навык Salute.
"""
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.api.common_routes import router as common_router
from app.platforms.salute.routes import router as salute_router

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

file_handler = logging.FileHandler(log_dir / "salute.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])

app = FastAPI(title="Robot Panda Salute API", version="1.0.0")
app.include_router(common_router)
app.include_router(salute_router)


@app.get("/v1/", include_in_schema=False)
async def salute_root():
    return {"status": "ok", "message": "Salute API is running"}


if __name__ == "__main__":
    uvicorn.run("app.main_salute:app", host="0.0.0.0", port=8000, reload=True)
