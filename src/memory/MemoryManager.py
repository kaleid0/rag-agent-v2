from typing import Protocol

# from llm.Message import Messages
from .Memory import ShortTermMemory, LongTermMemory, Memory

# from .llm_call import memory_merge, memory_summary


# TODO: 1. 重构 MemoryManager 类，持久化类为Memory
#       2. 不需要状态的接口，不需要封装为类；但是为了后续设置不同的MemoryManager，使用鸭子类型Protocol
#       3. MemoryManager 负责管理记忆的保存与检索逻辑
# DialogManager（业务层） -> Session（数据层）
# DialogManager（业务层） -> MemoryManager（业务层） -› Memory（数据层）
class MemoryManager(Protocol):
    async def update_short_term_memory(
        self,
        Memory: ShortTermMemory,
        session_id: str,
        messages: list[dict[str, str]],
    ) -> ShortTermMemory: ...

    async def update_long_term_memory(self, session_id: str) -> LongTermMemory: ...

    async def should_update_short_term_memory(self, session_id: str) -> bool: ...

    async def ingest_memory_to_rag(self, session_id: str, memory: Memory): ...

    async def retrieve_memory_from_rag(
        self, session_id: str, query: str
    ) -> list[Memory]: ...

    async def memory_assemble(
        self,
        short_term_memory: Memory | None = None,
        long_term_memory: Memory | None = None,
        retrieved_memory: Memory | None = None,
    ) -> Memory: ...
