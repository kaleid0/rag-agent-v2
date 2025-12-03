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
    all_grades = []
    batch = 5
    for i in range(0, len(documents), batch):
        batch_texts = documents[i : i + batch]
        # grades = await grade_texts(
        #     query,  # type: ignore
        #     [doc.page_content for doc in batch_texts],
        # )
        grades = await llm_call(
            prompt_name="grade_texts",
            llm=get_llm(
                llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"]
            ),
            args={
                "query": query,
                "test1": batch_texts[0].page_content,
                "test2": batch_texts[1].page_content,
                "test3": batch_texts[2].page_content,
                "test4": batch_texts[3].page_content,
                "test5": batch_texts[4].page_content,
            },
        )
        grades = list(map(int, grades.values()))
        all_grades.extend(grades)

    text_grade_pairs = list(zip(documents, all_grades))
    # 按分数降序排序
    sorted_pairs = sorted(text_grade_pairs, key=lambda x: x[1], reverse=True)
    # 提取排序后的文本
    sorted_texts = [pair[0] for pair in sorted_pairs]
    return sorted_texts
