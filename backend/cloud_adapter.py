import os
import asyncio
from typing import AsyncGenerator, Dict, Any, List
import dotenv
import logging
from backend.config import system_config
from google import genai

logger = logging.getLogger("cloud_bridge")

class CloudBridge:
    """
    Cloud bridge permanently disabled per Owner instruction.
    100% strictly local GGUF execution only.
    """
    def __init__(self):
        self.enabled = False
        self._keys = []
        self._current_key_idx = 0
        self.model_candidates = []
        self.model_name = ""
        self._current_key_idx = 0
        env_model = os.getenv("GEMINI_MODEL")
        candidates = []
        if env_model and env_model not in ["gemini-3.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]:
            candidates.append(env_model)
        for m in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]:
            if m not in candidates:
                candidates.append(m)
        self.model_candidates = candidates
        self.model_name = self.model_candidates[0]

    def _get_client(self) -> genai.Client:
        if not self._keys:
            raise RuntimeError("No Gemini API keys found.")
        key = self._keys[self._current_key_idx]
        return genai.Client(api_key=key)

    def _rotate_key(self):
        if self._keys:
            self._current_key_idx = (self._current_key_idx + 1) % len(self._keys)

    @staticmethod
    def _is_capacity_error(err_str: str) -> bool:
        """Returns True if the error is due to model-tier demand spikes (503 UNAVAILABLE)."""
        upper = err_str.upper()
        return any(ind in upper for ind in ["503", "UNAVAILABLE", "HIGH DEMAND", "OVERLOADED"])

    @staticmethod
    def _is_transient_error(err_str: str) -> bool:
        """Returns True if the error is temporary/retriable across keys or models."""
        upper = err_str.upper()
        return any(ind in upper for ind in [
            "503", "UNAVAILABLE", "HIGH DEMAND", "RESOURCE_EXHAUSTED", "429",
            "500", "502", "504", "TIMEOUT", "DEADLINE"
        ])

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        from google.genai import types

        if not self.enabled or not getattr(system_config.model, "cloud_api_enabled", False) or not self._keys:
            return

        # Prepare messages
        contents = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            text_val = m.get("content", "")
            if text_val:
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(text_val))]))

        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Hello")]))

        config = types.GenerateContentConfig(
            system_instruction=system_prompt or "You are K-Jocker, an advanced Cambodia AI assistant created for Kimsokun (Owner)."
        )

        yielded_any = False

        # Cascade through model candidates if demand spikes or errors occur
        for model in self.model_candidates:
            if yielded_any:
                break

            for attempt in range(len(self._keys)):
                try:
                    client = self._get_client()
                    loop = asyncio.get_running_loop()
                    queue = asyncio.Queue()
                    sentinel = object()

                    def _producer(active_model=model):
                        try:
                            response_stream = client.models.generate_content_stream(
                                model=active_model,
                                contents=contents,
                                config=config
                            )
                            for chunk in response_stream:
                                if chunk.text:
                                    loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
                        except Exception as ex:
                            loop.call_soon_threadsafe(queue.put_nowait, ex)
                        finally:
                            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

                    producer_future = loop.run_in_executor(None, _producer)

                    should_retry_key = False
                    should_fallback_model = False

                    while True:
                        item = await queue.get()
                        if item is sentinel:
                            break
                        if isinstance(item, Exception):
                            err_str = str(item)
                            # If tokens already started flowing to user, don't cascade mid-response
                            if yielded_any:
                                return
                            if self._is_capacity_error(err_str):
                                # 503 UNAVAILABLE is model-specific -> immediate cascade to next fallback model
                                should_fallback_model = True
                                break
                            elif self._is_transient_error(err_str):
                                # 429 or quota -> rotate key and retry
                                self._rotate_key()
                                should_retry_key = True
                                break
                            else:
                                # Other errors -> cascade model
                                should_fallback_model = True
                                break

                        yielded_any = True
                        yield item

                    await producer_future

                    if should_fallback_model:
                        break  # Break inner key loop, advance to next candidate model
                    if should_retry_key:
                        continue  # Try next key for current model

                    # If completed successfully without errors
                    return

                except Exception as e:
                    err_str = str(e)
                    if yielded_any:
                        return
                    if self._is_capacity_error(err_str):
                        break
                    elif self._is_transient_error(err_str):
                        self._rotate_key()
                        continue
                    else:
                        break

cloud_bridge = CloudBridge()
