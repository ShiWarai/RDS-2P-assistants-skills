"""
Entrypoint robot-gateway: только gRPC, без HTTP.
"""
import logging
import sys
from pathlib import Path

# Корень репозитория в PYTHONPATH
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from gateway.server import serve  # noqa: E402

if __name__ == "__main__":
    serve()
