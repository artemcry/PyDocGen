"""Tests for Stage 1: Python Source Parser."""

import os
import tempfile
import pytest
from slop_doc.parser import (
    parse_file, parse_folder, parse_google_docstring,
    SourceData, ClassData, FunctionData, ConstantData,
    ArgData, PropertyData, ParamDoc, ReturnDoc, RaiseDoc
)


class TestParseSimpleClass:
    """Test parsing a simple class with methods and properties."""

    def test_parse_simple_class(self):
        code = '''
class Pipeline:
    """A data processing pipeline that chains nodes together."""

    def __init__(self, name: str = "default"):
        """Initialize the pipeline."""
        self.name = name

    @property
    def node_count(self) -> int:
        """Number of registered nodes."""
        return len(self._nodes)

    def add_node(self, node: "BaseNode") -> None:
        """Add a processing node to the pipeline."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.classes) == 1
            cls = data.classes[0]
            assert cls.name == "Pipeline"
            assert len(cls.methods) == 2  # __init__, add_node (node_count is a property)
            assert len(cls.properties) == 1
            assert len(cls.properties) == 1
            assert cls.properties[0].name == "node_count"
            assert cls.properties[0].type == "int"
        finally:
            os.unlink(filepath)


class TestParseGoogleDocstring:
    """Test parsing Google-style docstrings."""

    def test_parse_full_google_docstring(self):
        docstring = '''Runs the pipeline with the given configuration.

Executes all registered nodes in order. If a node fails,
the pipeline stops and returns False.

Args:
    timeout: Maximum seconds to wait for completion.
    verbose: If True, prints progress to stdout.

Returns:
    True if all nodes completed successfully, False otherwise.

Raises:
    PipelineError: If no nodes are registered.
    TimeoutError: If execution exceeds timeout.

Examples:
    >>> p = Pipeline()
    >>> p.run(timeout=60)
    True'''

        short, full, params, returns, raises, examples = parse_google_docstring(docstring)

        assert short == "Runs the pipeline with the given configuration."
        assert "Executes all registered nodes" in full
        assert len(params) == 2
        assert params[0].name == "timeout"
        assert params[0].type is None  # No type in docstring (type hints would be used)
        assert "Maximum seconds" in params[0].description
        assert params[1].name == "verbose"
        assert returns is not None
        assert "True" in returns.description
        assert len(raises) == 2
        assert raises[0].type == "PipelineError"
        assert ">>> p = Pipeline()" in examples

    def test_parse_empty_docstring(self):
        short, full, params, returns, raises, examples = parse_google_docstring("")
        assert short == ""
        assert full == ""
        assert params == []
        assert returns is None


class TestParseTypeHintsPriority:
    """Test that type hints take priority over docstring types."""

    def test_type_hints_priority(self):
        code = '''
def process(value: int) -> str:
    """Process a value.

    Args:
        value: A number to process.

    Returns:
        The processed string.
    """
    return str(value)
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.functions) == 1
            func = data.functions[0]
            assert func.return_type == "str"
            assert len(func.args) == 1
            assert func.args[0].type == "int"
        finally:
            os.unlink(filepath)


class TestParseConstants:
    """Test parsing module-level constants."""

    def test_parse_constants(self):
        code = '''
MAX_SIZE = 100
PAGE_SIZE = 50
regular_var = "hello"
Private = 123
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            const_names = [c.name for c in data.constants]
            assert "MAX_SIZE" in const_names
            assert "PAGE_SIZE" in const_names
            assert "regular_var" not in const_names
            assert "Private" not in const_names
        finally:
            os.unlink(filepath)


class TestSkipPrivateClasses:
    """Test that private classes are skipped."""

    def test_skip_private_classes(self):
        code = '''
class _Internal:
    """Should be skipped."""
    pass

class Public:
    """Should be included."""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            class_names = [c.name for c in data.classes]
            assert "_Internal" not in class_names
            assert "Public" in class_names
        finally:
            os.unlink(filepath)


class TestParseDecorators:
    """Test parsing decorators."""

    def test_parse_decorators(self):
        code = '''
import dataclasses

@dataclasses.dataclass
class Config:
    """A config class."""

    @staticmethod
    def default():
        """Get default config."""
        pass

    @classmethod
    def from_dict(cls, data):
        """Create from dict."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.classes) == 1
            cls = data.classes[0]
            assert "dataclass" in cls.decorators

            # Check method decorators
            method_decorators = {m.name: m.decorators for m in cls.methods}
            assert "staticmethod" in method_decorators["default"]
            assert "classmethod" in method_decorators["from_dict"]
        finally:
            os.unlink(filepath)


class TestParseBaseClasses:
    """Test parsing class base classes."""

    def test_parse_base_classes(self):
        code = '''
class Foo(Bar, Baz):
    """A class inheriting from Bar and Baz."""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.classes) == 1
            cls = data.classes[0]
            assert "Bar" in cls.base_classes
            assert "Baz" in cls.base_classes
        finally:
            os.unlink(filepath)


class TestParseEmptyFile:
    """Test parsing an empty file."""

    def test_parse_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert data.classes == []
            assert data.functions == []
            assert data.constants == []
        finally:
            os.unlink(filepath)


class TestParseProperty:
    """Test parsing @property decorated methods."""

    def test_parse_property(self):
        code = '''
class Person:
    """A person."""

    @property
    def name(self) -> str:
        """The person's name."""
        return self._name
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.classes) == 1
            cls = data.classes[0]
            assert len(cls.properties) == 1
            assert cls.properties[0].name == "name"
            assert cls.properties[0].type == "str"
        finally:
            os.unlink(filepath)


class TestParseMethodCategories:
    """Test method categorization by naming conventions."""

    def test_parse_method_categories(self):
        code = '''
class MyClass:
    """Test class."""

    def public_method(self):
        """Public method."""
        pass

    def _private_method(self):
        """Private method."""
        pass

    def __mangled_method(self):
        """Mangled method."""
        pass

    def __dunder_method__(self):
        """Dunder method."""
        pass

    @staticmethod
    def static_method():
        """Static method."""
        pass

    @classmethod
    def class_method(cls):
        """Class method."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            filepath = f.name

        try:
            data = parse_file(filepath)
            assert len(data.classes) == 1
            cls = data.classes[0]
            method_names = [m.name for m in cls.methods]
            assert "public_method" in method_names
            assert "static_method" in method_names
            assert "class_method" in method_names
            assert "_private_method" in method_names
            assert "__mangled_method" in method_names
            assert "__dunder_method__" in method_names
        finally:
            os.unlink(filepath)


class TestParseFolder:
    """Test parsing a folder with multiple Python files."""

    def test_parse_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first file
            with open(os.path.join(tmpdir, "module_a.py"), "w") as f:
                f.write('''
class ClassA:
    """Class A."""
    pass
''')

            # Create second file
            with open(os.path.join(tmpdir, "module_b.py"), "w") as f:
                f.write('''
class ClassB:
    """Class B."""
    pass

def top_level_func():
    """A top-level function."""
    pass
''')

            data = parse_folder(tmpdir)
            class_names = [c.name for c in data.classes]
            func_names = [f.name for f in data.functions]

            assert "ClassA" in class_names
            assert "ClassB" in class_names
            assert "top_level_func" in func_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
