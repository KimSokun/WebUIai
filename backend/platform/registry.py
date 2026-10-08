from typing import Dict, List, Optional, Set, Any
from backend.platform.manifest import PlatformTool, ToolCategory, RiskLevel, BaseTool

class ToolPlatformRegistry:
    """
    Scalable Tool Platform Registry indexing hundreds of tools across categories.
    Supports dynamic discovery, tag indexing, and selective LLM function exports.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_meta: Dict[str, Dict[str, Any]] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}

    def _ensure_loaded(self):
        if not self._tools:
            try:
                import backend.tools  # noqa: F401
            except Exception:
                pass

    def register(self, tool: BaseTool, category: str = "utility", tags: Optional[List[str]] = None, risk: str = "READ"):
        tool_id = tool.name
        self._tools[tool_id] = tool

        # Index by category
        cat_key = category.lower()
        if cat_key not in self._by_category:
            self._by_category[cat_key] = []
        if tool_id not in self._by_category[cat_key]:
            self._by_category[cat_key].append(tool_id)

        # Index by tags
        tag_list = list(tags) if tags else []
        tag_list.extend([tool_id, cat_key])
        for t in tag_list:
            t_clean = t.lower().strip()
            if t_clean not in self._by_tag:
                self._by_tag[t_clean] = set()
            self._by_tag[t_clean].add(tool_id)

        self._tool_meta[tool_id] = {
            "category": cat_key,
            "tags": tag_list,
            "risk": risk
        }

    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        self._ensure_loaded()
        if tool_id in self._tools:
            return self._tools[tool_id]
        alt = tool_id.replace(".", "_") if "." in tool_id else tool_id.replace("_", ".")
        return self._tools.get(alt)

    def list_all_tools(self) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        results = []
        for t in self._tools.values():
            meta = self._tool_meta.get(t.name, {})
            cat = meta.get("category")
            if not cat:
                manifest = getattr(t, "manifest", None)
                cat = manifest.category.value if manifest else "utility"
            tags = meta.get("tags") or (getattr(t, "manifest", None).tags if getattr(t, "manifest", None) else [])
            results.append({
                "id": t.name,
                "name": t.name.replace("_", " ").title(),
                "category": cat,
                "description": t.description,
                "risk_level": t.risk_level,
                "tags": tags,
                "schema": t.get_input_schema()
            })
        return results

    def list_categories(self) -> Dict[str, int]:
        self._ensure_loaded()
        return {cat: len(tools) for cat, tools in sorted(self._by_category.items())}

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        self._ensure_loaded()
        ids = self._by_category.get(category.lower(), [])
        return [self._tools[i] for i in ids if i in self._tools]

    def get_tools_definitions(self, tool_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        Returns JSON schema function definitions for only the selected tool IDs.
        Guarantees zero prompt context bloat.
        """
        defs = []
        for name, tool in self._tools.items():
            if tool_ids is not None and name not in tool_ids:
                continue
            defs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_input_schema()
                }
            })
        return defs

tool_platform = ToolPlatformRegistry()
