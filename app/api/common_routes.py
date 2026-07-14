"""
Общие маршруты: health, admin.
"""
import ipaddress
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/health")
async def health():
    return {"status": "healthy"}


# root определяется в main_salute / main_alice


def _is_private_client_ip(request: Request) -> bool:
    host = request.client.host if request.client else None
    if not host:
        return False
    if host == "::1":
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def require_local_network(request: Request) -> None:
    if not _is_private_client_ip(request):
        logger.warning(
            "Отклонён доступ к /v1/admin/* с IP: %s",
            getattr(request.client, "host", None),
        )
        raise HTTPException(status_code=403, detail="Access allowed only from local network")


def get_command_feedback_repository():
    from app.application.dependencies import create_command_feedback_repository

    return create_command_feedback_repository()


@router.get("/v1/admin/command-feedback")
async def export_command_feedback(
    request: Request,
    _: None = Depends(require_local_network),
    repo=Depends(get_command_feedback_repository),
) -> JSONResponse:
    try:
        items = repo.get_all_feedback()
        return JSONResponse(
            content=items,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
    except Exception as e:
        logger.error("Ошибка выгрузки command-feedback: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
