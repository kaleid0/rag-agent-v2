# from __future__ import annotations

from typing import Any, AsyncGenerator, Optional
import asyncio
from datetime import datetime, timezone
from beanie.odm.operators.update.general import Set

from src.llm import BaseChatAdapter
from src.rag import RetrievePipelineProtocol

from .DialogMessage import DialogMessage, RoleEnum
from src.session.odm.Session import Session

from src.prompt import llm_chat_stream, llm_call


class DialogManager:
    """管理会话生命周期并协调 RAG 与 LLM 调用的简单实现。

    RAG 和 LLM 是可注入的函数/适配器，便于测试与替换：
      - retriever(session: Session, query: str) -> List[dict]
      - llm(chat_prompt: str) -> str
    """

    def __init__(
        self,
        llm_adapter: BaseChatAdapter,
        retrieve_pipeline: Optional[RetrievePipelineProtocol] = None,
    ):
        self.retrieve_pipeline = retrieve_pipeline
        self.llm_adapter = llm_adapter

    async def set_llm_adapter(self, llm_adapter: BaseChatAdapter):
        self.llm_adapter = llm_adapter

    async def set_retrieve_pipeline(self, retrieve_pipeline: RetrievePipelineProtocol):
        self.retrieve_pipeline = retrieve_pipeline

    async def _append_message(
        self,
        session: Session,
        role: RoleEnum,
        content: str,
        metadata: Optional[dict] = None,
    ):
        msg = DialogMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        if role == RoleEnum.system:
            session.system_prompt = content
            await session.update(Set({"system_message": content}))
        else:
            session.dialog_messages.append(msg)
            session.message_count += 1
            await session.save_changes()

    # TODO stream模式已更新，非stream模式待更新
    async def generate_response(
        self,
        session: Session,
        message_content: str,
        message_metadata: dict | None = None,
        knowledge_base_id: Optional[str] = None,
    ) -> DialogMessage:
        """生成回复：
        1. 加载会话
        2. （可选）调用 retriever 获取上下文
        3. 使用 prompts 组装 prompt（此处简化为字符串拼接）
        4. 调用 llm 返回文本
        5. 将 assistant 消息追加到会话并返回
        """
        ...

    async def generate_response_stream(
        self,
        session: Session,
        message_content: str,
        message_metadata: dict | None = None,
        knowledge_base_id: Optional[str] = None,
    ) -> AsyncGenerator[str, Any]:

        message_metadata = message_metadata or {}

        # 检索调用
        retrieved = None
        if knowledge_base_id and self.retrieve_pipeline:
            retrieved = await self.retrieve_pipeline.retrieve_knowledge_base(
                query=message_content,
                knowledge_base_id=knowledge_base_id,
            )
            message_metadata["retrieved_context"] = retrieved

            stream_source = await llm_chat_stream(
                "RAG_answer",
                self.llm_adapter,
                session.messages,
                {
                    "information": retrieved,
                    "question": message_content,
                },
            )

        # 无检索，直接聊天
        else:
            stream_source = await llm_chat_stream(
                "plain_chat",
                self.llm_adapter,
                session.messages,
                {"user_message": message_content},
            )

        if asyncio.iscoroutine(stream_source):
            stream_source = await stream_source

        # 使用异步流式接口逐块接收文本并拼接
        async def token_stream():
            response_text = ""
            async for chunk in stream_source:
                if chunk:
                    response_text += chunk
                    yield chunk

            # 全部结束后再保存到会话中
            await self._append_message(
                session,
                role=RoleEnum.user,
                content=message_content,
                metadata=message_metadata,
            )
            await self._append_message(
                session,
                role=RoleEnum.assistant,
                content=response_text,
                metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
            )
            await session.save()

        return token_stream()

    async def generate_dialog_title(
        self,
        session: Session,
    ) -> str:
        """为会话生成标题"""
        title = await llm_call(
            prompt_name="generate_dialog_title",
            llm=self.llm_adapter,
            args={"text": session.messages},
        )
        session.metadata["title"] = title
        await session.save_changes()
        return title
