import asyncio
import logging

from src.rag.utils import organize_context
from .context_retrieve import context_retrieve
from .rerank import rerank
from src.prompt import llm_call

from src.document import id_to_title, get_keywords
from src.rag.knowledge_base import KnowledgeBase, CollectionRecord
from src.rag.retrieve_pipeline.retrieve import retrieve_knowledge_base
from src.llm import get_llm
from config import rag_cfg

logger = logging.getLogger(__name__)

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


class EnhancedPipeline:

    # TODO llm_adapter，检索配置信息，把rerank等方法也加进来
    # def __init__(self, retriever_type: str) -> None:
    #     self.retriever_type = retriever_type

    # TODO
    async def retrieve_document(self, query: str, document_record_id: str) -> str:
        # 1. query rewrite

        # 2. retrieve document

        # 3. context retrieve

        raise NotImplementedError

    # TODO 设置检索数量
    async def retrieve_knowledge_base(self, query: str, knowledge_base_id: str) -> str:
        # knowledge_base = await KnowledgeBase.get(knowledge_base_id)
        if not await KnowledgeBase.get(knowledge_base_id):
            raise ValueError("Knowledge base not found")
        collection_records = await CollectionRecord.find(
            CollectionRecord.knowledge_base_id == knowledge_base_id
        ).to_list()

        # 1. query rewrite, query route ===============================================================
        tasks_map = {}

        if rag_cfg.get("query_rewrite"):
            tasks_map["rewrited_query"] = asyncio.create_task(
                llm_call(
                    prompt_name="query_rewrite",
                    llm=get_llm(
                        llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"]
                    ),
                    args={"question": query},
                )
            )

        if rag_cfg.get("query_route"):
            titles = [id_to_title(col.document_record_id) for col in collection_records]
            tasks = [
                asyncio.create_task(get_keywords(col.document_record_id))
                for col in collection_records
            ]
            keywords = await asyncio.gather(*tasks)

            tasks_map["routed_query"] = asyncio.create_task(
                llm_call(
                    prompt_name="query_route",
                    llm=get_llm(
                        llm_provider=rag_cfg["llm_provider"], model=rag_cfg["llm_model"]
                    ),
                    args={"titles": titles, "keywords": keywords, "question": query},
                )
            )

            # XXX 如果title有重复会出问题
            # title_to_id = {id_to_title(_id): _id for _id in document_record_ids}

        # 获取任务结果
        if tasks_map:
            results = await asyncio.gather(*tasks_map.values())
            rewrited_query = (
                results[list(tasks_map.keys()).index("rewrited_query")]
                if "rewrited_query" in tasks_map
                else None
            )
            routed_query = (
                results[list(tasks_map.keys()).index("routed_query")]
                if "routed_query" in tasks_map
                else None
            )
            logger.info(f"EnhancedPipeline: rewrited_query={rewrited_query}")
            logger.info(f"EnhancedPipeline: routed_query={routed_query}")
        # 如果没有任务，直接返回默认值
        else:
            rewrited_query = routed_query = None

        # 2. retrieve knowledge base ===============================================================================
        if rag_cfg.get("query_route"):
            routed_query_id: dict[str, int] = {}
            for i, (title, count) in enumerate(routed_query.items()):  # type: ignore
                routed_query_id[str(collection_records[i].id)] = count

            result = await retrieve_knowledge_base(
                knowledge_base_id=knowledge_base_id,
                query=rewrited_query if rewrited_query else query,
                query_route=routed_query_id,
            )
        else:
            result = await retrieve_knowledge_base(
                knowledge_base_id=knowledge_base_id,
                query=rewrited_query if rewrited_query else query,
                top_k=10,  # TODO config
            )
        logger.info(f"EnhancedPipeline: retrieved documents:")
        for doc in result or []:
            logger.info(f"  - {doc.metadata['document_title']}")
            logger.info(f"    {doc.page_content[:100]}...")

        # 3. rerank =============================================================================================
        if rag_cfg.get("rerank"):
            if result:
                documents = await rerank(
                    query=rewrited_query if rewrited_query else query,
                    documents=result,
                    top_k=10,
                )
        else:
            documents = result
        logger.info(f"EnhancedPipeline: reranked documents:")
        for doc in documents or []:
            logger.info(f"  - {doc.metadata['document_title']}")
            logger.info(f"    {doc.page_content[:30]}...")

        # 4. context retrieve ====================================================================================
        if rag_cfg.get("context_retrieve"):
            context_documents = (
                await context_retrieve(documents, num_context=3) if documents else {}
            )
        else:
            context_documents = (
                {doc.metadata["document_title"]: [doc] for doc in documents}
                if documents
                else {}
            )

        organized_context = organize_context(context_documents)

        logger.info("EnhancedPipeline: organized context:")
        for title, contents in organized_context.items():  # type: ignore
            logger.info(f"  - {title}:")
            for content in contents:
                logger.info(f"    {content[:30]}...")

        return organized_context

    async def retrieve_memory(self, query: str, user_id: str) -> str:
        raise NotImplementedError
