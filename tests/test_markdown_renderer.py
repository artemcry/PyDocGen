"""Tests for Stage 6: Markdown Renderer."""

import pytest


class TestBasicMarkdown:
    """Test basic Markdown to HTML conversion."""

    def test_basic_markdown(self):
        """# Title and paragraph text."""
        from slop_doc.markdown_renderer import markdown_to_html

        text = "# Title\nParagraph text"
        result = markdown_to_html(text)
        # Markdown library produces h1 with id attribute
        assert "Title" in result
        assert "<p>Paragraph text</p>" in result

    def test_preserve_html(self):
        """Existing HTML is preserved."""
        from slop_doc.markdown_renderer import markdown_to_html

        text = "<div class='custom'>text</div>"
        result = markdown_to_html(text)
        assert "<div class='custom'>" in result

    def test_mixed_content(self):
        """Markdown and HTML mixed correctly."""
        from slop_doc.markdown_renderer import markdown_to_html

        text = "## Header\n<div>html</div>\nMore **markdown**"
        result = markdown_to_html(text)
        assert "Header" in result
        assert "<div>" in result


class TestHeadingAnchors:
    """Test heading anchor id generation."""

    def test_heading_anchors(self):
        """## Public Methods becomes <h2 id="public-methods">Public Methods</h2>."""
        from slop_doc.markdown_renderer import markdown_to_html

        text = "## Public Methods"
        result = markdown_to_html(text)
        assert 'id="public-methods"' in result

    def test_text_to_anchor_id(self):
        """Test the anchor id generation."""
        from slop_doc.markdown_renderer import _text_to_anchor_id

        assert _text_to_anchor_id("Public Methods") == "public-methods"
        assert _text_to_anchor_id("API Reference") == "api-reference"
        assert _text_to_anchor_id("Class Name (C++)") == "class-name-c"


class TestCodeBlocks:
    """Test code block rendering."""

    def test_code_blocks(self):
        """Fenced code block with python."""
        from slop_doc.markdown_renderer import markdown_to_html

        text = "```python\nprint('hello')\n```"
        result = markdown_to_html(text)
        assert "<code" in result
        assert "python" in result or "language-python" in result


class TestExtractHeadings:
    """Test extracting headings for table of contents."""

    def test_extract_headings(self):
        """Extract h2 and h3 with their anchor ids."""
        from slop_doc.markdown_renderer import extract_headings

        html = '''
<h2 id="public-methods">Public Methods</h2>
<p>Content</p>
<h3 id="run-method">The run Method</h3>
<p>More content</h3>
'''
        headings = extract_headings(html)
        assert ("public-methods", "Public Methods") in headings
        assert ("run-method", "The run Method") in headings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
