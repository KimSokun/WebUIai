import json
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Any, Optional
from backend.config import CONFIG_DIR

VOICE_CONFIG_FILE = CONFIG_DIR / "voice_settings.json"

class VoiceSettings(BaseModel):
    enabled: bool = True
    stt_enabled: bool = True
    tts_enabled: bool = True
    auto_speak: bool = False
    language: str = "km-KH"
    fallback_language: str = "en-US"
    rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0

class VoiceManager:
    """Manages voice assistant configuration and client speech preferences."""
    def __init__(self, config_file: Path = VOICE_CONFIG_FILE):
        self.config_file = config_file
        self.settings = self.load_settings()

    def load_settings(self) -> VoiceSettings:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return VoiceSettings(**data)
            except Exception:
                pass
        s = VoiceSettings()
        self.save_settings(s)
        return s

    def save_settings(self, settings: VoiceSettings):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write(settings.model_dump_json(indent=2))
        self.settings = settings

    def update_settings(self, new_data: Dict[str, Any]) -> VoiceSettings:
        current_dict = self.settings.model_dump()
        current_dict.update(new_data)
        updated = VoiceSettings(**current_dict)
        self.save_settings(updated)
        return updated

    def get_config(self) -> Dict[str, Any]:
        return self.settings.model_dump()

    def update_config(self, **kwargs) -> Dict[str, Any]:
        return self.update_settings(kwargs).model_dump()

voice_manager = VoiceManager()

