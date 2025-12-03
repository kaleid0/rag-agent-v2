import logging
from langchain_core.documents import Document


from src.rag.retriever import RetrieverProtocol

# from src.rag.text_splitter.get_chunks import get_chunks

# from config import rag_cfg


logger = logging.getLogger(__name__)


def ingest(
    chunks: list[Document],
    retriever_type: list[RetrieverProtocol],
):
    """分块，并将Markdown文件内容分块并添加到指定的检索器中。"""

    if len(retriever_type) == 0:
        raise ValueError("至少需要指定一种检索器类型")

    # with open(markdown_path, "r", encoding="utf-8") as f:
    #     markdown_content = f.read()

    # # 1. chunking
    # chunks = get_chunks(
    #     markdown_content,
    #     chunk_save_path=chunk_save_path,
    #     chunk_size=chunk_size,
    #     chunk_overlap=chunk_overlap,
    # )
    # num_chunks = len(chunks)

    # 2. ingest
    for retriever in retriever_type:
        try:
            retriever.ingest(chunks)
        except Exception as e:
            logger.error(f"在向检索器 {retriever.name} 中添加文档时出错: {e}")
            raise e
