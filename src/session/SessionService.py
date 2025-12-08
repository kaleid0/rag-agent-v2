import asyncio
from fastapi import HTTPException

from .dialog.DialogManager import DialogManager
from .odm.Session import Session
from .memory.MemoryManager import MemoryManager
from src.prompt import get_prompt


# SessionService -> DialogManager（业务层） -> Session.messages（数据层）, Session.memory（数据层）
# SessionService -> MemoryManager（业务层） -› Session.memory（数据层）, LongTermMemory (user_id, RAG)
class SessionService:
    def __init__(self, dialog_manager: DialogManager, memory_manager: MemoryManager):
        self.dialog_manager = dialog_manager
        self.memory_manager = memory_manager

    async def create_session(
        self,
        user_id: str,
        system_prompt: str = "default_system_prompt",
        metadata: dict | None = None,
    ) -> Session:
        session = Session(
            user_id=user_id,
            system_prompt=get_prompt(system_prompt, "system"),
            metadata=metadata or {},
        )
        session.set_long_term_memory([])
        session.set_retrieved_memory("")

        await session.insert()
        if session.id is None:
            raise RuntimeError("Failed to create session - ID is None")
        return session

    async def delete_session(self, session_id: str):
        session = await Session.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        await self.memory_manager.delete_memory_from_rag(session_id, session)

        await session.delete()

    async def exit_session(self, session_id: str) -> str:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if (
            not getattr(session, "dialog_messages", None)
            or len(session.dialog_messages) == 0
        ):
            await session.delete()
            return "Session had no messages and was deleted."
        else:
            await asyncio.gather(
                self.memory_manager.update_long_term_memory(session),
                self.memory_manager.ingest_memory_to_rag(session),
                self.dialog_manager.generate_dialog_title(session),
            )
            # await self.memory_manager.update_long_term_memory(session)
            # await self.memory_manager.ingest_memory_to_rag(session)
            # await self.dialog_manager.generate_dialog_title(session)
            return "Session exited successfully."
            # Add any additional cleanup logic if needed

    async def send_message(
        self,
        session_id: str,
        content: str,
        metadata: dict | None = None,
        kb_id: str | None = None,
    ):
        raise NotImplementedError("send_message method is not implemented yet")

    async def send_message_stream(
        self,
        session_id: str,
        content: str,
        metadata: dict | None = None,
        kb_id: str | None = None,
    ):

        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await self.memory_manager.retrieve_memory_from_rag(
            query=content, session=session
        )

        token_stream = await self.dialog_manager.generate_response_stream(
            session=session,
            message_content=content,
            message_metadata=metadata,
            knowledge_base_id=kb_id,
        )

        # 更新记忆
        if self.memory_manager.should_update_short_term_memory(session):
            asyncio.create_task(self.memory_manager.update_short_term_memory(session))

        return token_stream

    async def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session.get_history()

    async def get_messages(
        self, session_id: str, offset: int = 0, limit: int = 20
    ) -> list[dict[str, str]]:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session.get_history(
            start_rev_index=offset + 1, end_rev_index=offset + limit + 1
        )

    async def list_sessions(
        self, user_id: str, offset: int = 0, limit: int = 20
    ) -> list[Session]:
        sessions = (
            await Session.find(Session.user_id == user_id)
            .sort(Session.created_at)  # type: ignore
            .to_list()
        )
        return sessions
