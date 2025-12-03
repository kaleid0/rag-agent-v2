"""聊天相关的 API 路由"""

# import time
from fastapi import APIRouter, BackgroundTasks, HTTPException

# from beanie import PydanticObjectId

from src.api.models import (
    SessionCreateRequest,
    SessionResponse,
    MessageRequest,
    ChatResponse,
    SessionHistoryResponse,
    MessageResponse,
    SuccessResponse,
)
from src.dialog import Session
from src.api.dependencies import get_dialog_manager
from fastapi.responses import StreamingResponse


router = APIRouter()


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(request: SessionCreateRequest):
    """创建新的聊天会话"""
    try:
        manager = await get_dialog_manager()
        session_id = await manager.start_session(
            user_id=request.user_id, metadata=request.metadata
        )

        session = await Session.get(session_id)
        if not session:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve created session"
            )

        return SessionResponse(
            session_id=str(session.id),
            user_id=session.user_id,  # type: ignore
            created_at=session.created_at,
            metadata=session.metadata,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str):
    """获取会话历史"""
    try:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionHistoryResponse(
            session_id=str(session.id),
            user_id=session.user_id,  # type: ignore
            messages=session.messages,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: str):
    """删除会话"""
    try:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        await session.delete()
        return SuccessResponse(message="Session deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@router.post("/sessions/{session_id}/exit", response_model=SuccessResponse)
async def exit_session(session_id: str):
    """退出会话：如果会话没有任何对话消息，则删除之，否则保留并返回信息。"""
    try:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 如果没有任何对话消息，则删除会话
        if (
            not getattr(session, "dialog_messages", None)
            or len(session.dialog_messages) == 0
        ):
            await session.delete()
            return SuccessResponse(message="Empty session deleted")

        return SuccessResponse(message="Session retained (has messages)")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to exit session: {str(e)}")


# XXX
@router.post("/chat", response_model=ChatResponse)
async def send_message(request: MessageRequest):
    """发送消息并获取回复

    这是核心的对话接口，支持基于RAG的智能回复
    """
    try:
        # 获取会话
        session = await Session.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 获取 DialogManager
        manager = await get_dialog_manager()

        # 添加用户消息
        # user_msg = await manager.append_message(
        #     session=session,
        #     role=RoleEnum.user,
        #     content=request.content,
        #     metadata=request.metadata,
        # )

        # 生成助手回复
        kb_id = request.knowledge_base_id if request.knowledge_base_id else None
        assistant_msg = await manager.generate_response(
            session, request.content, request.metadata, knowledge_base_id=kb_id
        )

        # 保存会话
        await session.save()

        return ChatResponse(
            session_id=str(session.id),
            user_message=MessageResponse(
                role="user",
                content=request.content,
                timestamp=None,
                metadata=request.metadata or {},
            ),
            assistant_message=MessageResponse(
                role=assistant_msg.role.value,
                content=assistant_msg.content,
                timestamp=assistant_msg.timestamp,
                metadata=assistant_msg.metadata,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process message: {str(e)}"
        )


@router.post("/chat-stream")
async def send_message_stream(
    request: MessageRequest, background_tasks: BackgroundTasks
):
    """发送消息并获取回复

    这是核心的对话接口，支持基于RAG的智能回复
    """
    try:
        # 获取会话
        session = await Session.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # 获取 DialogManager, MemoryManager
        dialog_manager = await get_dialog_manager()
        # memory_manager = await get_memory_manager()

        # 生成助手回复（流式）
        kb_id = request.knowledge_base_id if request.knowledge_base_id else None
        token_stream = await dialog_manager.generate_response_stream(
            session, request.content, request.metadata, knowledge_base_id=kb_id
        )

        # 保存会话
        # await session.save()

        # 检查是否需要总结短期记忆
        # if await memory_manager.should_summary_short_term_memory(session):
        #     background_tasks.add_task(memory_manager.update_short_term_memory, session)

        return StreamingResponse(token_stream, media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process message: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, limit: int = 50, offset: int = 0):
    """获取会话的消息列表（支持分页）"""
    try:
        session = await Session.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = session.messages[offset : offset + limit]
        return [
            MessageResponse(
                role=msg.get("role", "unknown"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp"),  # type: ignore
                metadata=msg.get("metadata", {}),  # type: ignore
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.get("/session-list", response_model=list[SessionResponse])
async def list_sessions(user_id: str):
    """列出指定用户的所有会话"""
    # start = time.time()
    try:
        sessions = await Session.find(Session.user_id == user_id).sort(Session.created_at).to_list()  # type: ignore

        return [
            SessionResponse(
                session_id=str(session.id),
                user_id=session.user_id,  # type: ignore
                created_at=session.created_at,
                metadata=session.metadata,
            )
            for session in sessions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list sessions: {str(e)}"
        )
    # finally:
    #     end = time.time()
    #     print(f"list_sessions took {end - start:.4f} seconds")
