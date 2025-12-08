from chromadb import Collection, EmbeddingFunction, GetResult, QueryResult
from langchain_core.documents import Document

# from beanie import PydanticObjectId

from logging import getLogger

from src.database import get_collection
from .EmbeddingFunction import EmbeddingFunction, SyncEmbeddingFunction


logger = getLogger(__name__)


class ChromaRetriever:
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
        collection_record_ids: list[str] | str,
        language: dict[str, str] | None = None,
        embedding_function: EmbeddingFunction = SyncEmbeddingFunction(),
    ):
        if getattr(self, "_initialized", False):
            return
        if isinstance(collection_record_ids, str):
            collection_record_ids = [collection_record_ids]
        self._initialized = True
        self.embedding_function = embedding_function

        collection_ids = [str(rid) for rid in collection_record_ids]
        self.vector_stores: dict[str, Collection] = {}
        self.language: dict[str, str] = {}
        for cid in collection_ids:
            self.vector_stores[cid] = get_collection(
                cid, embedding_function=embedding_function
            )
            self.language[cid] = language.get(cid, "EN") if language else "EN"

    @classmethod
    def ingest(
        cls,
        documents: list[Document],
        collection_record_id: str,
        embedding_function: EmbeddingFunction = SyncEmbeddingFunction(),
        **_: dict,
    ):
        if collection_record_id is None:
            collection_record_id = "default_record"

        try:
            # Chroma 向量化
            # 分批次传给embedding服务器，太大会导致传输时间太长超时
            # ids 用于上下文回找，vector_store.get(ids="0")
            batch_size = 10  # 最大10
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                page_contents, metadatas = zip(
                    *((b.page_content, b.metadata) for b in batch)
                )

                vector_store = get_collection(
                    collection_record_id, embedding_function=embedding_function
                )
                vector_store.add(
                    ids=[b.id for b in batch],  # type: ignore
                    documents=list(page_contents),
                    metadatas=list(metadatas),
                )

        except Exception as e:
            logger.error(f"文档向量化失败: {collection_record_id}", exc_info=e)
            raise RuntimeError(f"文档切片或向量化失败: {id}") from e

    # TODO query 中英文 配对
    def retrieve(
        self, query: dict | str, top_k: int = 10, query_route: dict | None = None
    ) -> list[Document]:
        if len(self.vector_stores) == 0:
            return []

        if query_route:
            documents = []
            for record_id, k in query_route.items():
                if self.vector_stores[record_id] is not None and k > 0:
                    if isinstance(query, dict):
                        doc_language = self.language.get(record_id, "EN")
                        query = query.get(doc_language, "")
                    result = self.vector_stores[record_id].query(
                        query_texts=query, n_results=k  # type: ignore
                    )
                    documents.extend(flatten_query_result(result))

        else:
            results = []
            for vs in self.vector_stores.values():
                res = vs.query(
                    query_texts=[
                        query.get("EN", "") if isinstance(query, dict) else query
                    ],
                    n_results=top_k,
                )
                results.append(res)

            topk_results = get_topk_query_result(results, top_k)
            documents = [doc for _, doc in topk_results]
        return documents

    async def get_by_ids(
        self, record_ids: list[str], ids: list[list[str]]
    ) -> dict[str, list[Document]]:
        if len(record_ids) != len(ids):
            raise ValueError("record_ids 和 ids 长度不匹配")

        result: dict[str, list[Document]] = {}
        for rid, id_list in zip(record_ids, ids):
            collection = self.vector_stores.get(str(rid))
            if collection is None:
                result[str(rid)] = []
                raise ValueError(f"Chroma collection for record_id {rid} not found")
            else:
                docs = flatten_query_result(collection.get(ids=id_list))
                result[str(rid)] = docs
        return result


def get_topk_query_result(results: list[QueryResult], k: int):
    """
    从多个 QueryResult 中，基于 distances 全局排序，取前 k 条最相关文档。
    返回一个列表，每项为 (distance, document)
    """

    merged: list[tuple[float, Document]] = []

    for result in results:
        distances = result.get("distances")
        documents = result.get("documents")
        metadatas = result.get("metadatas")

        if distances is None or documents is None or metadatas is None:
            continue

        # 遍历每个 query 的结果
        for dist_list, doc_list, meta_list in zip(distances, documents, metadatas):
            for dist, doc, meta in zip(dist_list, doc_list, meta_list):
                merged.append((dist, Document(page_content=doc, metadata=meta)))  # type: ignore

    # 按距离升序排序
    merged.sort(key=lambda x: x[0])

    # 返回 top-k
    return merged[:k]


def flatten_query_result(result: QueryResult | GetResult) -> list[Document]:
    """基于 ChromaDB 返回的 QueryResult 或 GetResult，构建 Document 列表"""
    flat_docs = []

    ids_list = result.get("ids") or []
    docs_list = result.get("documents") or []
    metas_list = result.get("metadatas") or []

    # 遍历所有查询结果
    if "distances" in result:
        # QueryResult 结构
        for ids, docs, metas in zip(ids_list, docs_list, metas_list):
            # 遍历一次查询结果中的每个文档
            for id, doc, meta in zip(ids, docs, metas):
                if not isinstance(meta, dict):
                    raise ValueError("Metadata should be a dictionary.")
                flat_docs.append(
                    Document(
                        page_content=doc,
                        metadata={**meta},
                        id=id,
                    )
                )
    else:
        # GetResult 结构
        for id, doc, meta in zip(ids_list, docs_list, metas_list):
            if not isinstance(meta, dict):
                raise ValueError("Metadata should be a dictionary.")
            flat_docs.append(
                Document(
                    page_content=doc,  # type: ignore
                    metadata={**meta},
                    id=id,
                )
            )

    return flat_docs
