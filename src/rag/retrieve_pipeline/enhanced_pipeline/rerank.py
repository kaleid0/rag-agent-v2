import asyncio
from langchain_core.documents import Document

from src.prompt import llm_call
from src.llm import get_llm
from config import rag_cfg


async def rerank(
    query: str | dict, documents: list[Document], top_k: int = 10
) -> list[Document]:
    """
    Args:
        query (str):
            resnet18的参数量是多少?
        texts (list[str]):
            ["text1", "text2", "text3", "text4", "text5"]

    Returns:
        list[str]:
            ["text3", "text1", "text5", "text2", "text4"]
    """
    if isinstance(query, dict):
        query = query.get("EN", "")

    batch = 5
    task = []
    for i in range(0, len(documents), batch):
        batch_texts = documents[i : i + batch]
        task.append(
            llm_call(
                prompt_name="grade_texts",
                llm=get_llm(
                    llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"]
                ),
                args={
                    "query": query,
                    "text1": batch_texts[0].page_content,
                    "text2": batch_texts[1].page_content,
                    "text3": batch_texts[2].page_content,
                    "text4": batch_texts[3].page_content,
                    "text5": batch_texts[4].page_content,
                },
            )
        )

    result = await asyncio.gather(*task)
    all_grades = []
    for grades in result:
        all_grades.extend(list(map(int, grades.values())))

    # grades = list(map(int, grades.values()))
    # all_grades.extend(grades)

    text_grade_pairs = list(zip(documents, all_grades))
    # 按分数降序排序
    sorted_pairs = sorted(text_grade_pairs, key=lambda x: x[1], reverse=True)
    # 提取排序后的文本
    sorted_texts = [pair[0] for pair in sorted_pairs]
    return sorted_texts
