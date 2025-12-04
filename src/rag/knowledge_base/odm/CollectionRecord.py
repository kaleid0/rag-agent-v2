import os
import shutil

from beanie import Delete, before_event
from pydantic import Field
from pymongo import DESCENDING, ASCENDING

from src.database import BaseDocument, delete_collection


# 数据库设计
# KnowledgeBase -> [CollectionRecord ...]
# DocumentRecord -> [CollectionRecord ...]
class CollectionRecord(BaseDocument):
    """知识库中的集合记录信息，一个集合记录对应一个文档记录"""

    chunk_path: str = Field(default="")
    num_chunks: int = Field(default=0)

    document_record_id: str = Field(...)  # 关联的文档记录ID
    knowledge_base_id: str = Field(...)  # 关联的知识库ID

    class Settings:
        name = "collection_record"  # MongoDB 集合名
        indexes = [
            [("created_at", DESCENDING)],  # 单字段索引 (列表格式)
            # **唯一复合索引：** 复合字段列表 + 选项字典
            [
                ("document_record_id", ASCENDING),  # 字段 1
                ("knowledge_base_id", ASCENDING),  # 字段 2
            ],
            [("knowledge_base_id", ASCENDING)],
            [("document_record_id", ASCENDING)],
        ]
        use_state_management = True

    @before_event([Delete])
    async def clean_up_chunks(self):
        if os.path.exists(self.chunk_path):
            shutil.rmtree(self.chunk_path)

    @before_event([Delete])
    async def clean_up_chroma(self):
        delete_collection(str(self.id))
