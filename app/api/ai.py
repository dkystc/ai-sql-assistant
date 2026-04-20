"""AI REST 接口"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.models.schemas import (
    ChatRequest, SqlRequest, Nl2SqlRequest,
    ChatResponse, Nl2SqlResponse, StatusResponse,
    SessionInfo, SessionCreateResponse, SessionDetailResponse,
)
from app.services.ai_service import AiService
from app.services.llm_provider import get_provider
from app.services.session_manager import session_manager


router = APIRouter(prefix="/api/ai", tags=["AI 辅助开发"])


def get_ai_service() -> AiService:
    provider = get_provider(settings.default_provider, settings)
    return AiService(provider)


# ========== 非流式端点 ==========

@router.post("/chat", response_model=ChatResponse, summary="AI 对话")
def chat(req: ChatRequest, service: AiService = Depends(get_ai_service)):
    if not req.message.strip():
        raise HTTPException(400, "消息不能为空")
    try:
        result = service.chat(req.message, req.context, req.session_id)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(500, f"AI 调用失败: {e}")


@router.post("/explain", response_model=ChatResponse, summary="SQL 解释")
def explain(req: SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.sql.strip():
        raise HTTPException(400, "SQL 不能为空")
    try:
        return ChatResponse(reply=service.explain_sql(req.sql))
    except Exception as e:
        raise HTTPException(500, f"AI 调用失败: {e}")


@router.post("/optimize", response_model=ChatResponse, summary="SQL 优化")
def optimize(req: SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.sql.strip():
        raise HTTPException(400, "SQL 不能为空")
    try:
        return ChatResponse(reply=service.optimize_sql(req.sql))
    except Exception as e:
        raise HTTPException(500, f"AI 调用失败: {e}")


@router.post("/nl2sql", response_model=Nl2SqlResponse, summary="自然语言转 SQL")
def nl2sql(req: Nl2SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.question.strip():
        raise HTTPException(400, "问题不能为空")
    try:
        return Nl2SqlResponse(**service.nl2sql(req.question, req.table_schema))
    except Exception as e:
        raise HTTPException(500, f"AI 调用失败: {e}")


# ========== 流式端点 ==========

@router.post("/chat/stream", summary="AI 对话(流式)")
def chat_stream(req: ChatRequest, service: AiService = Depends(get_ai_service)):
    if not req.message.strip():
        raise HTTPException(400, "消息不能为空")

    def gen():
        try:
            for chunk in service.chat_stream(req.message, req.context, req.session_id):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/explain/stream", summary="SQL 解释(流式)")
def explain_stream(req: SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.sql.strip():
        raise HTTPException(400, "SQL 不能为空")

    def gen():
        try:
            for chunk in service.explain_sql_stream(req.sql):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/optimize/stream", summary="SQL 优化(流式)")
def optimize_stream(req: SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.sql.strip():
        raise HTTPException(400, "SQL 不能为空")

    def gen():
        try:
            for chunk in service.optimize_sql_stream(req.sql):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/nl2sql/stream", summary="自然语言转 SQL(流式)")
def nl2sql_stream(req: Nl2SqlRequest, service: AiService = Depends(get_ai_service)):
    if not req.question.strip():
        raise HTTPException(400, "问题不能为空")

    def gen():
        try:
            for chunk in service.nl2sql_stream(req.question, req.table_schema):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ========== 会话管理端点(新增) ==========

@router.post("/sessions", response_model=SessionCreateResponse, summary="创建新会话")
def create_session():
    session_id = session_manager.create_session()
    return SessionCreateResponse(session_id=session_id)


@router.get("/sessions", response_model=list[SessionInfo], summary="列出所有会话")
def list_sessions():
    return session_manager.list_sessions()


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    summary="获取会话详情(含完整消息)",
)
def get_session_detail(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    return SessionDetailResponse(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        messages=session.messages,
    )


@router.delete("/sessions/{session_id}", summary="删除会话")
def delete_session(session_id: str):
    if not session_manager.delete_session(session_id):
        raise HTTPException(404, "会话不存在")
    return {"ok": True}


# ========== 状态端点 ==========

@router.get("/status", response_model=StatusResponse, summary="服务状态")
def status():
    return StatusResponse(
        available=bool(settings.deepseek_api_key or settings.anthropic_api_key),
        provider=settings.default_provider,
        model=(settings.deepseek_model if settings.default_provider == "deepseek"
               else settings.anthropic_model),
    )
