"""FastAPI 依赖注入"""

from typing import Optional

from dialog.SessionService import SessionService
from src.dialog import DialogManager
from src.memory import MemoryManager
from src.rag import RetrievePipelineProtocol, EnhancedPipeline
from src.llm import get_llm

# from src.rag import retrieve_knowledge_base_pipeline
from config import rag_cfg


# 全局单例
_dialog_manager: Optional[DialogManager] = None
_memory_manager: Optional[MemoryManager] = None
_session_service: Optional[SessionService] = None

# def get_retriever_function():
#     """获取检索器 pipeline

#     返回一个可调用对象，用于从知识库检索相关信息
#     """
#     retriever: Optional[RetrievePipelineProtocol] = None

#     # 创建检索器
#     if rag_cfg.get("retriever_type") == "enhanced_pipeline":
#         retriever = EnhancedPipeline.create_from_config(rag_cfg)


#     return retriever


def get_dialog_manager() -> DialogManager:
    """获取 DialogManager 单例

    这个函数确保整个应用共享同一个 DialogManager 实例
    """
    global _dialog_manager

    if _dialog_manager is None:
        # 从配置创建 LLM 适配器
        llm_provider = rag_cfg.get("llm_provider", "deepseek")
        llm_model = rag_cfg.get("llm_model", "deepseek-chat")

        # 创建 LLM chat 函数
        llm_adapter = get_llm(llm_provider=llm_provider, model=llm_model)

        # 创建 DialogManager
        _dialog_manager = DialogManager(
            llm_adapter=llm_adapter, retrieve_pipeline=EnhancedPipeline()
        )

    return _dialog_manager


# async def get_memory_manager() -> MemoryManager:
#     """获取 MemoryManager 单例

#     这个函数确保整个应用共享同一个 MemoryManager 实例
#     """
#     global _memory_manager

#     if _memory_manager is None:
#         # 创建 MemoryManager 实例
#         _memory_manager = MemoryManager()

#     return _memory_manager


def reset_dialog_manager():
    """重置 DialogManager（主要用于测试）"""
    global _dialog_manager
    _dialog_manager = None


def get_session_service() -> SessionService:
    """获取 DialogService 实例"""
    global _session_service
    if _session_service is None:
        dialog_manager = get_dialog_manager()
        _session_service = SessionService(dialog_manager=dialog_manager)
    return _session_service
