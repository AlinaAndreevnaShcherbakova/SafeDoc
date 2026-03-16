from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_superadmin
from app.core.config import settings
from app.models import User

router = APIRouter()


@router.get("/tail")
async def tail_audit(
    lines: int = Query(100, ge=1, le=1000),
    _: User = Depends(require_superadmin),
) -> dict:
    logs_dir = Path(settings.logs_dir)
    if not logs_dir.exists():
        return {"lines": []}

    files = sorted(logs_dir.glob("Logs *.jsonl"))
    if not files:
        return {"lines": []}

    latest = files[-1]
    try:
        content = latest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return {"file": latest.name, "lines": content[-lines:]}

