"""Tests for Stage 5: Cross-Link Index & Resolver."""

import pytest
from pydocgen.cross_links import (
    CrossLinkIndex, resolve_links, build_index, CrossLinkError
)
from pydocgen.tree_builder import Node
from pydocgen.parser import SourceData, ClassData, FunctionData


class TestResolveClassLink:
    """Test resolving class links."""

    def test_resolve_class_link(self):
        """See [[Pipeline]], index has Pipeline."""
        index = CrossLinkIndex()
        index.qualified_index["Pipeline"] = "/api-reference/dataflow/pipeline-class.html"
        index.short_index["Pipeline"] = [
            ("/api-reference/dataflow/pipeline-class.html", "Pipeline", "DataFlow")
        ]

        text = "See [[Pipeline]]"
        result = resolve_links(text, index)
        assert '<a href="/api-reference/dataflow/pipeline-class.html">Pipeline</a>' in result

    def test_resolve_method_link(self):
        """Call [[Pipeline.run]]."""
        index = CrossLinkIndex()
        index.qualified_index["Pipeline.run"] = "/api-reference/dataflow/pipeline-class.html#run"

        text = "Call [[Pipeline.run]]"
        result = resolve_links(text, index)
        assert "#run" in result

    def test_resolve_custom_text(self):
        """[[Pipeline|the main class]]."""
        index = CrossLinkIndex()
        index.qualified_index["Pipeline"] = "/api-reference/dataflow/pipeline-class.html"
        index.short_index["Pipeline"] = [
            ("/api-reference/dataflow/pipeline-class.html", "Pipeline", "DataFlow")
        ]

        text = "[[Pipeline|the main class]]"
        result = resolve_links(text, index)
        assert 'href="/api-reference/dataflow/pipeline-class.html"' in result
        assert "the main class" in result

    def test_resolve_not_found(self):
        """[[NonExistent]] should raise error."""
        index = CrossLinkIndex()

        text = "[[NonExistent]]"
        with pytest.raises(CrossLinkError) as exc:
            resolve_links(text, index)
        assert "NonExistent" in str(exc.value)

    def test_ambiguous_name(self):
        """Two classes named 'Config' in different modules."""
        index = CrossLinkIndex()
        index.short_index["Config"] = [
            ("/api-reference/utils/config.html", "Config", "Utils"),
            ("/api-reference/core/config.html", "Config", "Core"),
        ]

        text = "[[Config]]"
        with pytest.raises(CrossLinkError) as exc:
            resolve_links(text, index)
        assert "Ambiguous" in str(exc.value)
        assert "Suggestions:" in str(exc.value)

    def test_fully_qualified(self):
        """[[dataflow.Pipeline]] resolves correctly even with ambiguity."""
        index = CrossLinkIndex()
        index.qualified_index["dataflow.Pipeline"] = "/api-reference/dataflow/pipeline-class.html"

        text = "[[dataflow.Pipeline]]"
        result = resolve_links(text, index)
        assert "pipeline-class.html" in result

    def test_no_links(self):
        """No links in text returns unchanged."""
        index = CrossLinkIndex()

        text = "No links here"
        result = resolve_links(text, index)
        assert result == text


class TestBuildIndex:
    """Test building the cross-link index."""

    def test_build_index_with_classes(self):
        """Index built from tree with class nodes."""
        tree = [
            Node(
                title="DataFlow",
                template="module",
                output_path="/api-reference/dataflow/index.html",
                source="/path/to/src/dataflow"
            )
        ]
        source_data = {
            "/path/to/src/dataflow": SourceData(
                classes=[ClassData(name="Pipeline", base_classes=[], decorators=[])],
                functions=[],
                constants=[]
            )
        }

        index = build_index(tree, source_data)

        assert "Pipeline" in index.short_index
        # Classes are stored as "module.ClassName" in qualified_index
        assert "DataFlow.Pipeline" in index.qualified_index

    def test_build_index_with_methods(self):
        """Index includes method anchors."""
        tree = [
            Node(
                title="DataFlow",
                template="module",
                output_path="/api-reference/dataflow/index.html",
                source="/path/to/src/dataflow"
            )
        ]
        source_data = {
            "/path/to/src/dataflow": SourceData(
                classes=[
                    ClassData(
                        name="Pipeline",
                        base_classes=[],
                        decorators=[],
                        methods=[
                            FunctionData(name="run", args=[], decorators=[]),
                            FunctionData(name="stop", args=[], decorators=[])
                        ]
                    )
                ],
                functions=[],
                constants=[]
            )
        }

        index = build_index(tree, source_data)

        # Should have Pipeline.run and Pipeline.stop
        assert "Pipeline.run" in index.qualified_index
        assert "Pipeline.stop" in index.qualified_index
        assert index.qualified_index["Pipeline.run"] == "/api-reference/dataflow/index.html#run"


class TestCrossLinkPattern:
    """Test the cross-link pattern matching."""

    def test_pattern_simple(self):
        """Simple [[Target]] pattern."""
        import re
        CROSS_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

        text = "[[Pipeline]]"
        match = CROSS_LINK_PATTERN.search(text)
        assert match.group(1) == "Pipeline"
        assert match.group(2) is None

    def test_pattern_with_display(self):
        """[[Target|display text]] pattern."""
        import re
        CROSS_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

        text = "[[Pipeline|the main class]]"
        match = CROSS_LINK_PATTERN.search(text)
        assert match.group(1) == "Pipeline"
        assert match.group(2) == "the main class"

    def test_pattern_with_method(self):
        """[[Target.method]] pattern."""
        import re
        CROSS_LINK_PATTERN = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')

        text = "[[Pipeline.run]]"
        match = CROSS_LINK_PATTERN.search(text)
        assert match.group(1) == "Pipeline.run"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
