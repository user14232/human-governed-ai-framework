from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


class LLMClientError(RuntimeError):
    """Raised when the LLM HTTP request fails or returns a non-200 status."""


class LLMResponseParseError(LLMClientError):
    """Raised when the LLM response body cannot be parsed into a text completion."""


@dataclass(frozen=True)
class LLMClientConfig:
    api_url: str
    api_key: str
    model: str
    timeout_seconds: int


def llm_client_from_env() -> "LLMClient":
    """
    Construct an LLMClient from environment variables.

    Required environment variables:
        DEVOS_LLM_API_URL  — base URL, e.g. https://api.openai.com
        DEVOS_LLM_API_KEY  — bearer token / API key

    Optional:
        DEVOS_LLM_MODEL    — model name, defaults to gpt-4o
        DEVOS_LLM_TIMEOUT  — HTTP timeout in seconds, defaults to 120
    """
    api_url = os.environ.get("DEVOS_LLM_API_URL", "").rstrip("/")
    api_key = os.environ.get("DEVOS_LLM_API_KEY", "")
    model = os.environ.get("DEVOS_LLM_MODEL", "gpt-4o")
    timeout = int(os.environ.get("DEVOS_LLM_TIMEOUT", "120"))

    if not api_url:
        raise LLMClientError(
            "DEVOS_LLM_API_URL is not set. "
            "Set it to an OpenAI-compatible API base URL before running in automated mode."
        )
    if not api_key:
        raise LLMClientError(
            "DEVOS_LLM_API_KEY is not set. "
            "Set it to your API key before running in automated mode."
        )

    config = LLMClientConfig(
        api_url=api_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout,
    )
    return LLMClient(config)


class LLMClient:
    """
    Minimal stateless LLM client for OpenAI-compatible chat completion APIs.

    Isolation contract:
    - Only this module contains HTTP transport logic.
    - Kernel modules must not import from this module.
    - The kernel stays provider-independent.
    """

    def __init__(self, config: LLMClientConfig) -> None:
        self._config = config

    def generate(self, prompt: str) -> str:
        """
        Send a single prompt and return the text completion.

        The prompt is sent as a user message in a zero-shot chat completion request.
        Returns the raw text content of the first completion choice.

        Raises LLMClientError on HTTP errors.
        Raises LLMResponseParseError if the response body is unexpected.
        """
        endpoint = f"{self._config.api_url}/v1/chat/completions"
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(
                f"LLM API returned HTTP {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"LLM API connection error: {exc.reason}") from exc

        return self._extract_text(raw, endpoint)

    def _extract_text(self, raw: str, endpoint: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseParseError(
                f"LLM response from {endpoint} is not valid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise LLMResponseParseError("LLM response is not a JSON object.")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMResponseParseError(
                f"LLM response contains no choices. Response keys: {list(data.keys())}"
            )

        first = choices[0]
        if not isinstance(first, dict):
            raise LLMResponseParseError("LLM response 'choices[0]' is not an object.")

        message = first.get("message")
        if not isinstance(message, dict):
            raise LLMResponseParseError("LLM response 'choices[0].message' is not an object.")

        content = message.get("content")
        if not isinstance(content, str):
            raise LLMResponseParseError(
                f"LLM response 'choices[0].message.content' is not a string: {type(content)}"
            )

        return content
