from langchain_core.documents import Document


from .MarkdownHeaderTextSplitter import MarkdownHeaderTextSplitter
from .RecursiveCharacterTextSplitter import RecursiveCharacterTextSplitter


def get_chunks(
    text: str,
    # chunk_save_path: str,
    chunk_size: int,
    chunk_overlap: int,
    split_method: str = "hierarchical",  # 'hierarchical' or 'recursive'
    file_title: str | None = None,
    record_id: str | None = None,
) -> list[Document]:

    # 切片处理
    chunks = _chunking(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        split_method=split_method,
    )
    chunks = _add_metadata(chunks, file_title, record_id)

    return chunks


def _chunking(
    text: str, chunk_size: int, chunk_overlap: int = 0, **kwargs
) -> list[dict[str, str]]:
    """
    文档分块处理, 保存片段

    output: list[str] or list[dict] [{'Header 1': 'Introduction', 'content': '...'}, ...]
    """
    if kwargs.get("split_method") == "recursive":
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        # -> list[dict] [{'content': '...'}, ...]

    elif kwargs.get("split_method") == "hierarchical":
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            chunk_size=chunk_size,
        )
        # -> list[dict] [{'Header 1': 'Introduction', 'content': '...'}, ...]

    text_list = text_splitter.split_text(text)

    return text_list


def _add_metadata(
    chunks: list[dict], document_title: str | None = None, record_id: str | None = None
) -> list[Document]:
    """
    添加id元数据
    """
    documents = [
        Document(
            page_content=chunk.get("content", ""),
            metadata={
                "header": chunk.get("Header 3")
                or chunk.get("Header 2")
                or chunk.get("Header 1")
                or "No Header",
                "document_title": document_title if document_title else "unknown_title",
                "record_id": str(record_id) if record_id else "unknown_record",
                "num_chunks": len(chunks),
            },
            id=f"{i}",
        )
        for i, chunk in enumerate(chunks)
    ]

    return documents
