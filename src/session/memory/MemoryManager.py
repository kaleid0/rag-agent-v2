import os
from typing import Protocol

# from llm.Message import Messages
from .LongTermMemory import LongTermMemory
from src.session import Session
from src.prompt import llm_call
from src.llm import BaseChatAdapter
from src.rag import ingest_memory, RetrievePipelineProtocol
from src.database import delete_content_from_collection
from config import memory_cfg

# from .llm_call import memory_merge, memory_summary


class MemoryManager:

    def __init__(
        self,
        llm_adapter: BaseChatAdapter,
        short_term_memory_period: int = 10,
        retrieve_pipeline: RetrievePipelineProtocol | None = None,
    ) -> None:
        self.llm_adapter = llm_adapter
        self.short_term_memory_period = short_term_memory_period
        self.retrieve_pipeline = retrieve_pipeline

    def should_update_short_term_memory(self, session: Session) -> bool:
        return (
            session.message_count - session.last_summary_count
            == self.short_term_memory_period * 2
        )

    async def update_short_term_memory(self, session: Session):
        new_messages = session.get_history(
            start_rev_index=session.last_summary_count + 1,
            end_rev_index=session.message_count - self.short_term_memory_period,
        )

        new_memory = await llm_call(
            prompt_name="short_term_memory_summary",
            llm=self.llm_adapter,
            args={"messages": new_messages},
        )
        if len(session.memory) > 0:
            new_memory = await llm_call(
                prompt_name="memory_merge",
                llm=self.llm_adapter,
                args={
                    "existing_summary": session.memory,
                    "new_summary": new_memory,
                },
            )

        session.memory = new_memory
        session.last_summary_count = (
            session.message_count - self.short_term_memory_period
        )
        await session.save_changes()

    async def update_long_term_memory(self, session: Session):
        history = session.messages
        long_term_memory = await LongTermMemory.find_one(
            LongTermMemory.user_id == session.user_id
        )

        new_memory = await llm_call(
            prompt_name="long_term_memory_summary",
            llm=self.llm_adapter,
            args={"messages": str(history)},
        )
        if long_term_memory and len(long_term_memory.memory) > 0:
            new_memory = await llm_call(
                prompt_name="memory_merge",
                llm=self.llm_adapter,
                args={
                    "existing_summary": long_term_memory.memory,
                    "new_summary": new_memory,
                },
            )

        session.set_long_term_memory(new_memory)

    async def ingest_memory_to_rag(self, session: Session):
        if session.user_id is None:
            return
        history = session.get_history()
        chunk_save_path = os.path.join(
            memory_cfg["chunk_dir"], session.user_id + ".pkl"
        )
        ingest_memory(
            user_id=session.user_id,
            messages=history,
            chunk_save_path=chunk_save_path,
            session_id=str(session.id),
        )

    async def retrieve_memory_from_rag(self, query: str, session: Session) -> str:
        if not self.retrieve_pipeline or not session.user_id:
            return ""

        retrieved_memories = await self.retrieve_pipeline.retrieve_memory(
            query=query,
            user_id=session.user_id,
        )

        session.set_retrieved_memory(retrieved_memories)

        return retrieved_memories

    async def delete_memory_from_rag(self, user_id: str, session: Session):
        delete_content_from_collection(
            name=user_id, metadata={"session_id": str(session.id)}
        )

    async def memory_assemble(
        self,
    ): ...
