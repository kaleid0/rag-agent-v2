# from beanie import PydanticObjectId
# from typing import Optional
from langchain_core.documents import Document

from src.rag.knowledge_base import KnowledgeBase
from src.document import DocumentRecord
from src.rag.retriever import RetrieverProtocol, BM25Retriever, ChromaRetriever

# from src.rag.utils import remove_duplicates
from config import rag_cfg

"""
Document 结构：
{
    'page_content': '...',          # 文本内容
    'metadata': {
        'header': '...',            # 章节标题
        'document_title': '...',    # 文档标题
        'record_id': '...',         # 文档记录ID
        'num_chunks': 10,         # 文档总片段数
    },
    'id': '...'                     # 文档片段ID
}
"""


# async def retrieve_document(record_id: str, query: str, top_k: int) -> list[Document]:
#     record = await DocumentRecord.find_one(DocumentRecord.id == record_id)
#     if not record:
#         raise ValueError("Record not found")
#     if record.status != "completed":
#         raise ValueError("Record ingestion not completed")

#     if rag_cfg.get("retrievel_method") is None:
#         raise ValueError("retrievel_method is not configured")

#     retriever: list[BaseRetriever] = []
#     if "chroma" in rag_cfg["retrievel_method"]:
#         retriever.append(ChromaRetriever(str(record_id)))
#     if "bm25" in rag_cfg["retrievel_method"]:
#         retriever.append(BM25Retriever(str(record_id), language="EN"))

#     results = []
#     for r in retriever:
#         results.extend(r.retrieve(query, top_k // len(retriever)))

#     # 去重
#     unique_docs = remove_duplicates(results)
#     return unique_docs


async def retrieve_knowledge_base(
    knowledge_base_id: str,
    query: dict | str,
    # retriever_type: Optional[str],
    top_k: int = 10,
    query_route: dict[str, int] | None = None,
) -> list[Document] | None:
    knowledge_base = await KnowledgeBase.find_one(KnowledgeBase.id == knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    record_ids = [str(record_id) for record_id in knowledge_base.document_record_ids]
    if not record_ids:
        return None
    languages = {}
    for rid in record_ids:
        record = await DocumentRecord.get(rid)
        if record:
            languages[rid] = record.language

    # retriever: list[RetrieverProtocol] = []
    # if "chroma" in rag_cfg["retriever_type"]:
    #     retriever.append(ChromaRetriever(record_ids, language=languages))
    # if "bm25" in rag_cfg["retriever_type"]:
    #     retriever.append(BM25Retriever(record_ids, language=languages))
    if knowledge_base.retriever_type == "vector":
        retriever = [ChromaRetriever(record_ids, language=languages)]
    elif knowledge_base.retriever_type == "sparse":
        retriever = [BM25Retriever(record_ids, language=languages)]
    elif knowledge_base.retriever_type == "hybrid":
        retriever = [
            ChromaRetriever(record_ids, language=languages),
            BM25Retriever(record_ids, language=languages),
        ]

    results: list[Document] = []
    if query_route:
        for r in retriever:
            results.extend(r.retrieve(query, query_route=query_route))
    else:
        for r in retriever:
            results.extend(r.retrieve(query, top_k=top_k // len(retriever)))

    return results
