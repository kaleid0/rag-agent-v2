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
        texts = [doc.page_content for doc in batch_texts]
        # 不足5个补齐到5个
        while len(texts) < 5:
            texts.append("")
        task.append(
            llm_call(
                prompt_name="grade_texts",
                llm=get_llm(
                    llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"]
                ),
                args={
                    "query": query,
                    "text1": texts[0],
                    "text2": texts[1],
                    "text3": texts[2],
                    "text4": texts[3],
                    "text5": texts[4],
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
