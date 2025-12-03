"""知识库相关的 API 路由"""

from fastapi import APIRouter, HTTPException

from typing import List

from src.api.models import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
    FileRecordResponse,
    SuccessResponse,
)
from src.rag import KnowledgeBase, knowledge_base_service as kb_service
from src.document import DocumentRecord, id_to_title, document_service as doc_service


router = APIRouter()


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(request: KnowledgeBaseCreateRequest):
    """创建新的知识库"""
    try:
        kb = await kb_service.create_knowledge_base(
            name=request.name,
            description=request.description,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            split_method=request.split_method,
            retriever_type=request.retriever_type,
            document_record_ids=request.record_ids,
        )

        return KnowledgeBaseResponse(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            record_ids=[str(rid) for rid in kb.document_record_ids],
            created_at=kb.created_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create knowledge base: {str(e)}"
        )


@router.get("/knowledge-bases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(skip: int = 0, limit: int = 100):
    """获取知识库列表"""
    try:
        knowledge_bases = (
            await KnowledgeBase.find_all().skip(skip).limit(limit).sort(KnowledgeBase.created_at).to_list()  # type: ignore
        )
        total = await KnowledgeBase.find_all().count()

        return KnowledgeBaseListResponse(
            total=total,
            knowledge_base_list=[
                KnowledgeBaseResponse(
                    id=str(kb.id),
                    name=kb.name,
                    description=kb.description,
                    record_ids=[str(rid) for rid in kb.document_record_ids],
                    record_titles=[
                        await id_to_title(str(rid)) for rid in kb.document_record_ids
                    ],
                    created_at=kb.created_at,
                )
                for kb in knowledge_bases
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list knowledge bases: {str(e)}"
        )


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(kb_id: str):
    """获取知识库详情"""
    try:
        kb = await KnowledgeBase.get(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        return KnowledgeBaseResponse(
            id=str(kb.id),
            name=kb.name,
            description=kb.description,
            record_ids=[str(rid) for rid in kb.document_record_ids],
            created_at=kb.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge base: {str(e)}"
        )


@router.delete("/knowledge-bases/{kb_id}", response_model=SuccessResponse)
async def delete_knowledge_base(kb_id: str):
    """删除知识库"""
    try:
        kb = await KnowledgeBase.get(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        await kb.delete()
        return SuccessResponse(message="Knowledge base deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete knowledge base: {str(e)}"
        )


@router.get("/knowledge-bases/{kb_id}/files", response_model=List[FileRecordResponse])
async def list_files_in_knowledge_base(kb_id: str):
    """获取知识库中的所有文件"""
    try:
        kb = await KnowledgeBase.get(kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        files = []
        for record_id in kb.document_record_ids:
            file_record = await DocumentRecord.get(record_id)
            if file_record:
                files.append(
                    FileRecordResponse(
                        id=str(file_record.id),
                        title=file_record.filename,
                        knowledge_base_id=kb_id,
                        chunks_count=(
                            len(file_record.chunks)
                            if hasattr(file_record, "chunks")
                            else None
                        ),
                        metadata=(
                            file_record.metadata
                            if hasattr(file_record, "metadata")
                            else None
                        ),
                        created_at=(
                            file_record.created_at
                            if hasattr(file_record, "created_at")
                            else None
                        ),
                    )
                )

        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/knowledge-bases/{kb_id}/files/{file_id}", response_model=SuccessResponse)
async def add_file_to_knowledge_base(kb_id: str, file_id: str):
    """将文件添加到知识库"""
    try:
        await kb_service.add_record_to_knowledge_base(
            knowledge_base_id=kb_id,
            document_record_id=file_id,
        )
        return SuccessResponse(message="File added to knowledge base successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add file: {str(e)}")


@router.post("/knowledge-bases/{kb_id}/files", response_model=SuccessResponse)
async def add_multiple_files_to_knowledge_base(
    kb_id: str, file_ids: List[str]
) -> SuccessResponse:
    """将多个文件添加到知识库"""
    try:
        for file_id in file_ids:
            await kb_service.add_record_to_knowledge_base(
                knowledge_base_id=kb_id,
                document_record_id=file_id,
            )
        return SuccessResponse(message="Files added to knowledge base successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add files: {str(e)}")


@router.delete(
    "/knowledge-bases/{kb_id}/files/{file_id}", response_model=SuccessResponse
)
async def remove_file_from_knowledge_base(kb_id: str, file_id: str):
    """从知识库中移除文件"""
    try:
        await kb_service.remove_record_from_knowledge_base(
            knowledge_base_id=kb_id,
            document_record_id=file_id,
        )
        return SuccessResponse(message="File removed from knowledge base successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove file: {str(e)}")
