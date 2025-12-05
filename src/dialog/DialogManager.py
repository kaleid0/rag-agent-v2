from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

# from beanie import PydanticObjectId
import asyncio
from datetime import datetime, timezone
from beanie.odm.operators.update.array import Push

from src.llm.adapter.BaseChatAdapter import BaseChatAdapter
from src.rag import RetrievePipelineProtocol
from .DialogMessage import DialogMessage, RoleEnum
from .odm.Session import Session

from src.prompt import llm_chat_stream


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
        memory_manager: Optional[Any] = None,
    ):
        self.retrieve_pipeline = retrieve_pipeline
        self.llm_adapter = llm_adapter
        self.mrmory_manager = memory_manager

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
    ) -> DialogMessage:
        msg = DialogMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        session.add_message(msg)
        session.message_count += 1
        await session.update(Push({Session.dialog_messages: msg}))  # type: ignore
        return msg

    # async def start_session(self, user_id: str, metadata: Optional[dict] = None) -> str:
    #     """创建并保存新会话，返回会话 ID"""
    #     s = Session(user_id=user_id, metadata=metadata or {})
    #     await s.insert()
    #     if s.id is None:
    #         raise RuntimeError("Failed to create session - ID is None")
    #     return str(s.id)

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

        await self._append_message(
            session,
            role=RoleEnum.user,
            content=message_content,
            metadata=message_metadata,
        )

        # 简单检索调用
        retrieved = []
        # 提取最近用户内容作为 query
        # last_user_msgs = [m for m in session.messages if m.get("role") == "user"]
        # query = last_user_msgs[-1].get("content") if last_user_msgs else ""

        if knowledge_base_id and self.retrieve_pipeline:
            retrieved = await self.retrieve_pipeline.retrieve_knowledge_base(
                query=message_content,
                knowledge_base_id=knowledge_base_id,
            )

            # prompt_template = get_prompt("RAG_answer")
            # prompt = prompt_template.format(
            #     information=retrieved, question=message_content
            # )

        else:
            prompt = message_content
        # messages = session.messages[:-1] + [{"role": "user", "content": prompt}]

        response_text = self.llm_adapter.chat(message_content)  # type: ignore

        if not response_text:
            raise RuntimeError("LLM did not return any response")

        # assistant_msg = DialogMessage(
        #     role=RoleEnum.assistant,
        #     content=response_text,
        #     metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
        # )
        # session.add_message(assistant_msg)
        assistant_msg = await self._append_message(
            session,
            role=RoleEnum.assistant,
            content=response_text,
            metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
        )

        return assistant_msg

    async def generate_response_stream(
        self,
        session: Session,
        message_content: str,
        message_metadata: dict | None = None,
        knowledge_base_id: Optional[str] = None,
    ) -> AsyncGenerator[str, Any]:

        message_metadata = message_metadata or {}

        # 简单检索调用
        retrieved = []
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
            await self._append_message(
                session,
                role=RoleEnum.user,
                content=message_content,
                metadata=message_metadata,
            )

        else:
            await self._append_message(
                session,
                role=RoleEnum.user,
                content=message_content,
                metadata=message_metadata,
            )
            stream_source = self.llm_adapter.async_stream_chat(session.messages)

        if asyncio.iscoroutine(stream_source):
            stream_source = await stream_source

        # 使用异步流式接口逐块接收文本并拼接
        async def token_stream():
            response_text = ""
            async for chunk in stream_source:
                if chunk:
                    response_text += chunk
                    # print(chunk)
                    yield chunk  # ✔ 流式向外推送
            # 全部结束后再保存到会话中
            assistant_msg = await self._append_message(
                session,
                role=RoleEnum.assistant,
                content=response_text,
                metadata={"generated_at": datetime.now(timezone.utc).isoformat()},
            )
            await session.save()

        return token_stream()

    # async def exit_session(self, session: Session) -> None:
    #     """结束会话，执行任何必要的清理操作"""
    #     # TODO
    #     # raise NotImplementedError("Session exit logic not implemented yet")
        


# async def 