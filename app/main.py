"""FastAPI 启动入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api import ai


app = FastAPI(
    title="AI SQL Assistant",
    description="迷你版 DataNote AI - DeepSeek + FastAPI",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂 AI 路由
app.include_router(ai.router)


@app.get("/api/health")
def health():
    """API 健康检查(原来的 / 路由移到这里)"""
    return {
        "name": "AI SQL Assistant",
        "status": "running",
        "provider": settings.default_provider,
    }


@app.get("/")
def index():
    """首页 - 返回 static/index.html"""
    return FileResponse("static/index.html")


# 挂静态文件 - 方便后续扩展(放图片、字体等)
app.mount("/static", StaticFiles(directory="static"), name="static")
