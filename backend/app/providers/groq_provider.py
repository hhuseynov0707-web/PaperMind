"""Groq LLM provider — §18.

Bütün Groq-a xas detallar burada qalır: SDK, model adı, json rejimi, xəta
formatı. Biznes məntiqi (`rag/llm.py`, `rag/insights.py`, `rag/compare.py`)
yalnız `LLMProvider` protokolunu görür.
"""

from ..config import settings


class GroqLLM:
    name = "groq"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.groq_api_key
        self._model = model or settings.groq_model
        self._client = None

    def _ensure(self):
        # Tənbəl qurulum: açar olmayan mühitdə (test, CI) modulu import etmək
        # mümkün olmalıdır — xəta yalnız FAKTİKİ çağırışda atılır.
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("GROQ_API_KEY təyin olunmayıb")
            from groq import Groq
            self._client = Groq(api_key=self._api_key)
        return self._client

    def complete(self, system: str, user: str, *, temperature: float = 0.3,
                 max_tokens: int = 800, json_mode: bool = False,
                 model: str | None = None) -> str:
        kwargs = {
            "model": model or self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._ensure().chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
