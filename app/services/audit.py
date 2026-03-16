import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db import mongo


class AuditService:
    def __init__(self) -> None:
        self.logs_dir = Path(settings.logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.active_file = self.logs_dir / f"Logs {datetime.now(timezone.utc).isoformat().replace(':', '-')}.jsonl"

    async def log_event(
        self,
        event_type: str,
        event_object: str,
        event_subject: str,
        result: str,
        extra: str | None = None,
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "event_object": event_object,
            "event_subject": event_subject,
            "result": result,
            "extra": extra or "",
        }

        line = json.dumps(payload, ensure_ascii=True) + "\n"
        with self.active_file.open("a", encoding="utf-8") as fh:
            fh.write(line)

        if self.active_file.stat().st_size >= 100 * 1024 * 1024:
            await self._rotate_file()

    async def _rotate_file(self) -> None:
        closed_file = self.active_file
        if mongo.logs_bucket is not None and closed_file.exists():
            data = closed_file.read_bytes()
            await mongo.logs_bucket.upload_from_stream(
                closed_file.name,
                data,
                metadata={"created_at": datetime.now(timezone.utc).isoformat(), "size_bytes": len(data)},
            )

        self.active_file = self.logs_dir / f"Logs {datetime.now(timezone.utc).isoformat().replace(':', '-')}.jsonl"


audit_service = AuditService()

