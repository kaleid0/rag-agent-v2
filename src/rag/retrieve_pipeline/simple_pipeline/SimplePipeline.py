import logging

from src.rag.utils import organize_context
from src.rag.retrieve_pipeline.retrieve import retrieve_knowledge_base, retrieve_memory
from src.rag.knowledge_base import KnowledgeBase
from config import rag_cfg, memory_cfg


logger = logging.getLogger(__name__)


class SimplePipeline:

    async def retrieve_document(self, query: str, document_record_id: str) -> str:
        """Retrieve documents based on the query."""
        raise NotImplementedError("This method is not implemented yet.")

    async def retrieve_knowledge_base(self, query: str, knowledge_base_id: str) -> str:

        knowledge_base = await KnowledgeBase.get(knowledge_base_id)
        if not knowledge_base:
            raise ValueError("Knowledge base not found")

        documents = await retrieve_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=10,  # TODO config
        )

        context_documents = (
            {doc.metadata["document_title"]: [doc] for doc in documents}
            if documents
            else {}
        )

        organized_context = organize_context(context_documents)
        logger.info("SimplePipeline: organized context:")
        for title, contents in organized_context.items():  # type: ignore
            logger.info(f"  - {title}:")
            for content in contents:
                logger.info(f"    {content[:30]}...")

        return organized_context

    async def retrieve_memory(self, query: str, user_id: str) -> str:
        """Retrieve memory based on the query."""
        documents = await retrieve_memory(
            user_id=user_id,
            query=query,
            top_k=memory_cfg["top_k"],
        )
        return "".join([doc.page_content for doc in documents] if documents else [])
