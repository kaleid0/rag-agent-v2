from langchain_core.documents import Document


def remove_duplicates(doucuments: list[Document]) -> list[Document]:
    """根据 record_id 和 id 去重两个 Document 列表"""
    seen_contents = set()
    unique_documents = []

    for doc in doucuments:
        if (doc.id, doc.metadata.get("record_id")) not in seen_contents:
            seen_contents.add((doc.id, doc.metadata.get("record_id")))
            unique_documents.append(doc)

    return unique_documents


def organize_context(documents: dict[str, list[Document]]) -> str:
    """将 Document 列表组织成纯文本，并合并相邻同 header 的片段。"""

    organized_texts = []

    for record_id, docs in documents.items():
        if not docs:
            organized_texts.append(f"=== 文档（ID: {record_id}）无内容 ===\n")
            continue

        record_title = docs[0].metadata.get("document_title", "未知文档")
        organized_texts.append(f"=== 文档标题: {record_title} ===")

        # 1. 合并相邻 header 相同的片段
        merged_sections = []  # list[(header, content)]

        prev_header = None
        buffer_content = []

        for doc in docs:
            header = doc.metadata.get("header") or "未命名章节"
            content = doc.page_content.strip()

            if header == prev_header:
                # 和上一个章节同名 → 累积
                buffer_content.append(content)
            else:
                # 若 header 改变，把前面累积的存进结果
                if prev_header is not None:
                    merged_sections.append((prev_header, "\n".join(buffer_content)))
                # 开始新的 buffer
                prev_header = header
                buffer_content = [content]

        # 别忘记最后一个
        if prev_header is not None:
            merged_sections.append((prev_header, "\n".join(buffer_content)))

        # 2. 输出文本
        for header, content in merged_sections:
            organized_texts.append(f"\n--- 章节: {header} ---\n{content}")

        organized_texts.append("\n")

    return "\n".join(organized_texts).strip()
