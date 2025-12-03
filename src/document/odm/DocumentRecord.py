from typing import Optional
from pydantic import Field
from enum import Enum
from pymongo import DESCENDING
from beanie import Insert, Delete, before_event
from bidict import bidict
from beanie.odm.operators.update.general import Set

from src.database.mongo.BaseDocument import BaseDocument


class StatusEnum(int, Enum):
    pending = 0  # 待处理
    parse_completed = 1  # 解析完成
    completed = 2  # 向量化完成
    failed = -1  # 失败

    # 可根据实际情况添加更多状态


class DocumentRecord(BaseDocument):
    """存储文件解析信息"""

    source: str = Field(default="unknown")  # 文件来源描述
    storage_path: str = Field(...)  # 文件在存储系统中的路径
    markdown_path: str = Field(default="")  # 转换后的 Markdown 文件路径
    chunk_path: str = Field(default="")
    file_hash: str = Field(..., unique=True)  # type: ignore
    num_chunks: int = Field(default=0)
    language: str = Field(default="EN", pattern="^(ZH|EN)$")
    title: str = Field(default="")
    abstract: str = Field(default="")
    keywords: list[str] = Field(default=[])
    directory: list[str] = Field(default=[])
    status: StatusEnum = Field(default=StatusEnum.pending)
    embedding_provider: str = Field(default="default")  # 使用的嵌入服务名称
    embedding_model: str = Field(default="default")  # 使用的嵌入函数名称
    knowledge_base_ids: list[str] = Field(default=[])  # 关联的知识库ID

    class Settings:
        name = "document_record"  # MongoDB 集合名
        indexes = ["file_hash", [("created_at", DESCENDING)]]
        use_state_management = True

    def __str__(self) -> str:
        return f"DocumentRecord(id={self.id}, title={self.title}, status={self.status})"

    @property
    def metadata(self) -> dict:
        return {
            "source": self.source,
            "language": self.language,
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "num_chunks": self.num_chunks,
        }

    # async def update_status(self, new_status: StatusEnum, message: str = ""):
    #     self.status = new_status
    #     if message:
    #         self.error_message = message
    #     await self.update(Set({DocumentRecord.status: new_status}))

    @before_event([Insert])
    async def add_id_title_mapping(self):
        await add_id_title_mapping(str(self.id), self.title)

    @before_event([Delete])
    async def delete_id_title_mapping(self):
        await delete_id_title_mapping(str(self.id), self.title)


async def get_keywords(document_record_id: str) -> list[str]:
    record = await DocumentRecord.get(document_record_id)
    return record.keywords if record and record.keywords else []


# id:title mapping cache
id_title_mapping: Optional[dict[str, str]] = None


async def get_id_title_mapping() -> dict[str, str]:
    global id_title_mapping
    if id_title_mapping is None:
        id_title_mapping = dict()
        records = await DocumentRecord.find_all().to_list()
        for record in records:
            id_title_mapping[str(record.id)] = record.title
    return id_title_mapping


async def id_to_title(id: str) -> str:
    mapping = await get_id_title_mapping()
    return mapping.get(id, "unknown title")


async def add_id_title_mapping(id: str, title: str) -> None:
    global id_title_mapping
    if id_title_mapping is not None:
        id_title_mapping[id] = title


async def delete_id_title_mapping(id: str, title: str) -> None:
    global id_title_mapping
    if id_title_mapping is not None:
        id_title_mapping.pop(id, None)


# To use: id_title_mapping = await build_id_title_mapping()

# 插入示例（异步）
"""
record = FileRecord(
    storage_path=file_path,
    markdown_path=f"rag/database/markdown/{id}.md",
    file_hash=file_hash,
    language="ZH" if contains_chinese(file_path) else "EN",
)
await record.insert()

"""

# 查找示例
"""
record = await FileRecord.find_one(FileRecord.file_hash == "XXX")
if record:
    print("记录已存在:", record)
else:
    print("记录不存在")
"""

# 更新示例
"""
record = await FileRecord.find_one(FileRecord.file_hash == "XXX")
if record:
    record.status = "convert_markdown_completed"
    await record.save_changes()
"""
