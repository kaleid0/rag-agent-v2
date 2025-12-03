import asyncio
import os
import pickle
from beanie.odm.operators.update.general import Set

from .ingest import ingest
from src.document.odm.DocumentRecord import DocumentRecord, StatusEnum
from src.rag.retriever import ChromaRetriever, BM25Retriever
from src.rag.text_splitter.get_chunks import get_chunks

from config import rag_cfg


async def ingest_file(
    document_record_id: str,
    chunk_save_path: str | None = None,
    chunk_size: int = rag_cfg["chunk_size"],
    chunk_overlap: int = rag_cfg["chunk_overlap"],
    split_method: str = rag_cfg["split_method"],
    retriever_type: list[str] | None = None,
):
    """异步封装的 ingest 函数。

    Args:
        document_record_id (str): DocumentRecord 的 ID。
        chunk_save_path (str): 分块保存路径。
        chunk_size (int): 分块大小。
        chunk_overlap (int): 分块重叠大小。
        retriever_type (list[BaseRetriever]): 检索器类型列表。
    """
    if retriever_type is None:
        retriever_type = rag_cfg["retriever_type"]

    document_record = await DocumentRecord.get(document_record_id)
    if document_record is None:
        raise ValueError(f"未找到 ID 为 {document_record_id} 的 DocumentRecord")

    try:
        # 1. chunking
        chunk_save_path = (
            chunk_save_path
            if chunk_save_path is not None
            else os.path.join(rag_cfg["chunk_path"], str(document_record_id) + ".pkl")
        )

        with open(document_record.markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        chunks = get_chunks(
            markdown_content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            split_method=split_method,
            file_title=document_record.title,
            record_id=str(document_record.id),
        )

        os.makedirs(os.path.dirname(chunk_save_path), exist_ok=True)
        with open(chunk_save_path, "wb") as f:
            pickle.dump(chunks, f)

        document_record.num_chunks = len(chunks)

        # 2. ingeset
        r_type = []
        for rt in retriever_type:  # type: ignore
            if rt == "chroma":
                r_type.append(ChromaRetriever)
            elif rt == "bm25":
                r_type.append(BM25Retriever)

            await asyncio.to_thread(
                ingest,
                chunks=chunks,
                retriever_type=r_type,
            )
        document_record.status = StatusEnum.completed
        await document_record.save_changes()

    except Exception as e:
        document_record.status = StatusEnum.failed
        await document_record.update(Set({DocumentRecord.status: StatusEnum.failed}))
        raise e
