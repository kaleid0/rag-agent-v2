import asyncio
import os

from beanie.odm.operators.update.general import Set
from beanie.operators import In

from src.database import get_collection
from .odm.KnowledgeBase import KnowledgeBase
from .odm.CollectionRecord import CollectionRecord
from src.rag.ingest.ingest import ingest_file
from src.document import DocumentRecord

from config import rag_cfg


async def create_knowledge_base(
    name: str,
    description: str = "",
    chunk_size: int = 300,
    chunk_overlap: int = 50,
    split_method: str = "hierarchical",
    retriever_type: str = "hybrid",
    document_record_ids: list[str] | None = None,
) -> KnowledgeBase:
    """创建一个新的知识库。

    Args:
        name (str): 知识库名称，必须唯一。
        description (str, optional): 知识库描述. Defaults to "".
        document_record_ids (Optional[list[str]], optional): 关联的文件记录ID列表. Defaults to None.

    Returns:
        KnowledgeBase: 创建的知识库对象。
    """
    knowledge_base = KnowledgeBase(
        name=name,
        description=description,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        split_method=split_method,
        retriever_type=retriever_type,
    )

    task = []
    for record_id in document_record_ids or []:
        document_record = await DocumentRecord.get(record_id)
        if not document_record:
            raise ValueError(f"Document record with ID {record_id} not found")

        # TODO 解析任务，创建 CollectionRecord 等
        raise NotImplementedError(
            "Ingest task not implemented in create_knowledge_base"
        )

    await knowledge_base.insert()
    return knowledge_base


async def remove_record_from_knowledge_base(
    knowledge_base_id: str, collection_record_id: str
):
    """从知识库中移除一个 collection 记录。

    Args:
        knowledge_base_id (str): 知识库ID。
        collection_record_id (str): 文件记录ID。
    """
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    collection_record = await CollectionRecord.get(collection_record_id)
    if not collection_record:
        raise ValueError("Document record not found")

    # 清理相关内容（chunk，chromadb记录），已在 CollectionRecord 的删除钩子中处理
    collection_record.delete()


async def add_record_to_knowledge_base(knowledge_base_id: str, document_record_id: str):
    """向知识库中添加一个文件记录。

    Args:
        knowledge_base_id (str): 知识库ID。
        record_id (str): 文件记录ID。
    """
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")
    document_record = await DocumentRecord.get(document_record_id)
    if not document_record:
        raise ValueError("Document record not found")
    if not document_record.markdown_path:
        raise ValueError("Document record has not been parsed yet")

    collection_record = CollectionRecord(
        knowledge_base_id=knowledge_base_id,
        document_record_id=document_record_id,
    )
    await collection_record.insert()

    chunk_save_path = os.path.join(
        rag_cfg["chunk_dir"], str(collection_record.id) + ".pkl"
    )

    ingest_result = await asyncio.to_thread(
        ingest_file,
        str(collection_record.id),
        document_record.markdown_path,
        chunk_save_path,
        document_record.title,  # type: ignore
        knowledge_base.chunk_size,
        knowledge_base.chunk_overlap,
        knowledge_base.split_method,
        knowledge_base.retriever_type,
    )
    collection_record.chunk_path = chunk_save_path
    collection_record.num_chunks = ingest_result.num_chunks

    await collection_record.update(
        Set({CollectionRecord.chunk_path: chunk_save_path}),
        Set({CollectionRecord.num_chunks: ingest_result.num_chunks}),
    )


async def delete_knowledge_base(knowledge_base_id: str):
    """删除一个知识库。

    Args:
        knowledge_base_id (str): 知识库ID。
    """
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    if knowledge_base.retriever_type in ["vector", "hybrid"]:
        # 删除相关 向量库
        collection_records = await CollectionRecord.find(
            CollectionRecord.knowledge_base_id == knowledge_base_id
        ).to_list()
        for collection_record in collection_records:
            collection = get_collection(name=str(collection_record.id))
            collection.delete()

    await CollectionRecord.find(
        CollectionRecord.knowledge_base_id == knowledge_base_id
    ).delete()

    await knowledge_base.delete()


async def list_knowledge_bases(skip: int = 0, limit: int = 100) -> list[KnowledgeBase]:
    """列出所有知识库。

    Returns:
        list[KnowledgeBase]: 知识库列表。
    """
    knowledge_bases = await KnowledgeBase.find_all(skip, limit).to_list()
    return knowledge_bases


async def get_collections_in_knowledge_base(
    knowledge_base_id: str | list[str],
) -> list[CollectionRecord]:
    """获取知识库中的所有 collection 记录。

    Args:
        knowledge_base_id (str): 知识库ID。

    Returns:
        list[CollectionRecord]: collection 记录列表。
    """
    if isinstance(knowledge_base_id, str):
        knowledge_base_id = [knowledge_base_id]

    collections = await CollectionRecord.find(
        In(CollectionRecord.knowledge_base_id, knowledge_base_id)
    ).to_list()
    return collections
