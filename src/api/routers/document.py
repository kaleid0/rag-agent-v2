"""文档管理相关的 API 路由"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from src.api.models import (
    DocumentListResponse,
    FileRecordResponse,
    SuccessResponse,
)
from src.document import document_service as doc_service


router = APIRouter()


@router.get("/document", response_model=DocumentListResponse)
async def list_document_records():
    """列出所有文件记录"""
    try:
        document_records = await doc_service.list_document_records()
        return DocumentListResponse(
            total=len(document_records),
            documents=[
                FileRecordResponse(
                    id=str(record.id),
                    source=record.source,
                    metadata=record.metadata,
                    created_at=record.created_at,
                )
                for record in document_records
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list document records: {str(e)}"
        )


@router.post("/document/upload", response_model=FileRecordResponse, status_code=201)
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """上传文件并添加到知识库"""
    try:
        document_record = await doc_service.upload_file(file=file)
        # 不需要多线程，内部 CPU 密集型操作已使用 asyncio.run 处理
        background_tasks.add_task(doc_service.parse_file, str(document_record.id))

        return FileRecordResponse(
            id=str(document_record.id),
            source=document_record.source,
            created_at=(
                document_record.created_at
                if hasattr(document_record, "created_at")
                else None
            ),
            metadata=document_record.metadata,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


# TODO 清理本地文件（markdown，chroma...）
@router.delete("/document/{record_id}", response_model=SuccessResponse)
async def delete_document_record(record_id: str):
    """删除指定的文件记录"""
    try:
        await doc_service.delete_document_record(document_record_id=record_id)
        return SuccessResponse(message="File record deleted successfully")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete file record: {str(e)}"
        )
