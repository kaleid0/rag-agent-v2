from src.rag.utils import organize_context
from src.rag.retrieve_pipeline.retrieve import retrieve_knowledge_base
from src.rag.knowledge_base import KnowledgeBase
from config import rag_cfg


class SimplePipeline:

    # def __init__(self, retriever_type: str) -> None:
    #     self.retriever_type = retriever_type

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

        return organized_context
