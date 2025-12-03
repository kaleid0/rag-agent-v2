from chromadb import Documents, EmbeddingFunction, Embeddings

from src.embedding import get_embedding_model


class SyncEmbeddingFunction(EmbeddingFunction):
    """_summary_
    EmbeddingFunction 是一个“向量生成器的包装类”，
    用来让 Chroma 在插入或查询文本时，自动调用你定义的 embedding_call 函数生成向量。
    """

    def __init__(self, llm_provider: str = "bailian", model: str = "text-embedding-v4"):
        self.embedding_model = get_embedding_model(
            llm_provider=llm_provider, model=model
        )

    def __call__(self, input: Documents) -> Embeddings:
        # embed the documents somehow
        return self.embedding_model.embedding_call(input)


# TODO: 异步版本
# class AsyncEmbeddingFunction(EmbeddingFunction):
#     """_summary_
#     EmbeddingFunction 是一个“向量生成器的包装类”，
#     用来让 Chroma 在插入或查询文本时，自动调用你定义的 embedding_call 函数生成向量。
#     """

#     def __init__(self, llm_provider: str = "bailian", model: str = "text-embedding-v4"):
#         self.embedding_model = get_embedding_model(
#             llm_provider=llm_provider, model=model
#         )

#     async def __call__(self, input: Documents) -> Embeddings:
#         # embed the documents somehow
#         return await self.embedding_model.async_embedding_call(input)
