import re
from typing import List, Set, Dict, Any, Optional
from backend.platform.registry import tool_platform
from backend.platform.manifest import BaseTool

class ToolDiscoveryEngine:
    """
    Intelligent Capability Discovery Engine:
    Dynamically discovers and selects the 3 to 8 most relevant tools
    for any task without overloading the model prompt.
    """
    # Intent category keyword associations
    CATEGORY_SIGNALS = {
        "web_research": ["search", "google", "web", "internet", "news", "look up", "ស្វែងរក"],
        "documentation": ["documentation", "docs", "doc", "api reference", "rfc", "changelog", "release notes", "migration guide", "ឯកសារ"],
        "github": ["github", "repository", "commit", "issue", "pull request", "pr", "clone", "git repo"],
        "programming": ["code", "function", "class", "def ", "script", "syntax", "compile", "run", "program", "trace", "print", "loop", "output", "trace the output", "what will be printed", "evaluate", "variable", "កូដ", "ដំណើរការកូដ", "តេស្តកូដ"],
        "code_intelligence": ["callers", "references", "definition", "imports", "unused code", "dead code", "security issue", "find class", "where is"],
        "filesystem": ["file", "directory", "folder", "read file", "list files", "search files", "hash", "path", "ឯកសារ"],
        "terminal": ["terminal", "command", "shell", "bash", "powershell", "env", "process"],
        "git": ["git status", "git diff", "git log", "git branch", "git blame", "git commit", "git"],
        "package": ["pypi", "npm", "crates", "cargo", "package", "dependency", "version", "pip", "library"],
        "models": ["huggingface", "model card", "model search", "hf model", "download model"],
        "gguf": ["gguf", "quantization", "q4_k_m", "llama-server", "tensor", "metadata"],
        "hardware": ["cpu", "ram", "memory", "hardware", "disk", "specs", "gpu", "vram"],
        "benchmark": ["benchmark", "speed", "latency", "tokens per second", "tps", "throughput"],
        "debugging": ["traceback", "error", "exception", "bug", "crash", "stack trace", "log", "កំហុស"],
        "database": ["database", "sql", "sqlite", "postgres", "query", "table", "schema"],
        "media": ["ffmpeg", "ffprobe", "video", "audio", "codec", "media", "mp4", "mp3"],
        "khmer": ["khmer", "ខ្មែរ", "ភាសាខ្មែរ", "បកប្រែ", "ពាក្យបច្ចេកទេស", "terminology", "លេខខ្មែរ", "khmer number", "khmer numeral", "glossary"],
        "utility": ["calculate", "math", "calc", "គណនា", "discount", "percentage", "off", "area", "rectangle", "triangle", "circle", "radius", "length", "width", "equation", "solve", "បញ្ចុះតម្លៃ", "ផ្ទៃក្រឡា", "បណ្តោយ", "ទទឹង", "សមីការ", "ផលបូក", "ផលដក", "ផលគុណ", "ផលចែក", "fast calc", "unit", "convert", "celsius", "fahrenheit", "bytes", "mb", "gb", "compact", "regex", "extract"],
        "memory": ["memory", "remember", "store", "cache", "save fact", "note", "recall", "get key", "set key", "fast memory", "ចងចាំ", "កត់ត្រា"],
        "scaffold": ["scaffold", "boilerplate", "template", "starter", "new project", "generate project", "create app", "web app", "fastapi app", "react app"],
        "preview": ["preview", "live app", "open app", "browser preview", "view html", "view app", "run app", "មើលគេហទំព័រ", "បើកកម្មវិធី"],
        "rag": ["rag", "document", "knowledge base", "search doc", "search pdf", "book", "passages", "index docs", "ឯកសារ", "ស្រាវជ្រាវឯកសារ"]
    }

    def discover_tools(self, task_description: str, max_tools: int = 6) -> List[BaseTool]:
        """
        Analyzes user task description and returns Top-K matching tools.
        """
        clean_text = task_description.lower().strip()
        matching_scores: Dict[str, float] = {}

        # 1. Match categories
        active_categories: Set[str] = set()
        for cat, signals in self.CATEGORY_SIGNALS.items():
            for sig in signals:
                if sig in clean_text:
                    active_categories.add(cat)
                    break

        # 2. Score tools by category and tags
        for tool_meta in tool_platform.list_all_tools():
            tool_id = tool_meta["id"]
            score = 0.0
            tool_cat = tool_meta["category"]

            # Boost if category matched
            if tool_cat in active_categories:
                score += 3.0

            # Boost if tool id or space-separated name appears in prompt
            if tool_id in clean_text or tool_id.replace("_", " ") in clean_text or tool_id.replace(".", " ") in clean_text:
                score += 5.0

            for part in tool_id.replace(".", "_").split("_"):
                if len(part) >= 4 and part in clean_text:
                    score += 2.0
            
            for tag in tool_meta.get("tags", []):
                if tag in clean_text or tag.replace("_", " ") in clean_text:
                    score += 2.0

            if score > 0:
                matching_scores[tool_id] = score

        # 3. Sort by score descending
        sorted_ids = sorted(matching_scores.keys(), key=lambda x: matching_scores[x], reverse=True)

        selected_tools = []
        for tid in sorted_ids[:max_tools]:
            t = tool_platform.get_tool(tid)
            if t:
                selected_tools.append(t)

        # Fallback to general utilities if no match
        if not selected_tools:
            for fallback_id in ["calculator", "web_search", "codebase_search"]:
                t = tool_platform.get_tool(fallback_id)
                if t:
                    selected_tools.append(t)

        return selected_tools

tool_discovery = ToolDiscoveryEngine()
