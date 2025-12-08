from langchain_core.documents import Document
from beanie.operators import In
from beanie import PydanticObjectId

from src.rag.knowledge_base import KnowledgeBase
from src.document import DocumentRecord
from src.rag.retriever import BM25Retriever, ChromaRetriever
from src.rag.knowledge_base import CollectionRecord

from config import rag_cfg, memory_cfg

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


async def retrieve_knowledge_base(
    knowledge_base_id: str,
    query: dict | str,
    # retriever_type: Optional[str],
    top_k: int = 10,
    query_route: dict[str, int] | None = None,
) -> list[Document] | None:
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    collection_records = await CollectionRecord.find(
        CollectionRecord.knowledge_base_id == knowledge_base_id
    ).to_list()
    if not collection_records:
        return []

    document_record_ids = [PydanticObjectId(rec.document_record_id) for rec in collection_records]
    docs = await DocumentRecord.find(
        In(DocumentRecord.id, document_record_ids)
    ).to_list()
    doc_id_languages = {str(doc.id): doc.language for doc in docs}
    col_ids = []
    languages = {}
    for col_record in collection_records:
        col_ids.append(str(col_record.id))
        languages[str(col_record.id)] = doc_id_languages.get(
            str(col_record.document_record_id), "EN"
        )

    if knowledge_base.retriever_type == "vector":
        retriever = [ChromaRetriever(col_ids, language=languages)]
    elif knowledge_base.retriever_type == "sparse":
        retriever = [BM25Retriever(col_ids, language=languages)]
    elif knowledge_base.retriever_type == "hybrid":
        retriever = [
            ChromaRetriever(col_ids, language=languages),
            BM25Retriever(col_ids, language=languages),
        ]
    else:
        raise ValueError("Invalid retriever type")

    results: list[Document] = []
    if query_route:
        for r in retriever:
            results.extend(r.retrieve(query, query_route=query_route))
    else:
        for r in retriever:
            results.extend(r.retrieve(query, top_k=top_k // len(retriever)))

    return results

# TODO 设置相似度阈值
# TODO context 组装
async def retrieve_memory(
    user_id: str,
    query: dict | str,
    top_k: int = 10,
) -> list[Document] | None:

    if memory_cfg["retriever_type"] == "vector":
        retriever = [ChromaRetriever([user_id])]
    elif memory_cfg["retriever_type"] == "sparse":
        retriever = [BM25Retriever([user_id])]
    elif memory_cfg["retriever_type"] == "hybrid":
        retriever = [ChromaRetriever([user_id]), BM25Retriever([user_id])]

    results: list[Document] = []
    for r in retriever:
        results.extend(r.retrieve(query, top_k=top_k // len(retriever)))

    return results
