"""Cross-Link Index & Resolver — builds cross-reference index and resolves links.

Link format in Markdown:
    [[folder/ClassName]]           → link to class page
    [[folder/ClassName.method]]    → link to method anchor on class page
    [[folder/ClassName|display]]   → link with custom display text
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slop_doc.tree_builder import Node
    from slop_doc.parser import SourceData


class CrossLinkError(Exception):
    """Raised when cross-link resolution fails."""
    pass


# [[Target]] or [[Target|display text]]
CROSS_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


@dataclass
class LinkTarget:
    """Resolved link target."""
    url: str
    anchor: str | None = None


class CrossLinkIndex:
    """Global index for cross-reference resolution."""

    def __init__(self):
        # "folder/ClassName" → url
        self.folder_class_index: dict[str, str] = {}
        # Short name → list of (url, display_name, context)
        self.short_index: dict[str, list[tuple[str, str, str]]] = {}
        # Fully qualified name → url
        self.qualified_index: dict[str, str] = {}

    def resolve(self, target: str) -> LinkTarget:
        """Resolve a link target to a URL.

        Args:
            target: "folder/ClassName" or "folder/ClassName.method" format.

        Returns:
            LinkTarget with URL and optional anchor.

        Raises:
            CrossLinkError: If target not found or invalid format.
        """
        if '/' not in target:
            raise CrossLinkError(
                f"Invalid cross-link format '{target}'. "
                "Use 'folder/ClassName' or 'folder/ClassName.method' syntax."
            )

        method_name = None
        if '.' in target:
            class_path, method_name = target.rsplit('.', 1)
        else:
            class_path = target

        if class_path not in self.folder_class_index:
            raise CrossLinkError(f"Cross-link target '{class_path}' not found in index")

        url = self.folder_class_index[class_path]
        return LinkTarget(url=url, anchor=method_name)


def resolve_links(text: str, index: CrossLinkIndex, current_page: str = "") -> str:
    """Resolve [[Target]] patterns in text to HTML links."""
    def replace_link(match):
        target = match.group(1).strip()
        display_text = match.group(2)

        try:
            link = index.resolve(target)
            href = f"{link.url}#{link.anchor}" if link.anchor else link.url

            if current_page and href:
                href = _compute_relative_path(current_page, href)

            if display_text:
                return f'<a href="{href}">{display_text}</a>'

            display = target.rsplit('/', 1)[-1] if '/' in target else target
            if '.' in display:
                display = display.rsplit('.', 1)[-1]
            return f'<a href="{href}">{display}</a>'

        except CrossLinkError:
            # Unresolved link — render as plain text with a warning class
            import sys
            print(f"Warning: unresolved cross-link [[{target}]]", file=sys.stderr)
            display = display_text or target
            return f'<span class="unresolved-link" title="Unresolved: {target}">{display}</span>'

    return CROSS_LINK_PATTERN.sub(replace_link, text)


def _compute_relative_path(from_path: str, to_path: str) -> str:
    """Compute relative URL from one page to another."""
    from_dir = os.path.dirname(from_path)
    rel = os.path.relpath(to_path, from_dir) if from_dir else to_path
    return rel.replace('\\', '/')


def _get_folder_slug(output_path: str) -> str:
    """Extract folder slug from output path."""
    base = output_path.replace('.html', '')
    parts = base.split('/')
    if len(parts) >= 2:
        return parts[-2] if parts[-1] != 'index' else parts[-2]
    return ''


# ---------------------------------------------------------------------------
# Index building  (adapted for new Node structure)
# ---------------------------------------------------------------------------

def build_index(
    tree: list[Node],
    source_data_by_folder: dict[str, SourceData],
    hidden_nodes: list[Node] | None = None,
) -> CrossLinkIndex:
    """Build the global cross-link index from the tree.

    For auto-generated class pages, the class and its methods are indexed
    at that page's URL.  For regular pages with source, all classes in the
    source are indexed at the page URL (unless overridden by a child class page).

    ``hidden_nodes`` are auto-class nodes not in the nav tree — they are
    indexed the same way as tree auto-class nodes.
    """
    index = CrossLinkIndex()
    indexed_sources: set[str] = set()

    def _source_slug(src: str) -> str:
        return os.path.basename(src.rstrip('/\\')) if src else ''

    def _index_auto_class(node: Node) -> None:
        """Index an auto-class node (tree or hidden)."""
        class_name = node.auto_class
        source_data = source_data_by_folder.get(node.source)
        if not source_data:
            return
        folder_slug = _source_slug(node.source)
        key = f"{folder_slug}/{class_name}"
        index.folder_class_index[key] = node.output_path

        # Index methods
        for cls in source_data.classes:
            if cls.name == class_name:
                for method in cls.methods:
                    mkey = f"{folder_slug}/{class_name}.{method.name}"
                    index.folder_class_index[mkey] = node.output_path
                break

    def process_node(node: Node, parent_source: str | None = None):
        # --- Auto-generated class page ---
        if node.is_auto and node.auto_class and node.source:
            _index_auto_class(node)

        # --- Regular page with source ---
        elif node.source and node.source in source_data_by_folder:
            if node.source not in indexed_sources:
                indexed_sources.add(node.source)
                source_data = source_data_by_folder[node.source]
                folder_slug = _source_slug(node.source)
                if folder_slug:
                    for cls in source_data.classes:
                        key = f"{folder_slug}/{cls.name}"
                        # Don't overwrite if a child class page already claimed it
                        if key not in index.folder_class_index:
                            index.folder_class_index[key] = node.output_path
                        for method in cls.methods:
                            mkey = f"{folder_slug}/{cls.name}.{method.name}"
                            if mkey not in index.folder_class_index:
                                index.folder_class_index[mkey] = node.output_path

        # Recurse children (process auto class pages first so they claim URLs)
        auto_children = [c for c in node.children if c.is_auto]
        other_children = [c for c in node.children if not c.is_auto]

        for child in auto_children:
            process_node(child, node.source)
        for child in other_children:
            process_node(child, node.source)

    # Index hidden nodes first — they claim URLs before fallback indexing
    for node in (hidden_nodes or []):
        _index_auto_class(node)

    # Then process the tree (auto class pages in tree take priority via overwrite)
    for root_node in tree:
        process_node(root_node, None)

    return index
