from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class LanguageProfile:
    name: str
    category: str  # compiled, interpreted, scripting, query, markup, shading
    extensions: List[str]
    package_manager: Optional[str] = None
    package_registry: Optional[str] = None
    official_docs_url: Optional[str] = None
    compiler_or_runner: Optional[str] = None
    test_framework: Optional[str] = None
    standard_paradigm: str = "multi-paradigm"

class LanguageProfileRegistry:
    """
    Architectural registry supporting 38+ programming, markup, and query languages.
    """
    def __init__(self):
        self._profiles: Dict[str, LanguageProfile] = {}
        self._ext_map: Dict[str, str] = {}
        self._register_all()

    def _register(self, profile: LanguageProfile):
        key = profile.name.lower()
        self._profiles[key] = profile
        for ext in profile.extensions:
            self._ext_map[ext.lower()] = key

    def get_profile(self, name_or_ext: str) -> Optional[LanguageProfile]:
        lookup = name_or_ext.lower().strip().lstrip(".")
        if lookup in self._profiles:
            return self._profiles[lookup]
        if f".{lookup}" in self._ext_map:
            return self._profiles[self._ext_map[f".{lookup}"]]
        return None

    def list_languages(self) -> List[str]:
        return sorted([p.name for p in self._profiles.values()])

    def _register_all(self):
        # 1-10
        self._register(LanguageProfile("Python", "interpreted", [".py", ".pyw", ".pyi"], "pip", "PyPI", "https://docs.python.org/3/", "python", "pytest", "object-oriented, functional"))
        self._register(LanguageProfile("C", "compiled", [".c", ".h"], "vcpkg / conan", None, "https://en.cppreference.com/w/c", "gcc/clang/msvc", "Unity/cmocka", "procedural, imperative"))
        self._register(LanguageProfile("C++", "compiled", [".cpp", ".hpp", ".cc", ".cxx"], "conan / vcpkg / cmake", None, "https://en.cppreference.com/w/cpp", "g++/clang++/msvc", "GoogleTest/Catch2", "multi-paradigm"))
        self._register(LanguageProfile("C#", "compiled", [".cs"], "dotnet / nuget", "NuGet", "https://learn.microsoft.com/dotnet/csharp/", "dotnet", "xUnit/NUnit", "object-oriented"))
        self._register(LanguageProfile("Java", "compiled", [".java"], "maven / gradle", "Maven Central", "https://docs.oracle.com/en/java/", "javac / java", "JUnit 5", "object-oriented"))
        self._register(LanguageProfile("JavaScript", "interpreted", [".js", ".mjs", ".cjs"], "npm / pnpm / yarn", "npm", "https://developer.mozilla.org/docs/Web/JavaScript", "node", "Jest / Vitest", "prototype-based, event-driven"))
        self._register(LanguageProfile("TypeScript", "compiled", [".ts", ".tsx"], "npm / pnpm / yarn", "npm", "https://www.typescriptlang.org/docs/", "tsc / bun / deno", "Vitest / Jest", "typed superset of JavaScript"))
        self._register(LanguageProfile("Go", "compiled", [".go"], "go modules", "pkg.go.dev", "https://go.dev/doc/", "go", "testing", "concurrent, imperative"))
        self._register(LanguageProfile("Rust", "compiled", [".rs"], "cargo", "crates.io", "https://doc.rust-lang.org/", "rustc / cargo", "cargo test", "memory-safe, systems"))
        self._register(LanguageProfile("Kotlin", "compiled", [".kt", ".kts"], "gradle / maven", "Maven Central", "https://kotlinlang.org/docs/", "kotlinc", "JUnit / Kotest", "object-oriented, functional"))

        # 11-20
        self._register(LanguageProfile("Swift", "compiled", [".swift"], "swift package manager", "Swift Package Index", "https://www.swift.org/documentation/", "swift", "XCTest / Swift Testing", "protocol-oriented"))
        self._register(LanguageProfile("Dart", "compiled", [".dart"], "pub", "pub.dev", "https://dart.dev/guides", "dart", "test", "object-oriented"))
        self._register(LanguageProfile("PHP", "interpreted", [".php"], "composer", "Packagist", "https://www.php.net/docs.php", "php", "PHPUnit", "imperative, object-oriented"))
        self._register(LanguageProfile("Ruby", "interpreted", [".rb"], "gem / bundler", "RubyGems", "https://www.ruby-lang.org/en/documentation/", "ruby", "RSpec", "pure object-oriented"))
        self._register(LanguageProfile("Lua", "interpreted", [".lua"], "luarocks", "LuaRocks", "https://www.lua.org/docs.html", "lua", "Busted", "scripting, multi-paradigm"))
        self._register(LanguageProfile("R", "interpreted", [".r", ".R"], "install.packages", "CRAN", "https://cran.r-project.org/manuals.html", "Rscript", "testthat", "statistical computing"))
        self._register(LanguageProfile("MATLAB", "interpreted", [".m"], "MATLAB Add-Ons", "MATLAB File Exchange", "https://www.mathworks.com/help/matlab/", "matlab", "matlab.unittest", "numerical computing"))
        self._register(LanguageProfile("Scala", "compiled", [".scala"], "sbt / mill", "Maven Central", "https://docs.scala-lang.org/", "scala / sbt", "ScalaTest", "functional, object-oriented"))
        self._register(LanguageProfile("Perl", "interpreted", [".pl", ".pm"], "cpan", "CPAN", "https://perldoc.perl.org/", "perl", "Test::More", "scripting, text processing"))
        self._register(LanguageProfile("Bash", "scripting", [".sh", ".bash"], "system package manager", None, "https://www.gnu.org/software/bash/manual/", "bash", "bats-core", "command scripting"))

        # 21-30
        self._register(LanguageProfile("PowerShell", "scripting", [".ps1", ".psm1", ".psd1"], "PowerShellGallery", "PSGallery", "https://learn.microsoft.com/powershell/", "powershell / pwsh", "Pester", "task automation, object-pipeline"))
        self._register(LanguageProfile("SQL", "query", [".sql"], None, None, "https://www.iso.org/standard/63555.html", "sqlite3 / psql", "pgTAP", "relational declarative query"))
        self._register(LanguageProfile("HTML", "markup", [".html", ".htm"], None, None, "https://developer.mozilla.org/docs/Web/HTML", "browser", "W3C validator", "hypertext markup"))
        self._register(LanguageProfile("CSS", "markup", [".css"], None, None, "https://developer.mozilla.org/docs/Web/CSS", "browser", "stylelint", "style sheets"))
        self._register(LanguageProfile("SCSS", "markup", [".scss", ".sass"], "npm", "npm", "https://sass-lang.com/documentation/", "sass", "stylelint", "CSS preprocessor"))
        self._register(LanguageProfile("XML", "markup", [".xml", ".xsl", ".xsd"], None, None, "https://www.w3.org/XML/", "xmlstarlet", "xmllint", "extensible markup"))
        self._register(LanguageProfile("JSON", "data", [".json"], None, None, "https://www.json.org/", "jq", "json-schema", "data interchange"))
        self._register(LanguageProfile("YAML", "data", [".yaml", ".yml"], None, None, "https://yaml.org/spec/", "yamllint", "yamllint", "human-friendly data serialization"))
        self._register(LanguageProfile("TOML", "data", [".toml"], None, None, "https://toml.io/", None, "taplo", "configuration format"))
        self._register(LanguageProfile("Markdown", "markup", [".md", ".markdown"], None, None, "https://commonmark.org/", "glow / cmark", "markdownlint", "lightweight markup"))

        # 31-38
        self._register(LanguageProfile("GraphQL", "query", [".graphql", ".gql"], "npm", "npm", "https://graphql.org/learn/", "graphql-js", "jest", "API query language"))
        self._register(LanguageProfile("Assembly", "compiled", [".asm", ".s"], None, None, "https://www.felixcloutier.com/x86/", "nasm / as", None, "low-level hardware architecture"))
        self._register(LanguageProfile("CUDA", "compiled", [".cu", ".cuh"], "cuda-toolkit", None, "https://docs.nvidia.com/cuda/", "nvcc", "GoogleTest", "parallel computing GPU"))
        self._register(LanguageProfile("HLSL", "shading", [".hlsl"], "DirectX SDK", None, "https://learn.microsoft.com/windows/win32/direct3dhlsl/", "dxc / fxc", None, "high-level shader language"))
        self._register(LanguageProfile("GLSL", "shading", [".glsl", ".vert", ".frag", ".geom"], None, None, "https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language", "glslangValidator", None, "OpenGL shading language"))
        self._register(LanguageProfile("QML", "declarative", [".qml"], "Qt", None, "https://doc.qt.io/qt-6/qmlfirststeps.html", "qmlscene / qmllint", "Qt Quick Test", "user interface declarative"))

language_profiles = LanguageProfileRegistry()
