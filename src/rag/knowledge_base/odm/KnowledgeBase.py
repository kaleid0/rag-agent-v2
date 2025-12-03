from pydantic import Field
from pymongo import DESCENDING

# from beanie import PydanticObjectId

from src.database.mongo.BaseDocument import BaseDocument


class KnowledgeBase(BaseDocument):
    """存储知识库信息"""

    name: str = Field(..., unique=True)  # type: ignore # 知识库名称，唯一
    description: str = Field(default="")  # 知识库描述
    chunk_size: int = Field(default=300)  # 知识库文本块大小
    chunk_overlap: int = Field(default=50)  # 知识库文本块重叠大小
    split_method: str = Field(
        default="hierarchical"
    )  # 文本拆分方法 hierarchical, recursive
    retriever_type: str = Field(default="hybrid")  # 检索器类型 vector, sparse, hybrid
    document_record_ids: list[str] = Field(default=[])
    document_titles: list[str] = Field(default=[])

    class Settings:
        name = "knowledge_base"  # MongoDB 集合名
        indexes = [[("created_at", DESCENDING)]]
        use_state_management = True
