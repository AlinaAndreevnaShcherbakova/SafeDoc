from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from app.core.config import settings

client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None
files_bucket: AsyncIOMotorGridFSBucket | None = None
logs_bucket: AsyncIOMotorGridFSBucket | None = None


async def connect_mongo() -> None:
    global client, database, files_bucket, logs_bucket
    client = AsyncIOMotorClient(settings.mongo_url)
    database = client[settings.mongo_db]
    files_bucket = AsyncIOMotorGridFSBucket(database, bucket_name="files")
    logs_bucket = AsyncIOMotorGridFSBucket(database, bucket_name="logs")


async def disconnect_mongo() -> None:
    global client
    if client is not None:
        client.close()
        client = None

