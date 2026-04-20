"""AI 业务逻辑 - 加入对话历史支持"""
import re
from typing import Optional, Iterator, List, Dict
from app.services.llm_provider import LLMProvider
from app.services.session_manager import session_manager, Session


SYSTEM_PROMPT = """你是一个专业的数据工程师 AI 助手,专注于 SQL 开发和数据分析。
你的职责:
1. 将自然语言需求转换为准确的 SQL 语句
2. 解释复杂的 SQL 语句含义
3. 优化 SQL 性能
4. 回答数据工程相关问题

规则:
- 默认使用 HiveSQL 语法(支持分区表、ORC 格式等),也能处理 MySQL/PostgreSQL
- SQL 语句用 ```sql 代码块包裹
- 回答简洁专业,中文回复"""


class AiService:
    """AI 业务服务"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    # ========== 非流式 ==========

    def chat(
        self,
        user_message: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """对话 - 返回 {reply, session_id}

        如果传了 session_id,自动拼接历史。
        如果没传,当作一次性问答(不保存)。
        """
        if session_id:
            session = session_manager.get_or_create(session_id)
            messages = self._build_messages_with_history(
                user_message, context, session
            )
            reply = self.provider.chat(messages)
            session_manager.append_turn(session.session_id, user_message, reply)
            return {"reply": reply, "session_id": session.session_id}
        else:
            messages = self._build_messages(user_message, context)
            reply = self.provider.chat(messages)
            return {"reply": reply, "session_id": None}

    def explain_sql(self, sql: str) -> str:
        """SQL 解释 - 单次任务,不需要历史"""
        msgs = self._build_messages(
            f"请解释以下 SQL 的含义,包括每个部分的作用:\n```sql\n{sql}\n```"
        )
        return self.provider.chat(msgs)

    def optimize_sql(self, sql: str) -> str:
        msgs = self._build_messages(
            f"请分析以下 SQL 的性能问题并给出优化建议:\n```sql\n{sql}\n```"
        )
        return self.provider.chat(msgs)

    def nl2sql(self, question: str, table_schema: Optional[str] = None) -> dict:
        context = f"以下是可用的表结构信息:\n{table_schema}" if table_schema else None
        prompt = (
            f"请根据以下需求生成 SQL 语句:\n{question}\n\n"
            "要求:只返回可执行的 SQL,用 ```sql 包裹。"
        )
        msgs = self._build_messages(prompt, context)
        reply = self.provider.chat(msgs)
        return {"reply": reply, "sql": self._extract_sql_block(reply)}

    # ========== 流式 ==========

    def chat_stream(
        self,
        user_message: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Iterator[str]:
        """流式对话 - 自动写入会话历史

        流式版本的特殊点:要边 yield 边累积完整回复,流结束后一次性写入 session。
        """
        if session_id:
            session = session_manager.get_or_create(session_id)
            messages = self._build_messages_with_history(
                user_message, context, session
            )
            full_reply = []
            for chunk in self.provider.chat_stream(messages):
                full_reply.append(chunk)
                yield chunk
            # 流结束后,一次性保存整轮对话
            session_manager.append_turn(
                session.session_id, user_message, "".join(full_reply)
            )
        else:
            messages = self._build_messages(user_message, context)
            yield from self.provider.chat_stream(messages)

    def explain_sql_stream(self, sql: str) -> Iterator[str]:
        msgs = self._build_messages(
            f"请解释以下 SQL 的含义,包括每个部分的作用:\n```sql\n{sql}\n```"
        )
        yield from self.provider.chat_stream(msgs)

    def optimize_sql_stream(self, sql: str) -> Iterator[str]:
        msgs = self._build_messages(
            f"请分析以下 SQL 的性能问题并给出优化建议:\n```sql\n{sql}\n```"
        )
        yield from self.provider.chat_stream(msgs)

    def nl2sql_stream(
        self, question: str, table_schema: Optional[str] = None
    ) -> Iterator[str]:
        context = f"以下是可用的表结构信息:\n{table_schema}" if table_schema else None
        prompt = (
            f"请根据以下需求生成 SQL 语句:\n{question}\n\n"
            "要求:只返回可执行的 SQL,用 ```sql 包裹。"
        )
        msgs = self._build_messages(prompt, context)
        yield from self.provider.chat_stream(msgs)

    # ========== 工具方法 ==========

    @staticmethod
    def _build_messages(
        user_message: str, context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """无历史版本 - 解释/优化/nl2sql 用"""
        full_message = user_message
        if context:
            full_message = f"当前上下文:\n{context}\n\n用户问题:{user_message}"
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_message},
        ]

    @staticmethod
    def _build_messages_with_history(
        user_message: str,
        context: Optional[str],
        session: Session,
    ) -> List[Dict[str, str]]:
        """有历史版本 - system + 历史 messages + 当前 user

        结构:
        [
          {"role": "system", "content": SYSTEM_PROMPT},
          {"role": "user", "content": "上一轮问题"},
          {"role": "assistant", "content": "上一轮回答"},
          ... (更多历史)
          {"role": "user", "content": "本次问题"}
        ]
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # 带上历史消息
        messages.extend(session.messages)
        # 追加当前消息
        full_message = user_message
        if context:
            full_message = f"当前上下文:\n{context}\n\n用户问题:{user_message}"
        messages.append({"role": "user", "content": full_message})
        return messages

    @staticmethod
    def _extract_sql_block(text: str) -> Optional[str]:
        match = re.search(r"```sql\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def is_available(self) -> bool:
        return self.provider is not None
