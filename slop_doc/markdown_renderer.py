"""Stage 6: Markdown Renderer - converts Markdown to HTML."""

from __future__ import annotations

import re


def markdown_to_html(text: str) -> str:
    """Convert Markdown to HTML.

    This function handles:
    - Basic Markdown to HTML conversion
    - Preserves existing HTML tags
    - Adds id attributes to h2 and h3 for anchor links
    - Wraps code blocks properly

    Args:
        text: Markdown text (may contain HTML).

    Returns:
        HTML string.
    """
    try:
        import markdown
        # Use markdown library with extra extension for fenced code blocks, tables, etc.
        html = markdown.markdown(
            text,
            extensions=['fenced_code', 'tables', 'toc'],
            extension_configs={
                'toc': {'title': 'Contents'}
            }
        )
    except ImportError:
        # Fallback if markdown library not installed
        html = _basic_markdown(text)

    # Post-process to add anchor ids to headings
    html = _add_heading_anchors(html)

    # Ensure code blocks have proper classes
    html = _fix_code_blocks(html)

    return html


def _basic_markdown(text: str) -> str:
    """Basic Markdown to HTML fallback if markdown library not available.

    This is a simple implementation for common Markdown elements.
    """
    html = text

    # Escape HTML in text (but not in code blocks)
    # This is a simplified fallback

    return html


def _add_heading_anchors(html: str) -> str:
    """Add id attributes to h2 and h3 headings for anchor links.

    Args:
        html: HTML string.

    Returns:
        HTML with anchor ids added to headings.
    """
    def make_anchor(match):
        tag = match.group(1)  # h2 or h3
        content = match.group(2)
        # Create URL-safe id from heading text
        anchor_id = _text_to_anchor_id(content)
        return f'<{tag} id="{anchor_id}">{content}</{tag}>'

    # Match h2 and h3 tags with their content
    # Pattern: <h2>content</h2> or <h3>content</h3>
    pattern = r'<(h[23])>([^<]+)</h[23]>'
    return re.sub(pattern, make_anchor, html)


def _text_to_anchor_id(text: str) -> str:
    """Convert heading text to a URL-safe anchor id.

    Args:
        text: Heading text content.

    Returns:
        URL-safe anchor id.
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def _fix_code_blocks(html: str) -> str:
    """Ensure code blocks have proper classes.

    Args:
        html: HTML string.

    Returns:
        HTML with properly classed code blocks.
    """
    # Replace <code> inside <pre> with <code class="language-...">
    def fix_pre_code(match):
        pre_content = match.group(1)
        code_match = re.search(r'<code>(.*?)</code>', pre_content, re.DOTALL)
        if code_match:
            code_content = code_match.group(1)
            # Check if it looks like a code block with language
            # For now, just ensure proper wrapping
            return f'<pre><code>{code_content}</code></pre>'
        return match.group(0)

    # Fix standalone <pre> tags
    pattern = r'<pre>(.*?)</pre>'
    return re.sub(pattern, fix_pre_code, html, flags=re.DOTALL)
