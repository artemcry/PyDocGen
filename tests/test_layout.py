"""Tests for Stage 7: Layout Generator & HTML Output."""

import pytest
from slop_doc.layout import (
    generate_nav_tree, generate_breadcrumb, generate_contents_sidebar,
    assemble_page, BreadcrumbItem, Node, _assets_prefix, _relative_url
)


class TestNavTree:
    """Test navigation tree generation."""

    def test_nav_tree_html(self):
        """Tree with 3 levels."""
        tree = [
            Node(title="Introduction", template="intro", output_path="introduction.html"),
            Node(title="API Reference", template="api", output_path="api-reference.html", children=[
                Node(title="DataFlow", template="module", output_path="api-reference/dataflow.html", children=[
                    Node(title="Pipeline", template="class", output_path="api-reference/dataflow/pipeline.html")
                ])
            ])
        ]

        html = generate_nav_tree(tree)
        assert "Introduction" in html
        assert "API Reference" in html
        assert "DataFlow" in html
        assert "Pipeline" in html

    def test_nav_current_highlighted(self):
        """Current node has active class, parents expanded."""
        tree = [
            Node(title="API Reference", template="api", output_path="api-reference.html", children=[
                Node(title="Pipeline", template="class", output_path="api-reference/dataflow/pipeline.html")
            ])
        ]

        current = tree[0].children[0]
        html = generate_nav_tree(tree, current)

        assert "active" in html
        # Current page uses relative href (pipeline.html from same dir)
        assert 'href="pipeline.html"' in html


class TestBreadcrumb:
    """Test breadcrumb generation."""

    def test_breadcrumb(self):
        """Node at path Root > API > DataFlow > Pipeline."""
        tree = [
            Node(title="API Reference", template="api", output_path="api-reference.html", children=[
                Node(title="DataFlow", template="module", output_path="api-reference/dataflow.html", children=[
                    Node(title="Pipeline", template="class", output_path="api-reference/dataflow/pipeline.html")
                ])
            ])
        ]

        pipeline_node = tree[0].children[0].children[0]
        breadcrumb = generate_breadcrumb(pipeline_node, tree)

        assert len(breadcrumb) == 3
        assert breadcrumb[0].title == "API Reference"
        assert breadcrumb[1].title == "DataFlow"
        assert breadcrumb[2].title == "Pipeline"


class TestContentsSidebar:
    """Test contents sidebar generation."""

    def test_contents_sidebar(self):
        """Page with 3 h2 and 2 h3."""
        html_content = '''
<h2 id="public-methods">Public Methods</h2>
<p>Content</p>
<h2 id="private-methods">Private Methods</h2>
<p>More content</p>
<h3 id="run-method">The run Method</h3>
<p>Details</p>
<h3 id="stop-method">The stop Method</h3>
'''

        sidebar = generate_contents_sidebar(html_content)
        assert "Public Methods" in sidebar
        assert "Private Methods" in sidebar
        assert "The run Method" in sidebar
        assert "The stop Method" in sidebar


class TestFullPageAssembly:
    """Test complete page assembly."""

    def test_full_page_assembly(self):
        """Rendered content + tree + node assembles into valid HTML."""
        tree = [
            Node(title="Introduction", template="intro", output_path="introduction.html")
        ]

        node = tree[0]
        content = "<h1>Introduction</h1><p>Welcome to the documentation.</p>"

        html = assemble_page(content, node, tree, "MyProject", "1.0.0")

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "Introduction" in html
        assert "MyProject" in html
        assert "introduction.html" in html


class TestSearchIndex:
    """Test search index generation."""

    def test_search_index(self):
        """Tree with multiple nodes generates JSON index."""
        from slop_doc.layout import generate_search_index
        import json

        tree = [
            Node(title="Introduction", template="intro", output_path="introduction.html"),
            Node(title="API Reference", template="api", output_path="api-reference.html")
        ]

        index_json = generate_search_index(tree, {})

        # Should be valid JSON
        index = json.loads(index_json)

        # Should have entries for both nodes
        assert len(index) == 2
        titles = [entry['title'] for entry in index]
        assert "Introduction" in titles
        assert "API Reference" in titles


class TestAssetsPrefix:
    """Test _assets_prefix function."""

    def test_root_page(self):
        """introduction.html has no prefix."""
        assert _assets_prefix("introduction.html") == ""

    def test_one_level_deep(self):
        """api-reference/dataflow.html has ../ prefix."""
        assert _assets_prefix("api-reference/dataflow.html") == "../"

    def test_two_levels_deep(self):
        """api-reference/dataflow/pipeline.html has ../../ prefix."""
        assert _assets_prefix("api-reference/dataflow/pipeline.html") == "../../"


class TestRelativeUrl:
    """Test _relative_url function."""

    def test_same_directory(self):
        """From 'a.html' to 'b.html'."""
        result = _relative_url("a.html", "b.html")
        assert result == "b.html"

    def test_from_subdir_to_sibling(self):
        """From 'api/a.html' to 'api/b.html'."""
        result = _relative_url("api/a.html", "api/b.html")
        assert result == "b.html"

    def test_from_subdir_to_parent(self):
        """From 'api/dataflow/a.html' to 'api/b.html'."""
        result = _relative_url("api/dataflow/a.html", "api/b.html")
        assert result == "../b.html"

    def test_from_parent_to_subdir(self):
        """From 'api/a.html' to 'api/dataflow/b.html'."""
        result = _relative_url("api/a.html", "api/dataflow/b.html")
        assert result == "dataflow/b.html"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
