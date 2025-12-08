"""FastAPI 主应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from src.session import Session, LongTermMemory
from src.document import DocumentRecord
import src.document.odm.DocumentRecord as dr
from src.rag import KnowledgeBase, CollectionRecord
from src.prompt import load_all_prompts

from config import mongo_cfg
from .routers import chat, document, knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的生命周期管理"""
    # 启动时: 初始化数据库连接
    mongo_uri = mongo_cfg.get("uri", "mongodb://localhost:27017")
    database_name = mongo_cfg.get("database", "rag_agent")

    client = AsyncIOMotorClient(mongo_uri)
    db = client[database_name]

    # 初始化 Beanie ODM
    await init_beanie(
        database=db,  # type: ignore
        document_models=[
            Session,
            KnowledgeBase,
            DocumentRecord,
            CollectionRecord,
            LongTermMemory,
        ],
    )

    print(f"✅ Connected to MongoDB: {database_name}")

    # 加载提示模板
    load_all_prompts()

    # 加载id-title映射
    records = await DocumentRecord.find_all().to_list()
    dr.id_title_mapping = {
        str(record.id): record.title for record in records if record.title
    }

    yield

    # 关闭时: 清理资源
    client.close()
    print("✅ Closed MongoDB connection")


# 创建 FastAPI 应用
app = FastAPI(
    title="RAG Chatbot API",
    description="基于RAG的对话机器人后端API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(knowledge_base.router, prefix="/api/v1", tags=["Knowledge Base"])
app.include_router(document.router, prefix="/api/v1", tags=["Document Management"])


@app.get("/")
async def root():
    """健康检查端点"""
    return {
        "message": "RAG Chatbot API is running",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.on_event("startup")
async def preload_mapping():
    global id_title_mapping
    records = await DocumentRecord.find_all().to_list()
    id_title_mapping = {
        str(record.id): record.title for record in records if record.title
    }
