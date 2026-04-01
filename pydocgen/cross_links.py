"""Stage 5: Cross-Link Index & Resolver - builds cross-reference index and resolves links."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydocgen.tree_builder import Node
    from pydocgen.parser import SourceData


class CrossLinkError(Exception):
    """Raised when cross-link resolution fails."""
    pass


# Pattern to match [[Target]] or [[Target|display text]] or [[Target.method]]
CROSS_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


@dataclass
class LinkTarget:
    """Represents a resolved link target."""
    url: str
    anchor: str | None = None


class CrossLinkIndex:
    """Global index for cross-reference resolution."""

    def __init__(self):
        # Short name → list of (url, display_name, module_path)
        self.short_index: dict[str, list[tuple[str, str, str]]] = {}
        # Fully qualified name → url
        self.qualified_index: dict[str, str] = {}
        # Module path for disambiguation
        self.module_paths: dict[str, str] = {}  # node_path → module_name

    def add_node(self, node: Node, source_data: SourceData | None = None) -> None:
        """Add a node to the index.

        Args:
            node: The node to add.
            source_data: Optional SourceData for extracting class/function names.
        """
        url = node.output_path

        # Add class names
        if source_data:
            for cls in source_data.classes:
                # Fully qualified: module.ClassName
                module_name = node.title
                fq_name = f"{module_name}.{cls.name}" if module_name else cls.name

                self.qualified_index[fq_name] = url

                # Short name with module context for disambiguation
                key = (cls.name, module_name)
                if cls.name not in self.short_index:
                    self.short_index[cls.name] = []
                self.short_index[cls.name].append((url, cls.name, module_name))

                # Add method names: ClassName.method
                for method in cls.methods:
                    method_key = f"{cls.name}.{method.name}"
                    method_url = f"{url}#{method.name}"
                    self.qualified_index[method_key] = method_url
                    self.short_index[method.name] = self.short_index.get(method.name, [])
                    self.short_index[method.name].append((method_url, method.name, module_name))

            # Add function names
            for func in source_data.functions:
                fq_name = f"{node.title}.{func.name}" if node.title else func.name
                self.qualified_index[fq_name] = url

                if func.name not in self.short_index:
                    self.short_index[func.name] = []
                self.short_index[func.name].append((url, func.name, node.title))

        # Add node title itself
        if node.title:
            self.short_index[node.title] = self.short_index.get(node.title, [])
            self.short_index[node.title].append((url, node.title, node.title))

    def resolve(self, target: str) -> LinkTarget:
        """Resolve a link target to a URL.

        Args:
            target: The link target (e.g., "Pipeline", "Pipeline.run", "dataflow.Pipeline").

        Returns:
            LinkTarget with URL and optional anchor.

        Raises:
            CrossLinkError: If target is not found or ambiguous.
        """
        anchor = None

        # Check for method anchor: "ClassName.method"
        if '.' in target and not target.startswith('.'):
            parts = target.rsplit('.', 1)
            if len(parts) == 2:
                class_name, method_name = parts
                # Look for class_name.method in qualified index
                fq_key = f"{class_name}.{method_name}"
                if fq_key in self.qualified_index:
                    return LinkTarget(url=self.qualified_index[fq_key], anchor=method_name)

                # Try module-qualified form
                for fq_name, url in self.qualified_index.items():
                    if fq_name.endswith(fq_key):
                        return LinkTarget(url=url, anchor=method_name)

        # Check for fully qualified name
        if target in self.qualified_index:
            return LinkTarget(url=self.qualified_index[target])

        # Try to find by short name
        if target in self.short_index:
            entries = self.short_index[target]
            if len(entries) == 1:
                return LinkTarget(url=entries[0][0])
            else:
                # Multiple matches - need disambiguation
                suggestions = [f"[[{entry[2]}.{target}]]" for entry in entries]
                raise CrossLinkError(
                    f"Ambiguous target '{target}'. Use fully qualified name. "
                    f"Suggestions: {', '.join(suggestions)}"
                )

        # Not found
        raise CrossLinkError(f"Cross-link target '{target}' not found in index")


def resolve_links(text: str, index: CrossLinkIndex) -> str:
    """Resolve [[Target]] patterns in text to HTML links.

    Args:
        text: Text containing [[Target]] patterns.
        index: CrossLinkIndex for resolving targets.

    Returns:
        Text with [[Target]] replaced by <a href> tags.

    Raises:
        CrossLinkError: If a target cannot be resolved.
    """
    def replace_link(match):
        target = match.group(1).strip()
        display_text = match.group(2)  # Could be None for [[Target]]

        try:
            link = index.resolve(target)
            if link.anchor:
                href = f"{link.url}#{link.anchor}"
            else:
                href = link.url

            if display_text:
                return f'<a href="{href}">{display_text}</a>'
            else:
                return f'<a href="{href}">{target}</a>'
        except CrossLinkError as e:
            raise CrossLinkError(f"Error resolving link [[{target}]]: {e}")

    return CROSS_LINK_PATTERN.sub(replace_link, text)


def build_index(tree: list[Node], source_data_by_folder: dict[str, SourceData]) -> CrossLinkIndex:
    """Build the global cross-link index from the tree.

    Args:
        tree: The navigation tree.
        source_data_by_folder: Dict mapping source folder paths to SourceData.

    Returns:
        CrossLinkIndex with all targets indexed.
    """
    index = CrossLinkIndex()

    def process_node(node: Node):
        # Get source data for this node
        source_data = None
        if node.source and node.source in source_data_by_folder:
            source_data = source_data_by_folder[node.source]

        index.add_node(node, source_data)

        # Process children
        for child in node.children:
            process_node(child)

    for root_node in tree:
        process_node(root_node)

    return index
