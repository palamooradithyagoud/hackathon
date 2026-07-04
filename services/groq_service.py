"""
Groq LLM service abstraction layer.
Provides a modular interface for LLM generation that can be swapped to other providers.
"""

from groq import Groq

from core.config import settings
from core.logger import logger


class GroqService:
    """Abstracted LLM provider using Groq API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model = model or settings.GROQ_MODEL
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not configured in .env")
        self._client = Groq(api_key=self._api_key)

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        """Generate a response from the LLM."""
        logger.debug(f"Groq request: model={self._model}, temp={temperature}")
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug(f"Groq response: {len(content)} chars")
            return content
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "rate limit" in error_str:
                for fallback_model in ["llama-3.1-8b-instant", "qwen/qwen3-32b"]:
                    if fallback_model == self._model:
                        continue
                    logger.warning(f"Groq rate limit hit for {self._model}. Retrying with: {fallback_model}")
                    try:
                        response = self._client.chat.completions.create(
                            model=fallback_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        return response.choices[0].message.content
                    except Exception:
                        continue
                raise RuntimeError(
                    "Groq API daily token quota exhausted on all models. "
                    "Please wait ~14 minutes for the per-minute limit to reset, or use a new API key."
                )
            logger.error(f"Groq API error: {e}")
            raise

    def generate_with_history(
        self,
        messages: list[dict],
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1500,
    ) -> str:
        """Generate a response with full message history."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "rate limit" in error_str:
                for fallback_model in ["llama-3.1-8b-instant", "qwen/qwen3-32b"]:
                    if fallback_model == self._model:
                        continue
                    logger.warning(f"Groq rate limit hit for {self._model}. Retrying with: {fallback_model}")
                    try:
                        response = self._client.chat.completions.create(
                            model=fallback_model,
                            messages=full_messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        return response.choices[0].message.content
                    except Exception:
                        continue
                raise RuntimeError(
                    "Groq API daily token quota exhausted on all models. "
                    "Please wait ~14 minutes for the per-minute limit to reset, or use a new API key."
                )
            logger.error(f"Groq API error: {e}")
            raise

    def generate_json(
        self,
        user_prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        """Generate a response in JSON format."""
        logger.debug(f"Groq JSON request: model={self._model}, temp={temperature}")
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return content
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "rate limit" in error_str:
                for fallback_model in ["llama-3.1-8b-instant", "qwen/qwen3-32b"]:
                    if fallback_model == self._model:
                        continue
                    logger.warning(f"Groq rate limit hit for {self._model}. Retrying JSON with: {fallback_model}")
                    try:
                        response = self._client.chat.completions.create(
                            model=fallback_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens,
                            response_format={"type": "json_object"},
                        )
                        return response.choices[0].message.content
                    except Exception:
                        continue
                raise RuntimeError(
                    "Groq API daily token quota exhausted on all models. "
                    "Please wait ~14 minutes for the per-minute limit to reset, or use a new API key."
                )
            logger.error(f"Groq API error: {e}")
            raise

