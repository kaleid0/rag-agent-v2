from beanie import PydanticObjectId
from pydantic import Field
from src.database.mongo.BaseDocument import BaseDocument


class Memory(BaseDocument):
    memory: dict = Field(default_factory=dict)
    metadata: dict = {}

    def __init__(self, memory: dict, metadata: dict | None = None):
        self.memory = memory
        self.metadata = metadata or {}


class LongTermMemory(Memory):
    """长期记忆类"""

    user_id: PydanticObjectId | None = Field(...)

    class Settings:
        name = "long_term_memory"  # MongoDB 集合名
        indexes = ["user_id"]
        use_state_management = True


class ShortTermMemory(Memory):
    """短期记忆类"""

    session_id: PydanticObjectId | None = Field(...)

    class Settings:
        name = "short_term_memory"  # MongoDB 集合名
        indexes = ["session_id"]
        use_state_management = True
