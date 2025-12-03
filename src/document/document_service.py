import hashlib
import os
import uuid
from fastapi import File, HTTPException, UploadFile
from pathlib import Path
from beanie.odm.operators.update.general import Set
from beanie.odm.operators.update.array import Pop

from .odm.DocumentRecord import DocumentRecord, StatusEnum
from src.rag import KnowledgeBase
from .parse import parse
from config import rag_cfg


async def list_document_records() -> list[DocumentRecord]:
    """列出所有文件记录。

    Returns:
        list[DocumentRecord]: 文件记录列表。
    """
    document_records = await DocumentRecord.find_all().to_list()
    return document_records


async def delete_document_record(document_record_id: str):
    """删除指定的文件记录。

    Args:
        record_id (str): 文件记录ID。
    """
    document_record = await DocumentRecord.get(document_record_id)
    if not document_record:
        raise ValueError("File record not found")

    for kb_id in document_record.knowledge_base_ids:
        kb = await KnowledgeBase.find_one(KnowledgeBase.id == kb_id)
        if kb:
            await kb.update(Pop({KnowledgeBase.document_record_ids: document_record_id}))  # type: ignore

    await document_record.delete()


async def upload_file(file: UploadFile = File(...)) -> DocumentRecord:
    """上传文件（≤10MB）"""

    filename = file.filename or "unknown_file"
    file_id = uuid.uuid4().hex
    ext = Path(filename).suffix
    new_filename = f"{file_id}{ext}"

    save_path = Path(rag_cfg["file_storage_path"]) / new_filename
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取全部内容
    content = await file.read()

    # 文件大小限制
    if len(content) > rag_cfg.get("max_file_size_mb", 10) * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    # 计算 MD5
    file_hash = hashlib.md5(content).hexdigest()
    document_record = await DocumentRecord.find_one(
        DocumentRecord.file_hash == file_hash
    )
    if document_record:
        raise HTTPException(
            status_code=400, detail=f"File {document_record} already exists"
        )

    # 保存文件
    save_path.write_bytes(content)

    # 创建记录
    document_record = DocumentRecord(
        source=filename,
        storage_path=str(save_path),
        file_hash=file_hash,
        status=StatusEnum.pending,
    )
    await document_record.insert()

    return document_record


async def parse_file(document_record_id: str):
    """解析上传的文件，转换为Markdown格式"""
    document_record = await DocumentRecord.get(document_record_id)
    if not document_record:
        raise ValueError("File record not found")
    # 解析
    try:
        output_dir = Path(rag_cfg["markdown_storage_path"])
        os.makedirs(output_dir, exist_ok=True)
        markdown_filename = Path(document_record.storage_path).with_suffix(".md").name
        output_path = output_dir / markdown_filename

        parse_result = await parse(document_record.storage_path, str(output_path))

        document_record.markdown_path = str(output_path)
        document_record.title = parse_result.title
        document_record.abstract = parse_result.abstract
        document_record.keywords = parse_result.keywords
        document_record.directory = parse_result.directory
        document_record.language = parse_result.language
        document_record.status = StatusEnum.parse_completed

        await document_record.save_changes()

    except Exception as e:
        document_record.status = StatusEnum.failed
        await document_record.update(Set({DocumentRecord.status: StatusEnum.failed}))
        raise e
