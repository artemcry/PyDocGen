#!/usr/bin/env python3
"""
Generates PROJECT_MAP.md from Python source files.

Parses tagged comments:
    At the top of a file (single or multi-line):
        # <FILEDESCRIPTION>: short one-liner
        — or —
        # <FILEDESCRIPTION>
        # Longer description
        # spanning multiple lines

    Above functions/classes:
        # <Description>: JWT lifecycle: issue, refresh, revoke
        # <TODO>: add rate limiting
        # <WARNING>: no input sanitization
        # <DEPRECATED>: use new_func instead
        # <PERF>: O(n²) — consider caching
        # <HACK>: workaround for upstream bug #123
        # <DEPENDS>: stripe==7.x, STRIPE_SECRET_KEY env var

Usage:
    python scripts/gen_map.py                    # scans src/ and tests/
    python scripts/gen_map.py --root ./myapp     # custom root
    python scripts/gen_map.py --watch            # regenerate on file changes
"""

import ast
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Tag parsing ─────────────────────────────────────────────

TAG_PATTERN = re.compile(
    r"^#\s*<(Description|TODO|WARNING|DEPRECATED|PERF|HACK|DEPENDS)>\s*:\s*(.+)$",
    re.IGNORECASE,
)

KNOWN_TAGS = {"description", "todo", "warning", "deprecated", "perf", "hack", "depends"}

FILE_DESC_START = re.compile(r"^#\s*<FILEDESCRIPTION>\s*(?::\s*(.+))?$", re.IGNORECASE)


def extract_file_description(lines: list[str]) -> str:
    """
    Look for a <FILEDESCRIPTION> block near the top of the file.
    Supports single-line:  # <FILEDESCRIPTION>: text
    And multi-line block:  # <FILEDESCRIPTION>
                           # text line 1
                           # text line 2
    Stops collecting on first non-comment, non-blank line after the tag.
    """
    desc_lines: list[str] = []
    in_block = False

    for line in lines:
        stripped = line.strip()

        if not in_block:
            # Allow shebang / encoding / blank lines before the tag
            if not stripped or stripped.startswith("#!") or re.match(r"^#\s*-\*-", stripped):
                continue
            m = FILE_DESC_START.match(stripped)
            if m:
                inline = m.group(1)
                if inline:
                    return inline.strip()
                in_block = True
                continue
            # Any other non-blank line before the tag — give up
            if stripped:
                break
        else:
            if stripped.startswith("#"):
                desc_lines.append(re.sub(r"^#\s?", "", stripped))
            elif not stripped:
                desc_lines.append("")
            else:
                break

    # Strip trailing blank lines
    while desc_lines and not desc_lines[-1]:
        desc_lines.pop()

    return "\n".join(desc_lines)


def parse_tags_from_lines(lines: list[str], end_lineno: int) -> dict[str, list[str]]:
    """
    Scan upward from the line before a definition to collect tagged comments.
    Stops at first non-comment, non-blank line.
    """
    tags: dict[str, list[str]] = {}
    i = end_lineno - 2  # 0-indexed, line before the def/class

    while i >= 0:
        line = lines[i].strip()
        if not line or line.startswith("#"):
            match = TAG_PATTERN.match(line)
            if match:
                tag_name = match.group(1).upper()
                tag_value = match.group(2).strip()
                tags.setdefault(tag_name, []).append(tag_value)
            i -= 1
        else:
            break

    # Reverse so tags appear in source order
    for key in tags:
        tags[key].reverse()

    return tags


# ── AST walking ─────────────────────────────────────────────

def format_args(node: ast.FunctionDef) -> str:
    """Extract simplified argument signature."""
    args = []
    all_args = node.args.args.copy()

    # Skip 'self' and 'cls'
    if all_args and all_args[0].arg in ("self", "cls"):
        all_args = all_args[1:]

    for arg in all_args:
        name = arg.arg
        if arg.annotation:
            try:
                ann = ast.unparse(arg.annotation)
                name = f"{name}: {ann}"
            except Exception:
                pass
        args.append(name)

    return ", ".join(args)


def format_return(node: ast.FunctionDef) -> str:
    """Extract return type annotation if present."""
    if node.returns:
        try:
            return f" -> {ast.unparse(node.returns)}"
        except Exception:
            pass
    return ""


def extract_entities(filepath: Path) -> list[dict]:
    """
    Parse a Python file and extract classes, methods, functions,
    and their tagged comments.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    entities = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            tags = parse_tags_from_lines(lines, node.lineno)

            # Check for base classes
            bases = ""
            if node.bases:
                try:
                    bases = "(" + ", ".join(ast.unparse(b) for b in node.bases) + ")"
                except Exception:
                    pass

            entities.append({
                "type": "class",
                "name": f"{node.name}{bases}",
                "tags": tags,
                "methods": [],
            })

            # Extract methods
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue  # Skip private methods
                    mtags = parse_tags_from_lines(lines, item.lineno)
                    sig = format_args(item)
                    ret = format_return(item)
                    entities[-1]["methods"].append({
                        "name": f".{item.name}({sig}){ret}" if item.name != "__init__" else f"__init__({sig})",
                        "tags": mtags,
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tags = parse_tags_from_lines(lines, node.lineno)
            sig = format_args(node)
            ret = format_return(node)
            entities.append({
                "type": "function",
                "name": f"{node.name}({sig}){ret}",
                "tags": tags,
            })

        elif isinstance(node, ast.Assign):
            # Detect route-like patterns: router.get("/path")
            # This is a heuristic — adjust for your framework
            pass

    return entities


# ── Route detection (FastAPI / Flask) ───────────────────────

ROUTE_PATTERN = re.compile(
    r"""@(?:app|router|bp)\.(get|post|put|patch|delete|head|options)\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def extract_routes(filepath: Path) -> list[dict]:
    """Extract HTTP routes from decorators."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    lines = source.splitlines()
    routes = []

    for i, line in enumerate(lines):
        match = ROUTE_PATTERN.search(line)
        if match:
            method = match.group(1).upper()
            path = match.group(2)

            # Look for the function below and its tags
            tags = {}
            for j in range(i + 1, min(i + 5, len(lines))):
                func_match = re.match(r"^(?:async\s+)?def\s+(\w+)", lines[j])
                if func_match:
                    tags = parse_tags_from_lines(lines, j + 1)
                    break

            # Find description from tags
            desc = ""
            if "DESCRIPTION" in tags:
                desc = tags.pop("DESCRIPTION")[0]

            routes.append({
                "method": method,
                "path": path,
                "desc": desc,
                "tags": tags,
            })

    return routes


# ── Map generation ──────────────────────────────────────────

def build_tree(root: Path, scan_dirs: list[str]) -> dict:
    """Build a nested dict representing the project file tree with entities."""
    tree = {}

    for scan_dir in scan_dirs:
        base = root / scan_dir
        if not base.exists():
            continue

        for pyfile in sorted(base.rglob("*.py")):
            rel = pyfile.relative_to(root)
            parts = list(rel.parts)

            # Navigate/create nested dict
            node = tree
            for part in parts[:-1]:  # directories
                node = node.setdefault(part + "/", {})

            # File entry
            filename = parts[-1]
            entities = extract_entities(pyfile)
            routes = extract_routes(pyfile)
            try:
                file_lines = pyfile.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                file_lines = []
            file_desc = extract_file_description(file_lines)

            node[filename] = {
                "_entities": entities,
                "_routes": routes,
                "_file_desc": file_desc,
            }

    return tree


def render_tags(tags: dict[str, list[str]], indent: str) -> list[str]:
    """Render non-description tags as indented lines."""
    lines = []
    for tag_name in ("TODO", "WARNING", "DEPRECATED", "PERF", "HACK", "DEPENDS"):
        for value in tags.get(tag_name, []):
            lines.append(f"{indent}{tag_name}: {value}")
    return lines


def render_tree(tree: dict, indent: int = 0) -> list[str]:
    """Recursively render the tree to map lines."""
    lines = []
    pad = "  " * indent

    for key in sorted(tree.keys()):
        value = tree[key]

        if key.endswith("/"):
            # Directory
            lines.append(f"{pad}{key}")
            lines.extend(render_tree(value, indent + 1))

        elif isinstance(value, dict) and "_entities" in value:
            # File
            entities = value["_entities"]
            routes = value["_routes"]
            file_desc = value.get("_file_desc", "")

            # Skip __init__.py if empty
            if key == "__init__.py" and not entities and not routes and not file_desc:
                continue

            # Render filename — inline desc if single line, block if multi-line
            desc_lines_list = file_desc.splitlines() if file_desc else []
            if len(desc_lines_list) == 1:
                align_pad = max(2, 42 - len(key))
                lines.append(f"{pad}{key}{' ' * align_pad}# {desc_lines_list[0]}")
            else:
                lines.append(f"{pad}{key}")
                for dl in desc_lines_list:
                    lines.append(f"{pad}  # {dl}" if dl else f"{pad}  #")

            # Render routes
            for route in routes:
                desc_part = f"  # {route['desc']}" if route["desc"] else ""
                lines.append(f"{pad}  {route['method']:6s} {route['path']}{desc_part}")
                lines.extend(render_tags(route["tags"], f"{pad}    "))

            # Render entities
            for entity in entities:
                if entity["type"] == "class":
                    desc = entity["tags"].get("DESCRIPTION", [""])[0]
                    desc_part = f"  # {desc}" if desc else ""

                    # Align descriptions to column 44 from entity start
                    name = entity["name"]
                    align_pad = max(2, 40 - len(name))
                    lines.append(f"{pad}  {name}{' ' * align_pad}{desc_part.strip()}")
                    lines.extend(render_tags(entity["tags"], f"{pad}    "))

                    for method in entity.get("methods", []):
                        mdesc = method["tags"].get("DESCRIPTION", [""])[0]
                        mdesc_part = f"  # {mdesc}" if mdesc else ""
                        mname = method["name"]
                        malign_pad = max(2, 38 - len(mname))
                        lines.append(f"{pad}    {mname}{' ' * malign_pad}{mdesc_part.strip()}")
                        lines.extend(render_tags(method["tags"], f"{pad}      "))

                elif entity["type"] == "function":
                    desc = entity["tags"].get("DESCRIPTION", [""])[0]
                    desc_part = f"  # {desc}" if desc else ""
                    name = entity["name"]
                    align_pad = max(2, 40 - len(name))
                    lines.append(f"{pad}  {name}{' ' * align_pad}{desc_part.strip()}")
                    lines.extend(render_tags(entity["tags"], f"{pad}    "))

    return lines


# ── Config file detection ───────────────────────────────────

CONFIG_FILES = [
    ("pyproject.toml", "Project config"),
    ("setup.py", "Legacy setup"),
    ("setup.cfg", "Legacy config"),
    ("alembic.ini", "Alembic migrations config"),
    ("docker-compose.yml", "Docker services"),
    ("docker-compose.yaml", "Docker services"),
    ("Dockerfile", "Container build"),
    (".env.example", "Environment template"),
    ("Makefile", "Build commands"),
    ("tox.ini", "Test runner config"),
    ("pytest.ini", "Pytest config"),
    (".pre-commit-config.yaml", "Pre-commit hooks"),
]


def detect_configs(root: Path) -> list[str]:
    """Detect known config files in root."""
    lines = []
    for filename, desc in CONFIG_FILES:
        if (root / filename).exists():
            pad = max(2, 44 - len(filename))
            lines.append(f"{filename}{' ' * pad}# {desc}")
    return lines


# ── Test summary ────────────────────────────────────────────

def summarize_tests(root: Path, test_dir: str = "tests") -> list[str]:
    """Count test functions per test file."""
    lines = []
    test_path = root / test_dir
    if not test_path.exists():
        return lines

    for pyfile in sorted(test_path.rglob("*.py")):
        rel = pyfile.relative_to(root / test_dir)

        try:
            source = pyfile.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        # Count test functions
        test_count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )

        file_lines = source.splitlines()

        if str(rel) == "conftest.py":
            # List fixtures
            fixtures = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    tags = parse_tags_from_lines(file_lines, node.lineno)
                    desc = tags.get("DESCRIPTION", [""])[0]
                    # Check for @pytest.fixture decorator
                    is_fixture = any(
                        (isinstance(d, ast.Name) and d.id == "fixture")
                        or (isinstance(d, ast.Attribute) and d.attr == "fixture")
                        or (isinstance(d, ast.Call) and (
                            (isinstance(d.func, ast.Attribute) and d.func.attr == "fixture")
                            or (isinstance(d.func, ast.Name) and d.func.id == "fixture")
                        ))
                        for d in node.decorator_list
                    )
                    if is_fixture:
                        desc_part = f"  # {desc}" if desc else ""
                        name = node.name
                        pad = max(2, 40 - len(name))
                        fixtures.append(f"    {name}{' ' * pad}{desc_part.strip()}")
                        # Add tags
                        for tag_line in render_tags(tags, "      "):
                            fixtures.append(tag_line)

            if fixtures:
                lines.append(f"  conftest.py")
                lines.extend(fixtures)
        else:
            if test_count > 0:
                tags = parse_tags_from_lines(file_lines, 1)  # File-level tags
                desc_parts = []
                if test_count:
                    desc_parts.append(f"{test_count} tests")
                desc_tag = tags.get("DESCRIPTION", [""])[0]
                if desc_tag:
                    desc_parts.append(desc_tag)
                desc = ", ".join(desc_parts)

                name = str(rel)
                pad = max(2, 42 - len(name))
                lines.append(f"  {name}{' ' * pad}# {desc}")
                lines.extend(render_tags(tags, "    "))

    return lines


# ── Main ────────────────────────────────────────────────────

HEADER = """# Project map — {name}
# Updated: {date}
# Generator: scripts/gen_map.py
#
# Tags in source code:
#   At file top:              # <FILEDESCRIPTION>: what this file is for
#   Above functions/classes:  # <Description>: what it does
#                             # <TODO>: planned work
#                             # <WARNING>: known risk
#                             # <DEPRECATED>: use X instead
#                             # <PERF>: performance note
#                             # <HACK>: temporary workaround
#                             # <DEPENDS>: critical dependency
"""


def generate_map(
    root: Path,
    scan_dirs: list[str],
    test_dir: str = "tests",
    project_name: Optional[str] = None,
) -> str:
    """Generate the complete project map."""
    name = project_name or root.name
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [HEADER.format(name=name, date=date)]

    # Source tree
    tree = build_tree(root, scan_dirs)
    if tree:
        parts.append("# ── Source ──────────────────────────────────────────────────\n")
        parts.append("\n".join(render_tree(tree)))

    # Config files
    configs = detect_configs(root)
    if configs:
        parts.append("\n# ── Config ──────────────────────────────────────────────────\n")
        parts.append("\n".join(configs))

    # Tests
    test_lines = summarize_tests(root, test_dir)
    if test_lines:
        parts.append("\n# ── Tests ───────────────────────────────────────────────────\n")
        parts.append(f"{test_dir}/")
        parts.append("\n".join(test_lines))

    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Generate PROJECT_MAP.md from source")
    parser.add_argument("--root", type=Path, default=Path("."), help="Project root")
    parser.add_argument("--dirs", nargs="+", default=["src", "app", "lib"], help="Source dirs to scan")
    parser.add_argument("--test-dir", default="tests", help="Test directory")
    parser.add_argument("--name", default=None, help="Project name override")
    parser.add_argument("--output", type=Path, default=None, help="Output file (default: PROJECT_MAP.md)")
    parser.add_argument("--watch", action="store_true", help="Watch for changes and regenerate")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of file")

    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "PROJECT_MAP.md"

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.src_path.endswith(".py"):
                        print(f"  Changed: {event.src_path}")
                        result = generate_map(root, args.dirs, args.test_dir, args.name)
                        output.write_text(result, encoding="utf-8")
                        print(f"  Updated: {output}")

            observer = Observer()
            for d in args.dirs + [args.test_dir]:
                scan_path = root / d
                if scan_path.exists():
                    observer.schedule(Handler(), str(scan_path), recursive=True)

            print(f"Watching {args.dirs} for changes... (Ctrl+C to stop)")
            observer.start()

            # Initial generation
            result = generate_map(root, args.dirs, args.test_dir, args.name)
            output.write_text(result, encoding="utf-8")
            print(f"Generated: {output}")

            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        except ImportError:
            print("Install watchdog for --watch: pip install watchdog", file=sys.stderr)
            sys.exit(1)
    else:
        result = generate_map(root, args.dirs, args.test_dir, args.name)
        if args.stdout:
            print(result)
        else:
            output.write_text(result, encoding="utf-8")
            print(f"Generated: {output}")


if __name__ == "__main__":
    main()