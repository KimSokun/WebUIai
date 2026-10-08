from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class BaseTool(ABC):
    def __init__(self, name: str, description: str, risk_level: str = "LOW", requires_confirmation: bool = False):
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.requires_confirmation = requires_confirmation

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Returns JSON schema for the tool input arguments."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executes the tool logic under sandbox policy."""
        pass

    def audit(self, user: str, args: Dict[str, Any], result: ToolResult) -> Dict[str, Any]:
        return {
            "tool": self.name,
            "user": user,
            "args": args,
            "success": result.success,
            "risk_level": self.risk_level,
            "error": result.error,
        }

class RiskLevel(str, Enum):
    READ = "READ"
    RESEARCH = "RESEARCH"
    ANALYZE = "ANALYZE"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    DESTRUCTIVE = "DESTRUCTIVE"
    OWNER_ONLY = "OWNER_ONLY"

class ToolCategory(str, Enum):
    WEB_RESEARCH = "web_research"
    DOCUMENTATION = "documentation"
    GITHUB = "github"
    PROGRAMMING = "programming"
    CODE_INTELLIGENCE = "code_intelligence"
    FILESYSTEM = "filesystem"
    TERMINAL = "terminal"
    GIT = "git"
    PACKAGE = "package"
    MODELS = "models"
    GGUF = "gguf"
    HARDWARE = "hardware"
    BENCHMARK = "benchmark"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DATABASE = "database"
    DATA = "data"
    MEDIA = "media"
    NETWORK = "network"
    SECURITY = "security"
    DOCUMENT = "document"
    KHMER = "khmer"
    KNOWLEDGE = "knowledge"
    UTILITY = "utility"

class ToolManifest(BaseModel):
    id: str
    name: str
    category: ToolCategory
    description: str
    tags: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.READ
    requires_confirmation: bool = False
    requires_owner_auth: bool = False
    timeout_seconds: float = 15.0
    max_output_chars: int = 4000

class PlatformTool(BaseTool):
    def __init__(self, manifest: ToolManifest):
        super().__init__(
            name=manifest.id,
            description=manifest.description,
            risk_level=manifest.risk_level.value,
            requires_confirmation=manifest.requires_confirmation
        )
        self.manifest = manifest

    def truncate_output(self, data: Any) -> Any:
        if isinstance(data, str) and len(data) > self.manifest.max_output_chars:
            return data[:self.manifest.max_output_chars] + f"\n\n[Output truncated: {len(data) - self.manifest.max_output_chars} characters omitted]"
        return data
