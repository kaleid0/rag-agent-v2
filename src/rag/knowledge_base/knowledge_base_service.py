# from typing import Optional

from beanie.odm.operators.update.array import Pop, Push

from .odm.KnowledgeBase import KnowledgeBase
from src.document import DocumentRecord, id_to_title


async def create_knowledge_base(
    name: str,
    description: str = "",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    split_method: str = "recursive",
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
        document_record_ids=document_record_ids or [],
    )
    # for _id in document_record_ids or []:
    #     document_record = await DocumentRecord.get(_id)
    #     if document_record:
    #         document_record.knowledge_base_ids.append(str(knowledge_base.id))
    #         await document_record.update(
    #             Push({DocumentRecord.knowledge_base_ids: str(knowledge_base.id)})  # type: ignore
    #         )
    #         knowledge_base.document_titles.append(document_record.title)

    DocumentRecord.find({"$in": document_record_ids or []}).update_many(
        Push({DocumentRecord.knowledge_base_ids: str(knowledge_base.id)})  # type: ignore
    )
    knowledge_base.document_titles = [
        await id_to_title(_id) for _id in document_record_ids or []
    ]

    await knowledge_base.insert()
    return knowledge_base


async def remove_record_from_knowledge_base(
    knowledge_base_id: str, document_record_id: str
):
    """从知识库中移除一个文件记录。

    Args:
        knowledge_base_id (str): 知识库ID。
        record_id (str): 文件记录ID。
    """
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    if document_record_id in knowledge_base.document_record_ids:
        knowledge_base.document_record_ids.remove(document_record_id)
        await knowledge_base.update(Pop({KnowledgeBase.document_record_ids: document_record_id}))  # type: ignore


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

    if document_record_id not in knowledge_base.document_record_ids:
        knowledge_base.document_record_ids.append(document_record_id)
        await knowledge_base.update(Push({KnowledgeBase.document_record_ids: document_record_id}))  # type: ignore

    if knowledge_base_id not in document_record.knowledge_base_ids:
        document_record.knowledge_base_ids.append(knowledge_base_id)
        await document_record.update(
            Push({DocumentRecord.knowledge_base_ids: knowledge_base_id})  # type: ignore
        )


async def delete_knowledge_base(knowledge_base_id: str):
    """删除一个知识库。

    Args:
        knowledge_base_id (str): 知识库ID。
    """
    knowledge_base = await KnowledgeBase.get(knowledge_base_id)
    if not knowledge_base:
        raise ValueError("Knowledge base not found")

    for record_id in knowledge_base.document_record_ids:
        document_record = await DocumentRecord.get(record_id)
        if document_record and knowledge_base_id in document_record.knowledge_base_ids:
            document_record.knowledge_base_ids.remove(knowledge_base_id)
            await document_record.update(
                Pop({DocumentRecord.knowledge_base_ids: knowledge_base_id})  # type: ignore
            )

    await knowledge_base.delete()


async def list_knowledge_bases() -> list[KnowledgeBase]:
    """列出所有知识库。

    Returns:
        list[KnowledgeBase]: 知识库列表。
    """
    knowledge_bases = await KnowledgeBase.find_all().to_list()
    return knowledge_bases
