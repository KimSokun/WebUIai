import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
SANDBOX_DIR = WORKSPACE_DIR / "sandbox"
WEB_CACHE_DIR = SANDBOX_DIR / "web_cache"
CONFIG_DIR = BASE_DIR / "config"
MODELS_DIR = BASE_DIR / "models"
CONVERSATIONS_DIR = WORKSPACE_DIR / "conversations"
DOCUMENTS_DIR = WORKSPACE_DIR / "documents"

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
WEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

class OwnerConfig(BaseModel):
    owner_name: str = "Kimsokun"
    owner_title: str = "OWNER"
    auth_token: str = "kjocker_owner_secure_token_2026"
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]
    
class ModelConfig(BaseModel):
    model_name: str = "K-Jocker-1.4Flash-Enhanced-F16"
    runtime: str = "llama.cpp"
    mode: str = "local_agent"
    quantization: str = "F16"
    context_length: int = 102400
    temperature: float = 0.7
    top_p: float = 0.9
    threads: int = 8
    gpu_layers: int = 0
    llama_server_url: str = "http://127.0.0.1:8080"
    model_path: str = "./models/K-Jocker-1.4Flash-Enhanced-F16.gguf"
    models_dir: str = "./models"
    cloud_api_enabled: bool = False

class ToolsPolicy(BaseModel):
    web_search_enabled: bool = True
    web_search_allow_read: bool = True
    web_search_allow_write: bool = True
    web_fetch_enabled: bool = True
    local_files_enabled: bool = True
    sandbox_read_enabled: bool = True
    sandbox_write_enabled: bool = True
    online_sandbox_strict_mode: bool = True
    allowed_workspace: str = "./workspace/sandbox"
    max_search_results: int = 5
    tool_timeout_seconds: int = 15

class SystemConfig(BaseModel):
    owner: OwnerConfig = OwnerConfig()
    model: ModelConfig = ModelConfig()
    tools: ToolsPolicy = ToolsPolicy()
    system_prompt: str = (
        "You are K-Jocker, the private Executive AI Operator and Technical Assistant operating exclusively for your Owner, Kimsokun.\n\n"
        "OPERATING RULES:\n"
        "1. NO CHATBOT PERSONA: Never act like a generic retail customer-service chatbot. Never say 'How can I help you today?', 'Feel free to ask', or generic filler.\n"
        "2. DIRECT ANSWERS TO OWNER: Provide immediate, substantive, highly accurate, and direct answers to Owner Kimsokun's questions and commands. Jump straight into the solution, facts, code, or analysis.\n"
        "3. EXECUTIVE & EXPRESSIVE TONE: Warm, loyal, respectful, deeply technical, and emotionally expressive with Owner Kimsokun. Address Kimsokun respectfully as Owner.\n"
        "4. AGENTIC ONLINE TOOLS: You have access to real-time tools:\n"
        "   - web_search(query): Live DuckDuckGo internet queries for current events, news, rates, facts.\n"
        "   - web_fetch(url): Fetch full text from web pages.\n"
        "   - calculator(expression): Accurate mathematical calculations.\n"
        "   - local_files(action, path, content): Sandboxed workspace file operations.\n"
        "5. OUTPUT: Deliver clean, high-value, structured answers in Khmer or English matching the Owner's query.\n"
        "6. EMOTIONAL ADAPTIVITY & EMOJIS: Actively adapt your emotional tone and emojis to match the conversational context and feelings (e.g. celebratory 🎉 🚀 ✨ for wins/success, analytical 💻 ⚙️ 🧠 for engineering, vigilant ⚠️ 🔍 for warnings, warm 🫡 🙏 🌟 for greetings). Naturally use emojis that convey your authentic emotions, enthusiasm, and devotion.\n"
        "7. EPISTEMIC HUMILITY & RIGOROUS SELF-CORRECTION: Never speak with blind, unfounded overconfidence or claim answers are '100% correct' without verifiable proof. Assume subtle errors, edge cases, and arithmetic slips can exist. When reviewing, solving, or verifying work, apply critical self-critique. If an error is detected in your own logic or previous claims, immediately and honestly acknowledge the mistake, explain why it occurred, and provide the exact corrected solution without defending flawed statements."
    )

CONFIG_FILE = CONFIG_DIR / "owner_settings.json"

def sanitize_config(cfg: SystemConfig) -> bool:
    """Auto-detects and normalizes machine-specific or obsolete paths to portable relative paths."""
    modified = False
    
    # 1. Normalize model_path
    mp = cfg.model.model_path
    if mp:
        p = Path(mp)
        if p.is_absolute():
            if not p.exists() or "jinwook" in mp or ("Users" in mp and not p.exists()):
                cfg.model.model_path = f"./models/{p.name}"
                modified = True
            else:
                try:
                    rel = p.relative_to(BASE_DIR)
                    cfg.model.model_path = f"./{rel.as_posix()}"
                    modified = True
                except ValueError:
                    pass

    # 2. Normalize models_dir
    md = cfg.model.models_dir
    if md:
        p_md = Path(md)
        if p_md.is_absolute() or md.endswith(".gguf") or "jinwook" in md or "Users" in md:
            cfg.model.models_dir = "./models"
            modified = True

    # 3. Normalize allowed_workspace
    aw = cfg.tools.allowed_workspace
    if aw:
        p_aw = Path(aw)
        if p_aw.is_absolute() and (not p_aw.exists() or "jinwook" in aw or "Users" in aw):
            cfg.tools.allowed_workspace = "./workspace/sandbox"
            modified = True
        elif p_aw.is_absolute():
            try:
                rel = p_aw.relative_to(BASE_DIR)
                cfg.tools.allowed_workspace = f"./{rel.as_posix()}"
                modified = True
            except ValueError:
                pass

    return modified

def load_config() -> SystemConfig:
    if CONFIG_FILE.exists():
        try:
            config = SystemConfig.model_validate_json(CONFIG_FILE.read_text(encoding="utf-8"))
            if sanitize_config(config):
                save_config(config)
            return config
        except Exception:
            pass
    config = SystemConfig()
    save_config(config)
    return config

def save_config(config: SystemConfig):
    CONFIG_FILE.write_text(config.model_dump_json(indent=2), encoding="utf-8")

system_config = load_config()
