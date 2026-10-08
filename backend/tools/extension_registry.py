# Universal File Extension Registry & Intelligence Engine for K-Jocker
# Provides comprehensive support for 100+ programming languages, configs, and asset formats.

from typing import Dict, Any, Optional, Set, List
from pathlib import Path

EXTENSION_METADATA: Dict[str, Dict[str, Any]] = {
    # Web & Modern Frontend
    '.html': {'category': 'web', 'language': 'HTML', 'mime': 'text/html', 'is_binary': False},
    '.htm': {'category': 'web', 'language': 'HTML', 'mime': 'text/html', 'is_binary': False},
    '.css': {'category': 'web', 'language': 'CSS', 'mime': 'text/css', 'is_binary': False},
    '.scss': {'category': 'web', 'language': 'SCSS', 'mime': 'text/x-scss', 'is_binary': False},
    '.sass': {'category': 'web', 'language': 'Sass', 'mime': 'text/x-sass', 'is_binary': False},
    '.less': {'category': 'web', 'language': 'Less', 'mime': 'text/x-less', 'is_binary': False},
    '.js': {'category': 'web', 'language': 'JavaScript', 'mime': 'application/javascript', 'is_binary': False},
    '.jsx': {'category': 'web', 'language': 'JavaScript (React)', 'mime': 'text/jsx', 'is_binary': False},
    '.mjs': {'category': 'web', 'language': 'JavaScript (ESM)', 'mime': 'application/javascript', 'is_binary': False},
    '.cjs': {'category': 'web', 'language': 'JavaScript (CommonJS)', 'mime': 'application/javascript', 'is_binary': False},
    '.ts': {'category': 'web', 'language': 'TypeScript', 'mime': 'application/typescript', 'is_binary': False},
    '.tsx': {'category': 'web', 'language': 'TypeScript (React)', 'mime': 'text/tsx', 'is_binary': False},
    '.vue': {'category': 'web', 'language': 'Vue', 'mime': 'text/x-vue', 'is_binary': False},
    '.svelte': {'category': 'web', 'language': 'Svelte', 'mime': 'text/x-svelte', 'is_binary': False},
    '.astro': {'category': 'web', 'language': 'Astro', 'mime': 'text/x-astro', 'is_binary': False},
    '.svg': {'category': 'web', 'language': 'SVG', 'mime': 'image/svg+xml', 'is_binary': False},

    # Systems & Backend
    '.py': {'category': 'code', 'language': 'Python', 'mime': 'text/x-python', 'is_binary': False},
    '.pyw': {'category': 'code', 'language': 'Python GUI', 'mime': 'text/x-python', 'is_binary': False},
    '.c': {'category': 'code', 'language': 'C', 'mime': 'text/x-c', 'is_binary': False},
    '.h': {'category': 'code', 'language': 'C Header', 'mime': 'text/x-c', 'is_binary': False},
    '.cpp': {'category': 'code', 'language': 'C++', 'mime': 'text/x-c++', 'is_binary': False},
    '.cc': {'category': 'code', 'language': 'C++', 'mime': 'text/x-c++', 'is_binary': False},
    '.cxx': {'category': 'code', 'language': 'C++', 'mime': 'text/x-c++', 'is_binary': False},
    '.hpp': {'category': 'code', 'language': 'C++ Header', 'mime': 'text/x-c++', 'is_binary': False},
    '.rs': {'category': 'code', 'language': 'Rust', 'mime': 'text/x-rust', 'is_binary': False},
    '.go': {'category': 'code', 'language': 'Go', 'mime': 'text/x-go', 'is_binary': False},
    '.java': {'category': 'code', 'language': 'Java', 'mime': 'text/x-java', 'is_binary': False},
    '.kt': {'category': 'code', 'language': 'Kotlin', 'mime': 'text/x-kotlin', 'is_binary': False},
    '.kts': {'category': 'code', 'language': 'Kotlin Script', 'mime': 'text/x-kotlin', 'is_binary': False},
    '.cs': {'category': 'code', 'language': 'C#', 'mime': 'text/x-csharp', 'is_binary': False},
    '.php': {'category': 'code', 'language': 'PHP', 'mime': 'text/x-php', 'is_binary': False},
    '.rb': {'category': 'code', 'language': 'Ruby', 'mime': 'text/x-ruby', 'is_binary': False},
    '.lua': {'category': 'code', 'language': 'Lua', 'mime': 'text/x-lua', 'is_binary': False},
    '.swift': {'category': 'code', 'language': 'Swift', 'mime': 'text/x-swift', 'is_binary': False},
    '.dart': {'category': 'code', 'language': 'Dart', 'mime': 'text/x-dart', 'is_binary': False},
    '.zig': {'category': 'code', 'language': 'Zig', 'mime': 'text/x-zig', 'is_binary': False},
    '.nim': {'category': 'code', 'language': 'Nim', 'mime': 'text/x-nim', 'is_binary': False},
    '.scala': {'category': 'code', 'language': 'Scala', 'mime': 'text/x-scala', 'is_binary': False},
    '.pl': {'category': 'code', 'language': 'Perl', 'mime': 'text/x-perl', 'is_binary': False},
    '.r': {'category': 'code', 'language': 'R', 'mime': 'text/x-r', 'is_binary': False},

    # Config & Data
    '.json': {'category': 'data', 'language': 'JSON', 'mime': 'application/json', 'is_binary': False},
    '.json5': {'category': 'data', 'language': 'JSON5', 'mime': 'application/json5', 'is_binary': False},
    '.yaml': {'category': 'config', 'language': 'YAML', 'mime': 'text/yaml', 'is_binary': False},
    '.yml': {'category': 'config', 'language': 'YAML', 'mime': 'text/yaml', 'is_binary': False},
    '.toml': {'category': 'config', 'language': 'TOML', 'mime': 'text/toml', 'is_binary': False},
    '.ini': {'category': 'config', 'language': 'INI', 'mime': 'text/plain', 'is_binary': False},
    '.cfg': {'category': 'config', 'language': 'Config', 'mime': 'text/plain', 'is_binary': False},
    '.conf': {'category': 'config', 'language': 'Config', 'mime': 'text/plain', 'is_binary': False},
    '.env': {'category': 'config', 'language': 'Environment', 'mime': 'text/plain', 'is_binary': False},
    '.xml': {'category': 'data', 'language': 'XML', 'mime': 'application/xml', 'is_binary': False},
    '.csv': {'category': 'data', 'language': 'CSV', 'mime': 'text/csv', 'is_binary': False},
    '.tsv': {'category': 'data', 'language': 'TSV', 'mime': 'text/tab-separated-values', 'is_binary': False},
    '.sql': {'category': 'data', 'language': 'SQL', 'mime': 'text/x-sql', 'is_binary': False},
    '.prisma': {'category': 'data', 'language': 'Prisma', 'mime': 'text/plain', 'is_binary': False},
    '.graphql': {'category': 'data', 'language': 'GraphQL', 'mime': 'application/graphql', 'is_binary': False},
    '.gql': {'category': 'data', 'language': 'GraphQL', 'mime': 'application/graphql', 'is_binary': False},
    '.proto': {'category': 'data', 'language': 'Protobuf', 'mime': 'text/x-protobuf', 'is_binary': False},

    # Shell & DevOps Scripts
    '.bat': {'category': 'script', 'language': 'Batch', 'mime': 'application/x-bat', 'is_binary': False},
    '.cmd': {'category': 'script', 'language': 'Batch', 'mime': 'application/x-bat', 'is_binary': False},
    '.ps1': {'category': 'script', 'language': 'PowerShell', 'mime': 'text/x-powershell', 'is_binary': False},
    '.psm1': {'category': 'script', 'language': 'PowerShell Module', 'mime': 'text/x-powershell', 'is_binary': False},
    '.sh': {'category': 'script', 'language': 'Shell', 'mime': 'application/x-sh', 'is_binary': False},
    '.bash': {'category': 'script', 'language': 'Bash', 'mime': 'application/x-sh', 'is_binary': False},
    '.zsh': {'category': 'script', 'language': 'Zsh', 'mime': 'application/x-sh', 'is_binary': False},
    '.dockerfile': {'category': 'devops', 'language': 'Dockerfile', 'mime': 'text/plain', 'is_binary': False},

    # Documentation & Plain Text
    '.md': {'category': 'doc', 'language': 'Markdown', 'mime': 'text/markdown', 'is_binary': False},
    '.mdx': {'category': 'doc', 'language': 'MDX', 'mime': 'text/mdx', 'is_binary': False},
    '.txt': {'category': 'doc', 'language': 'Plain Text', 'mime': 'text/plain', 'is_binary': False},
    '.rst': {'category': 'doc', 'language': 'reStructuredText', 'mime': 'text/x-rst', 'is_binary': False},
    '.log': {'category': 'doc', 'language': 'Log File', 'mime': 'text/plain', 'is_binary': False},

    # Binary & Media Assets
    '.png': {'category': 'image', 'language': 'PNG Image', 'mime': 'image/png', 'is_binary': True},
    '.jpg': {'category': 'image', 'language': 'JPEG Image', 'mime': 'image/jpeg', 'is_binary': True},
    '.jpeg': {'category': 'image', 'language': 'JPEG Image', 'mime': 'image/jpeg', 'is_binary': True},
    '.gif': {'category': 'image', 'language': 'GIF Image', 'mime': 'image/gif', 'is_binary': True},
    '.webp': {'category': 'image', 'language': 'WebP Image', 'mime': 'image/webp', 'is_binary': True},
    '.ico': {'category': 'image', 'language': 'Icon', 'mime': 'image/x-icon', 'is_binary': True},
    '.pdf': {'category': 'doc', 'language': 'PDF Document', 'mime': 'application/pdf', 'is_binary': True},
    '.bin': {'category': 'binary', 'language': 'Binary Data', 'mime': 'application/octet-stream', 'is_binary': True},
    '.wasm': {'category': 'binary', 'language': 'WebAssembly', 'mime': 'application/wasm', 'is_binary': True}
}

class ExtensionRegistry:
    @staticmethod
    def get_info(path_or_ext: str) -> Dict[str, Any]:
        ext = Path(path_or_ext).suffix.lower()
        if not ext and path_or_ext.startswith('.'):
            ext = path_or_ext.lower()
        
        # Exact match
        if ext in EXTENSION_METADATA:
            info = EXTENSION_METADATA[ext].copy()
            info['extension'] = ext
            return info

        # Default fallback for unknown extensions (open & permissive)
        return {
            'extension': ext or '.txt',
            'category': 'custom',
            'language': ext.lstrip('.').upper() if ext else 'Text',
            'mime': 'text/plain',
            'is_binary': False
        }

    @staticmethod
    def is_text_file(path_or_ext: str) -> bool:
        return not ExtensionRegistry.get_info(path_or_ext).get('is_binary', False)

    @staticmethod
    def is_binary_file(path_or_ext: str) -> bool:
        return ExtensionRegistry.get_info(path_or_ext).get('is_binary', False)

    @staticmethod
    def get_all_supported_extensions() -> List[str]:
        return sorted(list(EXTENSION_METADATA.keys()))

    @staticmethod
    def summarize_directory(dir_path: Path) -> Dict[str, Any]:
        ext_counts = {}
        total_files = 0
        total_bytes = 0
        for p in dir_path.rglob('*'):
            if p.is_file():
                total_files += 1
                total_bytes += p.stat().st_size
                ext = p.suffix.lower() or '(no ext)'
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
        return {
            'total_files': total_files,
            'total_bytes': total_bytes,
            'extension_breakdown': ext_counts
        }

extension_registry = ExtensionRegistry()
