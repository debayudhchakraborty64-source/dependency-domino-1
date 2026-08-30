"""
Dependency Domino - Repository Analyzer
Safely extracts and analyzes repository structure from a ZIP upload or local path.
Security: prevents path traversal, size limits, binary file filtering.
"""
import os
import re
import zipfile
import shutil
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from models import (
    Repository, Component, ComponentMetadata,
    Language, NodeType, AnalysisStatus
)
from config import settings

logger = logging.getLogger(__name__)

# Directories to skip entirely
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "env", "coverage", ".nyc_output", ".next",
    ".nuxt", "out", "target", "vendor", ".cache", "tmp", "temp",
    ".pytest_cache", ".mypy_cache", "eggs", ".eggs", "htmlcov",
    ".tox", "__MACOSX", ".DS_Store", "bin", "obj",
}

# Files to skip
IGNORED_FILES = {
    ".DS_Store", ".gitignore", ".gitattributes", ".env.local",
    "package-lock.json", "yarn.lock", "poetry.lock",
}

# File extensions to include in analysis
ANALYZABLE_EXTENSIONS = {
    # Full dependency-extraction support
    ".js":   Language.JAVASCRIPT,
    ".jsx":  Language.JSX,
    ".ts":   Language.TYPESCRIPT,
    ".tsx":  Language.TSX,
    ".py":   Language.PYTHON,
    # Structural analysis only (no dependency extraction)
    ".css":  Language.CSS,
    ".html": Language.HTML,
    ".json": Language.JSON,
    ".yaml": Language.YAML,
    ".yml":  Language.YAML,
    # Other recognized but no import extraction
    ".java": Language.OTHER,
    ".c":    Language.OTHER,
    ".cpp":  Language.OTHER,
    ".cc":   Language.OTHER,
    ".h":    Language.OTHER,
    ".hpp":  Language.OTHER,
    ".cs":   Language.OTHER,
    ".go":   Language.OTHER,
    ".rb":   Language.OTHER,
    ".rs":   Language.OTHER,
    ".swift":Language.OTHER,
    ".kt":   Language.OTHER,
}

# Languages for which we actually do dependency extraction
DEPENDENCY_LANGS = {
    Language.JAVASCRIPT, Language.JSX, Language.TYPESCRIPT, Language.TSX,
    Language.PYTHON,
}

MAX_FILE_SIZE = 500 * 1024  # 500 KB per file — skip oversized files
MAX_FILES = 2000

# Test file patterns
TEST_PATTERNS = [
    r"\.test\.(js|jsx|ts|tsx|mjs)$",
    r"\.spec\.(js|jsx|ts|tsx|mjs)$",
    r"_test\.py$",
    r"test_.*\.py$",
    r"__tests__/",
    r"/(tests?|spec)/",
    r"/(test|spec)$",        # directory named "test" or "spec"
]


def _is_test_file(path: str) -> bool:
    path_lower = path.replace("\\", "/")
    return any(re.search(p, path_lower) for p in TEST_PATTERNS)


def _is_service_file(path: str) -> bool:
    name = Path(path).stem.lower()
    return any(k in name for k in ("service", "api", "client", "provider", "gateway", "repository", "repo"))


def _is_api_file(path: str) -> bool:
    name = Path(path).stem.lower()
    parts = [p.lower() for p in Path(path).parts]
    return "api" in parts or name.startswith("api") or "route" in name or "endpoint" in name or "controller" in name


def detect_language(path: str) -> Language:
    ext = Path(path).suffix.lower()
    return ANALYZABLE_EXTENSIONS.get(ext, Language.OTHER)


def infer_node_type(path: str, is_test: bool) -> NodeType:
    if is_test:
        return NodeType.TEST
    if _is_service_file(path):
        return NodeType.SERVICE
    if _is_api_file(path):
        return NodeType.API
    return NodeType.FILE


def safe_extract_zip(zip_path: str, extract_to: str, repo_id: str) -> Tuple[str, List[str]]:
    """
    Safely extract a ZIP file.
    - Prevents path traversal
    - Skips directories in IGNORED_DIRS
    - Skips files over MAX_FILE_SIZE
    - Handles nested directory wrappers (e.g., project-main/src/...)
    - Returns (extracted_root, list_of_relative_file_paths)
    """
    dest = os.path.join(extract_to, repo_id)
    os.makedirs(dest, exist_ok=True)
    extracted_files = []
    top_level_dirs = set()

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        for member in members:
            # Path traversal protection
            member_path = os.path.normpath(member.filename)
            if member_path.startswith("..") or os.path.isabs(member_path):
                logger.debug("Skipping path traversal attempt: %s", member.filename)
                continue

            # Use forward-slash version for consistent filtering
            member_fwd = member.filename.replace("\\", "/")

            # Skip hidden system files/dirs (but allow .github etc.)
            parts_fwd = [p for p in member_fwd.split("/") if p]
            if any(p.startswith(".") and p not in {".github", ".gitignore", ".gitattributes"}
                   for p in parts_fwd):
                continue

            # Track top-level directory
            path_parts = Path(member_path).parts
            if path_parts:
                top_level_dirs.add(path_parts[0])

            # Skip ignored directories
            parts_lower = [p.lower() for p in path_parts]
            if any(p in IGNORED_DIRS for p in parts_lower):
                continue
            if any(p.endswith(".egg-info") for p in parts_lower):
                continue

            # Skip directories
            if member.is_dir():
                continue

            # Skip oversized files
            if member.file_size > MAX_FILE_SIZE:
                logger.debug("Skipping oversized file: %s (%d bytes)", member.filename, member.file_size)
                continue

            # Skip ignored filenames
            if Path(member_path).name in IGNORED_FILES:
                continue

            # Only include analyzable files
            ext = Path(member_path).suffix.lower()
            if ext not in ANALYZABLE_EXTENSIONS and ext not in (".md", ".txt", ".cfg", ".toml", ".ini", ".env.example"):
                continue

            # Extract safely
            target = os.path.join(dest, member_path)
            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)

            try:
                with zf.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                # Store with forward-slash paths for consistency
                extracted_files.append(member_path.replace("\\", "/"))
                if len(extracted_files) >= MAX_FILES:
                    logger.info("Hit MAX_FILES limit (%d) during extraction", MAX_FILES)
                    break
            except Exception as e:
                logger.warning("Failed to extract %s: %s", member.filename, e)
                continue

    # Handle single-top-level-directory wrapper (e.g. GitHub-style "project-main/src/...")
    actual_root = dest
    if len(top_level_dirs) == 1 and extracted_files:
        single_dir = list(top_level_dirs)[0]
        single_dir_path = os.path.join(dest, single_dir)
        if os.path.isdir(single_dir_path):
            prefix = single_dir + "/"
            all_under = all(f.startswith(prefix) for f in extracted_files)
            if all_under:
                actual_root = single_dir_path
                extracted_files = [f[len(prefix):] for f in extracted_files]
                logger.info("Detected single-directory wrapper '%s', using as repo root", single_dir)

    logger.info("Extracted %d files from ZIP to %s", len(extracted_files), actual_root)
    return actual_root, extracted_files


def count_lines(file_path: str) -> int:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def extract_js_imports(content: str) -> List[str]:
    """
    Extract import/require statements from JS/TS/JSX/TSX files.

    Handles:
    - import X from './x'
    - import { X } from './x'
    - import * as X from './x'
    - import './x'
    - export { X } from './x'
    - export * from './x'
    - export * as X from './x'
    - require('./x')
    - dynamic import('./x') — captured but treated as possible
    """
    imports = set()

    # ES module static imports (covers all named/default/namespace/side-effect forms)
    # Pattern: import [stuff] from 'path'  OR  import 'path'
    for m in re.finditer(
        r"""^\s*import\s+(?:[^'";\n]+?\s+from\s+)?['"]([^'"]+)['"]""",
        content, re.MULTILINE
    ):
        imports.add(m.group(1))

    # Re-exports: export { X } from './x'  /  export * from './x'  /  export * as X from './x'
    for m in re.finditer(
        r"""^\s*export\s+(?:\*(?:\s+as\s+\w+)?\s+from|{[^}]*}\s+from)\s+['"]([^'"]+)['"]""",
        content, re.MULTILINE
    ):
        imports.add(m.group(1))

    # CommonJS require('...')
    for m in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", content):
        imports.add(m.group(1))

    return list(imports)


def extract_js_exports(content: str) -> List[str]:
    """Extract export names from JS/TS files."""
    exports = []
    for m in re.finditer(
        r"export\s+(?:default\s+)?(?:class|function|const|let|var|async\s+function)\s+(\w+)",
        content
    ):
        exports.append(m.group(1))
    for m in re.finditer(r"module\.exports\s*=\s*\{([^}]+)\}", content):
        for name in re.findall(r"\b(\w+)\b", m.group(1)):
            exports.append(name)
    return list(set(exports))


def extract_js_functions(content: str) -> List[str]:
    """Extract function/class/arrow function names from JS/TS."""
    names = []
    for m in re.finditer(r"(?:function|class)\s+(\w+)", content):
        names.append(m.group(1))
    for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", content):
        names.append(m.group(1))
    return list(set(names))[:30]  # cap at 30


def extract_python_imports(content: str) -> List[str]:
    """
    Extract import statements from Python files.
    Handles:
    - import foo
    - import foo.bar
    - from foo import bar
    - from foo.bar import baz
    - from . import x  (relative, converted to module-relative)
    - from .. import x
    """
    imports = []
    for m in re.finditer(r"^import\s+([\w.]+)", content, re.MULTILINE):
        imports.append(m.group(1))
    for m in re.finditer(r"^from\s+([\w.]+)\s+import", content, re.MULTILINE):
        mod = m.group(1)
        # Skip pure relative imports with only dots (e.g., "from . import x")
        if mod and not mod.replace(".", ""):
            continue
        imports.append(mod)
    return list(set(imports))


def extract_python_functions(content: str) -> List[str]:
    """Extract function/class names from Python files."""
    names = []
    for m in re.finditer(r"^(?:def|class|async def)\s+(\w+)", content, re.MULTILINE):
        names.append(m.group(1))
    return list(set(names))[:30]


def analyze_file(repo_id: str, abs_path: str, rel_path: str) -> Optional[Component]:
    """
    Parse a single file and return a Component.

    rel_path must use forward slashes and be relative to the repository root.
    Component ID is deterministic: uuid5(NAMESPACE_DNS, "repo_id:rel_path")
    so the same file always produces the same ID within a repo session.
    """
    lang = detect_language(rel_path)
    if lang == Language.OTHER:
        # Still include as a structural node, but no imports
        pass

    is_test = _is_test_file(rel_path)
    node_type = infer_node_type(rel_path, is_test)

    try:
        content = open(abs_path, "r", encoding="utf-8", errors="ignore").read()
    except Exception as e:
        logger.debug("Failed to read %s: %s", abs_path, e)
        return None

    lines = content.count("\n") + 1

    imports: List[str] = []
    exports: List[str] = []
    functions: List[str] = []

    if lang in (Language.JAVASCRIPT, Language.JSX, Language.TYPESCRIPT, Language.TSX):
        imports = extract_js_imports(content)
        exports = extract_js_exports(content)
        functions = extract_js_functions(content)
    elif lang == Language.PYTHON:
        imports = extract_python_imports(content)
        exports = []
        functions = extract_python_functions(content)
    # For OTHER / CSS / HTML / JSON / YAML: no import extraction

    meta = ComponentMetadata(
        lines=lines,
        functions=functions,
        imports=imports,
        exports=exports,
        is_test=is_test,
    )

    # Deterministic ID within a single analysis session:
    # Using uuid5 keyed on (repo_id, rel_path) ensures that the same file
    # always gets the same component ID during one session.
    import uuid as _uuid
    comp_id = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"{repo_id}:{rel_path}"))

    return Component(
        id=comp_id,
        repository_id=repo_id,
        name=Path(rel_path).name,
        path=rel_path,
        type=node_type,
        language=lang,
        metadata=meta,
    )


def walk_repository(root: str, repo_id: str) -> List[Component]:
    """
    Walk all files in a repository root and return analyzed components.
    Preserves the full relative path from the root.
    """
    components = []
    root_path = Path(root)
    seen_paths = set()

    for abs_path in sorted(root_path.rglob("*")):  # sorted for determinism
        if not abs_path.is_file():
            continue

        # Compute repo-relative path with forward slashes
        try:
            rel = abs_path.relative_to(root_path)
        except ValueError:
            continue

        rel_str = str(rel).replace("\\", "/")

        # Check for ignored directories in path parts (excluding filename)
        parts = rel.parts
        if any(p.lower() in IGNORED_DIRS for p in parts[:-1]):
            continue

        # Skip non-analyzable extensions
        ext = Path(rel_str).suffix.lower()
        if ext not in ANALYZABLE_EXTENSIONS:
            continue

        # Skip ignored filenames
        if Path(rel_str).name in IGNORED_FILES:
            continue

        if rel_str in seen_paths:
            continue
        seen_paths.add(rel_str)

        comp = analyze_file(repo_id, str(abs_path), rel_str)
        if comp:
            components.append(comp)
            logger.debug("Analyzed: %s (lang=%s, imports=%d)",
                         rel_str, comp.language.value, len(comp.metadata.imports))

        if len(components) >= MAX_FILES:
            logger.info("Hit MAX_FILES limit (%d) during walk", MAX_FILES)
            break

    logger.info("Discovered %d components in repository root %s", len(components), root)
    return components


def compute_language_stats(components: List[Component]) -> List[Dict]:
    counts: Dict[str, int] = {}
    for c in components:
        lang = c.language.value
        counts[lang] = counts.get(lang, 0) + 1
    total = max(len(components), 1)
    return [
        {"language": lang, "count": count, "percentage": round(count / total * 100, 1)}
        for lang, count in sorted(counts.items(), key=lambda x: -x[1])
    ]


def count_directories(components: List[Component]) -> int:
    dirs = set()
    for c in components:
        p = Path(c.path).parent
        while str(p) not in (".", ""):
            dirs.add(str(p))
            p = p.parent
    return len(dirs)
