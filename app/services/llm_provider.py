"""LLM Provider 抽象层

Java 版用一个布尔变量区分 OpenAI 和 Anthropic 协议,代码里两处 if-else。
Python 版用抽象基类 + 多态,扩展新 provider 只需加一个子类。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Iterator
from openai import OpenAI


class LLMProvider(ABC):
    """LLM 调用抽象基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 4096) -> str:
        """非流式对话。返回完整回复字符串。"""
        raise NotImplementedError

    @abstractmethod
    def chat_stream(
        self, messages: List[Dict[str, str]], max_tokens: int = 4096
    ) -> Iterator[str]:
        """流式对话。返回生成器,每次 yield 一小段文本(通常是 1-2 个字符)。"""
        raise NotImplementedError


class DeepSeekProvider(LLMProvider):
    """DeepSeek 调用实现(OpenAI 兼容协议)"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 4096) -> str:
        """非流式 - 一次返回完整结果"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def chat_stream(
        self, messages: List[Dict[str, str]], max_tokens: int = 4096
    ) -> Iterator[str]:
        """流式 - 用生成器逐块返回

        OpenAI SDK 加 stream=True 后返回一个 Stream 对象,迭代它就能拿到每个 chunk。
        每个 chunk 里的 delta.content 是新增的文本片段。
        """
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,  # 关键!
        )
        for chunk in stream:
            # 防御性判断:有时 chunk 没有 choices(最后的 usage 统计块)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


class AnthropicProvider(LLMProvider):
    """Anthropic 调用实现 - 留口"""

    def __init__(self, api_key: str, base_url: str, model: str):
        raise NotImplementedError("AnthropicProvider 暂未实现")

    def chat(self, messages, max_tokens=4096):
        raise NotImplementedError

    def chat_stream(self, messages, max_tokens=4096):
        raise NotImplementedError


def get_provider(name: str, settings) -> LLMProvider:
    if name == "deepseek":
        return DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
    elif name == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
        )
    else:
        raise ValueError(f"未知的 provider: {name}")
