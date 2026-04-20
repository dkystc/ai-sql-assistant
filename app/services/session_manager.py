"""会话历史管理 - 让 AI 拥有多轮对话记忆

存储策略:
- 内存字典存 {session_id: [消息列表]}
- 每个消息格式: {"role": "user"/"assistant", "content": "..."}
- 达到 max_turns 时自动丢弃最早的一轮(user+assistant 成对)

生产环境建议:
- 改用 Redis(支持多进程共享 + TTL)
- 或存数据库(持久化,支持审计)
- 加用户隔离(当前用户只能访问自己的会话)

但学习目的,内存版足够。
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock


class Session:
    """单个会话 - 包含完整历史"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.messages: List[Dict[str, str]] = []  # [{role, content}, ...]

    def add_message(self, role: str, content: str) -> None:
        """添加一条消息"""
        self.messages.append({"role": role, "content": content})
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """序列化为字典(给前端用)"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages),
            "preview": self._get_preview(),
        }

    def _get_preview(self) -> str:
        """获取第一条用户消息作为会话预览(类似 ChatGPT 侧边栏)"""
        for msg in self.messages:
            if msg["role"] == "user":
                text = msg["content"]
                return text[:40] + ("..." if len(text) > 40 else "")
        return "(空会话)"


class SessionManager:
    """会话管理器 - 全局单例。

    max_turns: 每个会话最多保留的"轮数"(1 轮 = 1 user + 1 assistant)
    超过后会自动丢弃最早的一轮,防止 token 无限增长。
    """

    def __init__(self, max_turns: int = 20):
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()  # 多线程安全(FastAPI 是异步/多线程的)
        self.max_turns = max_turns

    def create_session(self) -> str:
        """创建新会话,返回 session_id"""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = Session(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话,不存在返回 None"""
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        """传了 id 就用,没传就新建"""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        with self._lock:
            session = Session(new_id)
            self._sessions[new_id] = session
        return session

    def append_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """一次性添加一轮对话(user + assistant)

        这是大部分调用方需要的接口——一次请求对应一轮,原子操作。
        同时处理窗口截断。
        """
        session = self._sessions.get(session_id)
        if not session:
            return
        with self._lock:
            session.add_message("user", user_msg)
            session.add_message("assistant", assistant_msg)
            self._trim(session)

    def _trim(self, session: Session) -> None:
        """窗口截断:如果消息数超过 max_turns * 2,丢弃最早的若干轮"""
        max_messages = self.max_turns * 2
        if len(session.messages) > max_messages:
            excess = len(session.messages) - max_messages
            # 确保按"轮"丢弃(偶数个)
            excess = excess + (excess % 2)
            session.messages = session.messages[excess:]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> List[dict]:
        """列出所有会话(按更新时间倒序,ChatGPT 风格)"""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )
        return [s.to_dict() for s in sessions]


# 全局单例
session_manager = SessionManager(max_turns=20)
