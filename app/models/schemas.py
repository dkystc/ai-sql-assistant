"""请求/响应数据模型"""
from typing import Optional, List
from pydantic import BaseModel, Field


# ===== 请求模型 =====

class ChatRequest(BaseModel):
    """AI 对话请求"""
    message: str = Field(..., description="用户消息")
    context: Optional[str] = Field(None, description="上下文(可选)")
    session_id: Optional[str] = Field(None, description="会话 ID(可选),传了会带上历史")


class SqlRequest(BaseModel):
    sql: str = Field(..., description="要处理的 SQL")


class Nl2SqlRequest(BaseModel):
    question: str = Field(..., description="自然语言问题")
    table_schema: Optional[str] = Field(None, description="可选的表结构信息")


# ===== 响应模型 =====

class ChatResponse(BaseModel):
    reply: str
    session_id: Optional[str] = None


class Nl2SqlResponse(BaseModel):
    reply: str
    sql: Optional[str] = None


class StatusResponse(BaseModel):
    available: bool
    provider: str
    model: str


# ===== 会话管理 =====

class SessionInfo(BaseModel):
    """会话摘要(列表用)"""
    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    preview: str


class SessionCreateResponse(BaseModel):
    session_id: str


class SessionDetailResponse(BaseModel):
    """会话详情(包含完整消息)"""
    session_id: str
    created_at: str
    updated_at: str
    messages: List[dict]
