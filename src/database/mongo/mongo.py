from typing import Optional
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config import mongo_cfg


# ---------- 连接与断开 ----------
async def connect_db(
    uri: Optional[str] = None,
    db_name: Optional[str] = None,
    models: Optional[list] = None,
):
    """
    使用 Beanie (Motor) 连接 MongoDB。
    Args:
        uri: 可选的 MongoDB URI
        db_name: 数据库名
        models: 要注册的 Document 类列表，如 [FileRecord]
    """
    if uri is None:
        uri = mongo_cfg["uri"]
    if db_name is None:
        db_name = mongo_cfg["db_name"]

    client = AsyncIOMotorClient(uri)
    await init_beanie(database=client[db_name], document_models=models or [])  # type: ignore
    return client


async def disconnect_db(client: AsyncIOMotorClient):
    """关闭 Mongo 连接"""
    client.close()
