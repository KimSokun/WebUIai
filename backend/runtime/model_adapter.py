import json
import httpx
from typing import AsyncGenerator, Dict, Any, List, Optional
from pydantic import BaseModel
from backend.config import system_config

class ModelCapabilities(BaseModel):
    model_name: str
    context_length: int = 102400
    supports_native_tools: bool = False
    chat_template: Optional[str] = None
    build_info: Optional[str] = None
    server_online: bool = False

class ModelAdapter:
    """
    Model-Agnostic GGUF Transport and Capability Adapter:
    Abstracts communication with llama-server on port 8080.
    Does NOT depend on specific model architectures or family names.
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or system_config.model.llama_server_url
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0)
            self._client = httpx.AsyncClient(limits=limits)
        return self._client

    async def aclose(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def detect_capabilities(self) -> ModelCapabilities:
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                if s.connect_ex(("127.0.0.1", 8080)) != 0:
                    return ModelCapabilities(
                        model_name=system_config.model.model_name,
                        context_length=system_config.model.context_length,
                        supports_native_tools=False,
                        server_online=False
                    )
        except Exception:
            pass

        try:
            client = self._get_client()
            res = await client.get(f"{self.base_url}/props", timeout=1.5)
            if res.status_code == 200:
                data = res.json()
                caps = data.get("chat_template_caps", {})
                n_ctx = data.get("default_generation_settings", {}).get("n_ctx", system_config.model.context_length)
                model_name = data.get("model_alias", system_config.model.model_name)
                supports_tools = bool(caps.get("supports_tools") or caps.get("supports_tool_calls"))
                return ModelCapabilities(
                    model_name=model_name,
                    context_length=n_ctx,
                    supports_native_tools=supports_tools,
                    chat_template=data.get("chat_template"),
                    build_info=data.get("build_info"),
                    server_online=True
                )
        except Exception:
            pass

        return ModelCapabilities(
            model_name=system_config.model.model_name,
            context_length=system_config.model.context_length,
            supports_native_tools=False,
            server_online=False
        )

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: int = 4096,
        timeout: float = 120.0
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Universal streaming generator for any compatible GGUF model via OpenAI-compatible endpoint.
        Yields chunks: {'type': 'token' or 'reasoning' or 'error', 'content': str}
        """
        model_messages = []
        if system_prompt:
            model_messages.append({"role": "system", "content": system_prompt})
        model_messages.extend(messages)

        payload = {
            "model": system_config.model.model_name,
            "messages": model_messages,
            "temperature": temperature if temperature is not None else system_config.model.temperature,
            "top_p": top_p if top_p is not None else system_config.model.top_p,
            "stream": True,
            "max_tokens": min(max_tokens, 2048),
            "stop": ["<|im_end|>", "<|endoftext|>", "</s>"]
        }

        try:
            client = self._get_client()
            async with client.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload, timeout=timeout) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        yield {"type": "error", "content": f"Server error ({response.status_code}): {err_body.decode(errors='replace')}"}
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if not choices:
                                    if chunk.get("timings") or chunk.get("usage"):
                                        yield {
                                            "type": "timings",
                                            "timings": chunk.get("timings"),
                                            "usage": chunk.get("usage")
                                        }
                                    continue
                                delta = choices[0].get("delta", {})

                                # Handle reasoning_content if present
                                reasoning = delta.get("reasoning_content", "")
                                if reasoning:
                                    yield {"type": "reasoning", "content": reasoning}

                                content = delta.get("content", "")
                                if content:
                                    yield {"type": "token", "content": content}

                                # Also yield timings if present on chunk with choices
                                if chunk.get("timings") or chunk.get("usage"):
                                    yield {
                                        "type": "timings",
                                        "timings": chunk.get("timings"),
                                        "usage": chunk.get("usage")
                                    }
                            except json.JSONDecodeError:
                                continue
        except httpx.ConnectError:
            yield {"type": "error", "content": f"Connection refused to llama-server at {self.base_url}. Ensure llama-server is running."}
        except httpx.TimeoutException as te:
            yield {"type": "error", "content": f"Request timed out waiting for model response ({type(te).__name__})."}
        except Exception as e:
            err_msg = str(e) or repr(e)
            yield {"type": "error", "content": f"Model adapter stream error: {err_msg}"}

model_adapter = ModelAdapter()
