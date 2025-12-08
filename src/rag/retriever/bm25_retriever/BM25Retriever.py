import os
import pickle

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever as LangchainBM25Retriever

from src.rag.utils import remove_duplicates
from config import rag_cfg
from logging import getLogger

logger = getLogger(__name__)


class BM25Retriever:
    _instances = {}

    # @property
    # def name(self) -> str:
    #     return self.__class__.__name__

    def __new__(cls, collection_record_ids: list[str] | str, *args, **kwargs):
        if isinstance(collection_record_ids, str):
            collection_record_ids = [collection_record_ids]
        key = frozenset(str(i) for i in collection_record_ids)
        if key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[key] = instance
        return cls._instances[key]

    def __init__(
        self,
        collection_record_ids: list[str],
        language: dict[str, str] | None = None,
    ):
        if getattr(self, "_initialized", False):
            return
        if isinstance(collection_record_ids, str):
            collection_record_ids = [collection_record_ids]
        self._initialized = True

        all_documents = []
        self.bm25_retrievers: dict[str, LangchainBM25Retriever] = {}
        self.language: dict[str, str] = {}
        for cid in collection_record_ids:
            with open(
                os.path.join(rag_cfg["chunk_dir"], cid + ".pkl"),
                "rb",
            ) as f:
                documents = pickle.load(f)
                self.bm25_retrievers[cid] = LangchainBM25Retriever.from_documents(
                    documents
                )
                self.language[cid] = language.get(cid, "EN") if language else "EN"
                all_documents.extend(documents)
        self.all_retriever = LangchainBM25Retriever.from_documents(all_documents)

    @classmethod
    def ingest(
        cls,
        documents: list[Document],
        collection_record_id: str,
        **_: dict,
    ) -> None:
        """
        使用原始chunk即可
        """
        ...  # No additional processing needed for BM25

    def retrieve(
        self, query: dict | str, top_k: int = 10, query_route: dict | None = None
    ) -> list[Document]:
        if len(self.bm25_retrievers) == 0:
            return []

        documents = []
        if query_route:
            for record_id, k in query_route.items():
                if self.bm25_retrievers[record_id] is not None and k > 0:
                    if isinstance(query, dict):
                        doc_language = self.language.get(record_id, "EN")
                        query = query.get(doc_language, "")
                    self.bm25_retrievers[record_id].k = k
                    documents.extend(self.bm25_retrievers[record_id].invoke(query))  # type: ignore

        else:
            self.all_retriever.k = top_k // 2
            documents.extend(
                self.all_retriever.invoke(
                    query.get("EN", "") if isinstance(query, dict) else query
                )
            )
            documents.extend(
                self.all_retriever.invoke(
                    query.get("ZH", "") if isinstance(query, dict) else query
                )
            )
            documents = remove_duplicates(documents)

        return documents
