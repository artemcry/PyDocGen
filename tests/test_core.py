"""Core unit tests — frontmatter, parser, tree builder, tags, markdown, cross-links."""

import os
import tempfile
import textwrap

import pytest

from slop_doc.frontmatter import parse_frontmatter, PageMeta, FrontmatterError
from slop_doc.parser import parse_file, parse_folder, SourceData
from slop_doc.tree_builder import build_tree, build_tree_with_root, Node, slugify
from slop_doc.tag_renderer import (
    render_presentation_functions,
    render_data_tags_inline,
    expand_data_tag,
)
from slop_doc.markdown_renderer import markdown_to_html
from slop_doc.cross_links import CrossLinkIndex, build_index, resolve_links


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_py_file(tmp_path):
    """A Python source file with a class and a function."""
    src = tmp_path / "mylib"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "core.py").write_text(textwrap.dedent("""\
        class Engine:
            \"\"\"Main engine class.

            Does important things.
            \"\"\"

            def run(self, speed: int = 10) -> bool:
                \"\"\"Run the engine.

                Args:
                    speed: How fast to go.

                Returns:
                    True if started.
                \"\"\"
                return True

            @property
            def status(self) -> str:
                \"\"\"Current status.\"\"\"
                return "idle"

        def create_engine(name: str) -> Engine:
            \"\"\"Create a new engine.

            Args:
                name: Engine name.

            Returns:
                A configured Engine.
            \"\"\"
            return Engine()

        MAX_SPEED = 100
    """))
    return str(src)


@pytest.fixture
def docs_tree(tmp_path, sample_py_file):
    """A minimal docs folder with root.md + one page."""
    docs = tmp_path / "docs"
    docs.mkdir()

    (docs / "root.md").write_text(textwrap.dedent(f"""\
        {{
            "title": "Test Project",
            "project_name": "TestProj",
            "version": "0.1",
            "py_source": "{sample_py_file.replace(os.sep, '/')}"
        }}

        # Welcome to TestProj
    """))

    (docs / "guide.md").write_text(textwrap.dedent("""\
        {
            "title": "Guide"
        }

        # Getting Started

        Some content here.

        ## Installation

        Run pip install.
    """))

    return str(docs)


# ── Frontmatter ─────────────────────────────────────────────


class TestFrontmatter:
    def test_basic(self):
        meta, body = parse_frontmatter('{"title": "Hello"}\n\nBody text')
        assert meta.title == "Hello"
        assert "Body text" in body

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("# Just markdown\n\nNo JSON here.")
        assert meta.title == ""
        assert "Just markdown" in body

    def test_relaxed_json(self):
        content = textwrap.dedent("""\
            {
                // comment
                title: "Test",
                "order": 5,
            }

            Body.
        """)
        meta, body = parse_frontmatter(content)
        assert meta.title == "Test"
        assert meta.order == 5
        assert "Body." in body

    def test_py_source(self):
        meta, _ = parse_frontmatter('{"py_source": "src/mylib"}')
        assert meta.py_source == "src/mylib"

    def test_children(self):
        meta, _ = parse_frontmatter('{"children": {"classes": "{{classes}}"}}')
        assert meta.children == {"classes": "{{classes}}"}

    def test_unclosed_brace(self):
        with pytest.raises(FrontmatterError, match="missing '}'"):
            parse_frontmatter('{"title": "oops"')

    def test_invalid_json(self):
        with pytest.raises(FrontmatterError, match="Invalid"):
            parse_frontmatter('{not valid at all}')


# ── Parser ──────────────────────────────────────────────────


class TestParser:
    def test_parse_file(self, sample_py_file):
        data = parse_file(os.path.join(sample_py_file, "core.py"))
        assert len(data.classes) == 1
        assert data.classes[0].name == "Engine"
        assert data.classes[0].short_description == "Main engine class."
        assert any(m.name == "run" for m in data.classes[0].methods)
        assert any(p.name == "status" for p in data.classes[0].properties)

        assert len(data.functions) == 1
        assert data.functions[0].name == "create_engine"

        assert any(c.name == "MAX_SPEED" for c in data.constants)

    def test_parse_folder(self, sample_py_file):
        data = parse_folder(sample_py_file)
        assert len(data.classes) >= 1
        assert len(data.functions) >= 1
        assert len(data.constants) >= 1

    def test_docstring_params(self, sample_py_file):
        data = parse_file(os.path.join(sample_py_file, "core.py"))
        run = [m for m in data.classes[0].methods if m.name == "run"][0]
        assert any(p.name == "speed" for p in run.parameters)
        assert run.returns is not None


# ── Tree builder ────────────────────────────────────────────


class TestTreeBuilder:
    def test_build_tree(self, docs_tree):
        nodes, source_data = build_tree(docs_tree)
        assert len(nodes) >= 1
        titles = [n.title for n in nodes]
        assert "Guide" in titles

    def test_build_tree_with_root(self, docs_tree):
        root, source_data = build_tree_with_root(docs_tree)
        assert root.title == "Test Project"
        assert len(root.children) >= 1

    def test_source_inheritance(self, docs_tree):
        root, source_data = build_tree_with_root(docs_tree)
        # root has py_source, children should inherit it
        for child in root.children:
            if child.title == "Guide":
                assert child.source is not None

    def test_slugify(self):
        assert slugify("Hello World") == "hello-world"
        assert slugify("MyClass") == "myclass"
        assert slugify("some_func!") == "some_func"


# ── Tag renderer ────────────────────────────────────────────


class TestTagRenderer:
    def test_expand_data_tag(self, sample_py_file):
        data = parse_folder(sample_py_file)
        classes = expand_data_tag("classes", data)
        assert "Engine" in classes

        funcs = expand_data_tag("functions", data)
        assert "create_engine" in funcs

    def test_render_classes_table(self, sample_py_file):
        data = parse_folder(sample_py_file)
        result = render_presentation_functions(
            "%classes_table()%", data, "mylib"
        )
        assert "Engine" in result
        assert "<table" in result

    def test_render_data_tags_inline(self, sample_py_file):
        data = parse_folder(sample_py_file)
        result = render_data_tags_inline("Classes: {{classes}}", data, "mylib")
        assert "Engine" in result

    def test_no_source_data(self):
        # Tags that need source should fail gracefully
        result = render_presentation_functions("plain text", None, "")
        assert result == "plain text"


# ── Markdown renderer ───────────────────────────────────────


class TestMarkdown:
    def test_basic(self):
        html = markdown_to_html("# Title\n\nParagraph **bold**.")
        assert "<h1" in html
        assert "<strong>bold</strong>" in html

    def test_heading_anchors(self):
        html = markdown_to_html("## My Section\n\nText.")
        assert 'id="my-section"' in html

    def test_code_block(self):
        html = markdown_to_html("```python\nprint('hi')\n```")
        assert "<code" in html

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = markdown_to_html(md)
        assert "<table" in html


# ── Cross-links ─────────────────────────────────────────────


class TestCrossLinks:
    def test_build_and_resolve(self, docs_tree):
        root, source_data = build_tree_with_root(docs_tree)
        tree = root.children
        index = build_index(tree, source_data)
        # If source was indexed, classes should be resolvable
        # (depends on whether auto-class pages exist in this simple tree)
        assert isinstance(index, CrossLinkIndex)

    def test_resolve_links_passthrough(self):
        index = CrossLinkIndex()
        result = resolve_links("No links here.", index)
        assert result == "No links here."

    def test_unresolved_link_warning(self, capsys):
        index = CrossLinkIndex()
        result = resolve_links("See [[missing/Thing]].", index)
        assert "unresolved-link" in result
        assert "missing/Thing" in result
