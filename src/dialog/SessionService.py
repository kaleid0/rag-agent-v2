from fastapi import HTTPException
from .DialogManager import DialogManager
from .odm.Session import Session


class SessionService:
    def __init__(self, dialog_manager: DialogManager):
        self.dialog_manager = dialog_manager

    async def create_session(
        self, user_id: str, metadata: dict | None = None
    ) -> Session:
        session = Session(user_id=user_id, metadata=metadata or {})
        await session.insert()
        if session.id is None:
            raise RuntimeError("Failed to create session - ID is None")
        return session

    async def delete_session(self, session_id: str):
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
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

        token_stream = await self.dialog_manager.generate_response_stream(
            session=session,
            message_content=content,
            message_metadata=metadata,
            knowledge_base_id=kb_id,
        )
        return token_stream

    async def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session.messages

    async def get_messages(
        self, session_id: str, offset: int = 0, limit: int = 20
    ) -> list[dict[str, str]]:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session.messages[offset : offset + limit]

    async def list_sessions(
        self, user_id: str, offset: int = 0, limit: int = 20
    ) -> list[Session]:
        sessions = (
            await Session.find(Session.user_id == user_id)
            .sort(Session.created_at)  # type: ignore
            .to_list()
        )
        return sessions
