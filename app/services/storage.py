from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from gridfs.errors import NoFile

from app.core.config import settings
from app.db import mongo


class StorageService:
    def __init__(self) -> None:
        self.storage_dir = Path(settings.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, filename: str, data: bytes, metadata: dict) -> str:
        if mongo.files_bucket is not None:
            object_id = await mongo.files_bucket.upload_from_stream(filename, data, metadata=metadata)
            return f"mongo://{str(object_id)}"

        key = f"local-{uuid4().hex}-{filename}"
        path = self.storage_dir / key
        path.write_bytes(data)
        return f"local://{key}"

    async def download(self, storage_key: str) -> bytes:
        if storage_key.startswith("mongo://"):
            if mongo.files_bucket is None:
                raise FileNotFoundError("MongoDB недоступна для чтения файла")
            object_id_raw = storage_key.replace("mongo://", "")
            if not ObjectId.is_valid(object_id_raw):
                raise ValueError("Некорректный storage_key для MongoDB")
            object_id = ObjectId(object_id_raw)
            try:
                stream = await mongo.files_bucket.open_download_stream(object_id)
            except NoFile as exc:
                raise FileNotFoundError("Файл в MongoDB не найден") from exc
            return await stream.read()

        key = storage_key.replace("local://", "")
        path = self.storage_dir / key
        if not path.exists():
            raise FileNotFoundError("Локальный файл не найден")
        return path.read_bytes()


storage_service = StorageService()

