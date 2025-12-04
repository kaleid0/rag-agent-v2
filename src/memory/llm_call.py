import json

# from src.dialog.DialogMessage import DialogMessage
# from src.llm.Message import Messages
# from ..tools.get_prompt import get_prompt
from ..llm.factory import get_llm
from config import rag_cfg


# async def memory_summary(
#     messages: list[dict[str, str]], memory_type: str = "short"
# ) -> dict:
#     """整理对话的关键信息，返回摘要结果的字典表示。"""
#     llm = get_llm(llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"])
#     if memory_type == "short":
#         summary_prompt = get_prompt("short_term_memory_summary")
#     elif memory_type == "long":
#         summary_prompt = get_prompt("long_term_memory_summary")
#     else:
#         raise ValueError(f"Unsupported memory_type: {memory_type}")

#     prompt = summary_prompt.format(messages=str(messages))
#     llm_response = await llm.async_call(
#         prompt, format="json", max_tokens=1000, temperature=0
#     )
#     if llm_response is None:
#         raise RuntimeError("LLM 调用失败，未获取响应。")

#     return json.loads(llm_response)


# async def memory_merge(exist_memory: dict, new_memory: dict) -> dict:
#     llm = get_llm(llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"])
#     merge_prompt = get_prompt("memory_merge")

#     prompt = merge_prompt.format(
#         existing_summary=str(exist_memory), new_summary=str(new_memory)
#     )
#     llm_response = await llm.async_call(
#         prompt, format="json", max_tokens=1000, temperature=0
#     )
#     if llm_response is None:
#         raise RuntimeError("LLM 调用失败，未获取响应。")

#     return json.loads(llm_response)
