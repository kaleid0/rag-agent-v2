from langchain_core.documents import Document

from src.rag.retriever import ChromaRetriever

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


# TODO 不够细致，粗略地扩展了 chunk IDs，可能会引入一些无关内容，可以更具 header 等信息进行更精细的扩展
async def context_retrieve(
    documents: list[Document], num_context: int = 3
) -> dict[str, list[Document]]:
    """
    基于初始检索到的文档片段（documents），根据它们的 record_id
    和 num_chunks 扩展上下文，然后获取所有扩展后的文档片段。
    """

    if not documents:
        return {}

    # 1. 按 collection_id 聚合 chunk IDs 和总片段数
    records_ids_chunk_ids = {}
    for doc in documents:
        collection_id = doc.metadata.get("collection_id")
        # 确保 num_chunks 是整数
        num_chunks = int(doc.metadata.get("num_chunks", 0))

        # 忽略没有 collection_id 或 num_chunks 小于等于 0 的文档
        if not collection_id or num_chunks <= 0:
            continue

        if collection_id not in records_ids_chunk_ids:
            records_ids_chunk_ids[collection_id] = {
                "chunk_ids": [],
                "num_chunks": num_chunks,
            }

        records_ids_chunk_ids[collection_id]["chunk_ids"].append(doc.id)

    # 如果聚合后没有有效记录，则返回空列表
    if not records_ids_chunk_ids:
        return {}

    all_extended_chunk_ids = []

    # 2. 遍历每个 record_id，扩展 chunk IDs
    for record_id, info in records_ids_chunk_ids.items():
        # 扩展 chunk ids
        extended_chunk_ids = extend_array(
            info["chunk_ids"],
            n=num_context,
            min_range=0,
            max_range=info["num_chunks"] - 1,
        )  # XXX

        # 将所有 record 的扩展 ID 收集起来
        all_extended_chunk_ids.append(extended_chunk_ids)

    # 4. 调用 get_by_ids 获取所有扩展后的文档
    retriever = ChromaRetriever(list(records_ids_chunk_ids.keys()), language={})  # XXX
    retrieved_documents = await retriever.get_by_ids(
        record_ids=list(records_ids_chunk_ids.keys()), ids=all_extended_chunk_ids
    )

    return retrieved_documents


def extend_array(
    arr: list[int | str], n: int, min_range: int, max_range: int
) -> list[str]:
    """
    对数组中的每个元素进行前后 n 位的整数扩展，并进行去重和范围限制。

    Args:
        arr: 原始整数数组。
        n: 扩展的位数（向前和向后）。
        min_range: 允许的最小范围值。
        max_range: 允许的最大范围值。

    Returns:
        包含所有扩展和原始元素的、已排序的列表。
    """

    # 使用集合（Set）来存储结果，自动实现去重
    result_set = set()

    for element in arr:
        # 1. 首先添加原始元素本身
        element = int(element)  # 确保元素是整数
        if min_range <= element <= max_range:
            result_set.add(element)

        # 2. 遍历 -n 到 n，计算扩展值
        for j in range(-n, n + 1):
            # 排除 j=0 的情况（因为 j=0 就是 element 本身，已在上面添加）
            if j == 0:
                continue

            extended_value = element + j

            # 3. 范围检查：确保扩展值在 [min_range, max_range] 范围内
            if min_range <= extended_value <= max_range:
                # 4. 添加到集合中，Set 会自动处理重复值
                result_set.add(extended_value)

    # 5. 将集合转换为列表并进行排序
    result_list = sorted(result_set)

    return [str(res) for res in result_list]
