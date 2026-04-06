"""Stage 1: Python Source Parser - extracts structured data from Python source files."""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArgData:
    """Represents a function argument."""
    name: str
    type: str | None
    default: str | None


@dataclass
class ParamDoc:
    """Represents a parameter from a docstring."""
    name: str
    type: str | None
    description: str
    is_optional: bool = False


@dataclass
class ReturnDoc:
    """Represents a return value from a docstring."""
    type: str | None
    description: str


@dataclass
class RaiseDoc:
    """Represents an exception from a docstring."""
    type: str
    description: str


@dataclass
class FunctionData:
    """Represents a parsed function."""
    name: str
    args: list[ArgData] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    short_description: str = ""
    full_description: str = ""
    parameters: list[ParamDoc] = field(default_factory=list)
    returns: ReturnDoc | None = None
    raises: list[RaiseDoc] = field(default_factory=list)
    examples: str = ""
    source_file: str = ""
    source_line: int = 0


@dataclass
class PropertyData:
    """Represents a property."""
    name: str
    type: str | None
    description: str


@dataclass
class ClassData:
    """Represents a parsed class."""
    name: str
    base_classes: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    short_description: str = ""
    full_description: str = ""
    properties: list[PropertyData] = field(default_factory=list)
    methods: list[FunctionData] = field(default_factory=list)
    source_file: str = ""
    source_line: int = 0
    # Classification flags
    is_enum: bool = False
    is_dataclass: bool = False
    is_interface: bool = False
    is_protocol: bool = False
    is_exception: bool = False


@dataclass
class ConstantData:
    """Represents a module-level constant."""
    name: str
    value: str
    type: str


@dataclass
class SourceData:
    """Container for all parsed source data from a module.

    ``classes``, ``functions``, ``constants`` — **all** items found recursively
    (used by presentation functions that need to look up any class/function).

    ``classes_flat``, ``functions_flat``, ``constants_flat`` — items from
    **direct** ``.py`` files in the folder only (no subfolders).  Used by
    ``{{classes}}``, ``{{functions}}``, ``{{constants}}`` data tags.
    """
    classes: list[ClassData] = field(default_factory=list)
    functions: list[FunctionData] = field(default_factory=list)
    constants: list[ConstantData] = field(default_factory=list)
    # Flat — only from direct .py files in the folder (not subfolders)
    classes_flat: list[ClassData] = field(default_factory=list)
    functions_flat: list[FunctionData] = field(default_factory=list)
    constants_flat: list[ConstantData] = field(default_factory=list)

    def _filter(self, attr: str, src: list[ClassData]) -> list[ClassData]:
        return [c for c in src if getattr(c, attr)]

    @staticmethod
    def _is_plain(c: ClassData) -> bool:
        return not (c.is_enum or c.is_dataclass or c.is_interface or c.is_protocol or c.is_exception)

    # Typed subsets — recursive
    @property
    def enums(self) -> list[ClassData]: return self._filter('is_enum', self.classes)
    @property
    def dataclasses(self) -> list[ClassData]: return self._filter('is_dataclass', self.classes)
    @property
    def interfaces(self) -> list[ClassData]: return self._filter('is_interface', self.classes)
    @property
    def protocols(self) -> list[ClassData]: return self._filter('is_protocol', self.classes)
    @property
    def exceptions(self) -> list[ClassData]: return self._filter('is_exception', self.classes)
    @property
    def plain_classes(self) -> list[ClassData]: return [c for c in self.classes if self._is_plain(c)]

    # Typed subsets — flat
    @property
    def enums_flat(self) -> list[ClassData]: return self._filter('is_enum', self.classes_flat)
    @property
    def dataclasses_flat(self) -> list[ClassData]: return self._filter('is_dataclass', self.classes_flat)
    @property
    def interfaces_flat(self) -> list[ClassData]: return self._filter('is_interface', self.classes_flat)
    @property
    def protocols_flat(self) -> list[ClassData]: return self._filter('is_protocol', self.classes_flat)
    @property
    def exceptions_flat(self) -> list[ClassData]: return self._filter('is_exception', self.classes_flat)
    @property
    def plain_classes_flat(self) -> list[ClassData]: return [c for c in self.classes_flat if self._is_plain(c)]


def parse_google_docstring(docstring: str) -> tuple[str, str, list[ParamDoc], ReturnDoc | None, list[RaiseDoc], str]:
    """Parse a Google-style docstring into structured components.

    Returns:
        (short_description, full_description, parameters, returns, raises, examples)
    """
    if not docstring:
        return "", "", [], None, [], ""

    lines = docstring.split('\n')
    short_desc = ""
    full_desc = ""
    parameters: list[ParamDoc] = []
    returns: ReturnDoc | None = None
    raises: list[RaiseDoc] = []
    examples = ""

    current_section = "short"
    section_content: list[str] = []
    current_param: ParamDoc | None = None

    for line in lines:
        stripped = line.strip()

        # Check for section headers
        if stripped.startswith("Args:") or stripped.startswith("Arguments:"):
            if short_desc == "" and full_desc == "" and section_content:
                full_desc = "\n".join(section_content).strip()
                section_content = []
            current_section = "args"
            continue
        elif stripped.startswith("Returns:"):
            if section_content and current_section == "args":
                _finish_current_param(section_content, parameters)
                section_content = []
            current_section = "returns"
            continue
        elif stripped.startswith("Raises:"):
            if section_content and current_section == "returns":
                # Process returns section before transitioning
                ret_text = " ".join(section_content)
                ret_type = None
                ret_desc = ret_text
                if "—" in ret_text:
                    parts = ret_text.split("—", 1)
                    ret_type = parts[0].strip()
                    ret_desc = parts[1].strip()
                elif "->" in ret_text:
                    parts = ret_text.split("->", 1)
                    ret_type = parts[0].strip()
                    ret_desc = parts[1].strip()
                returns = ReturnDoc(type=ret_type, description=ret_desc)
                section_content = []
            current_section = "raises"
            continue
        elif stripped.startswith("Examples:") or stripped.startswith("Example:"):
            if section_content and current_section == "returns":
                # Process returns section before transitioning
                ret_text = " ".join(section_content)
                ret_type = None
                ret_desc = ret_text
                if "—" in ret_text:
                    parts = ret_text.split("—", 1)
                    ret_type = parts[0].strip()
                    ret_desc = parts[1].strip()
                elif "->" in ret_text:
                    parts = ret_text.split("->", 1)
                    ret_type = parts[0].strip()
                    ret_desc = parts[1].strip()
                returns = ReturnDoc(type=ret_type, description=ret_desc)
                section_content = []
            current_section = "examples"
            continue
        elif stripped.startswith("=") and len(stripped) > 3 and current_section != "short":
            # Skip separator lines
            continue
        elif not stripped:
            # Empty line might separate sections
            if current_section == "args" and current_param:
                _finish_current_param(section_content, parameters)
                current_param = None
                section_content = []
            continue

        # Content lines
        if current_section == "short":
            if short_desc == "" and stripped:
                short_desc = stripped
                if len(lines) == 1:
                    full_desc = short_desc
            elif stripped:
                full_desc += ("\n" if full_desc else "") + stripped
        elif current_section == "args":
            # Parse arg lines like "    name: Type description" or "    name: description"
            content_line = line.lstrip()
            indent = len(line) - len(content_line)

            if content_line and not content_line.startswith(":") and indent > 0:
                # Could be a parameter line
                if ":" in content_line:
                    # Finish previous param if exists
                    if current_param:
                        _finish_current_param(section_content, parameters)

                    parts = content_line.split(":", 1)
                    arg_name = parts[0].strip()
                    rest = parts[1].strip() if len(parts) > 1 else ""

                    # Parse type from "Type, optional" or just "Type"
                    arg_type = None
                    desc = rest
                    is_optional = False

                    if "," in rest:
                        type_part, desc_part = rest.split(",", 1)
                        arg_type = type_part.strip()
                        desc = desc_part.strip()
                        is_optional = "optional" in desc_part.lower()
                    elif rest:
                        # No comma - the rest is description, not type
                        desc = rest
                        arg_type = None

                    current_param = ParamDoc(
                        name=arg_name,
                        type=arg_type if arg_type else None,
                        description=desc,
                        is_optional=is_optional
                    )
                    parameters.append(current_param)
                    section_content = []
                elif current_param:
                    # Continuation of previous param description
                    section_content.append(stripped)
            elif content_line.startswith(":") and current_param:
                # Docstring arg format like "    arg_name: Description"
                section_content.append(stripped)
        elif current_section == "returns":
            section_content.append(stripped)
        elif current_section == "raises":
            # Format: ExceptionType: description
            if ":" in stripped:
                exc_type, desc = stripped.split(":", 1)
                raises.append(RaiseDoc(type=exc_type.strip(), description=desc.strip()))
        elif current_section == "examples":
            examples += stripped + "\n"

    # Finish any remaining content
    if current_section == "args" and current_param:
        _finish_current_param(section_content, parameters)
    elif current_section == "returns" and section_content:
        ret_text = " ".join(section_content)
        # Try to parse return type
        ret_type = None
        ret_desc = ret_text
        if "—" in ret_text:
            parts = ret_text.split("—", 1)
            ret_type = parts[0].strip()
            ret_desc = parts[1].strip()
        elif "->" in ret_text:
            parts = ret_text.split("->", 1)
            ret_type = parts[0].strip()
            ret_desc = parts[1].strip()
        returns = ReturnDoc(type=ret_type, description=ret_desc)

    return short_desc, full_desc, parameters, returns, raises, examples.strip()


def _finish_current_param(section_content: list[str], parameters: list[ParamDoc]) -> None:
    """Helper to finish parsing a current parameter."""
    if section_content:
        param = parameters[-1] if parameters else None
        if param:
            param.description = (param.description + " " + " ".join(section_content)).strip()


def _get_decorator_name(d: ast.expr) -> str:
    """Extract decorator name from any AST node."""
    if isinstance(d, ast.Name):
        return d.id
    if isinstance(d, ast.Attribute):
        return d.attr
    if isinstance(d, ast.Call):
        return _get_decorator_name(d.func)
    try:
        return ast.unparse(d)
    except Exception:
        return "unknown"


def _get_class_decorators(node: ast.ClassDef) -> list[str]:
    """Extract class decorators."""
    return [_get_decorator_name(d) for d in node.decorator_list]


def _get_function_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract function decorators."""
    return [_get_decorator_name(d) for d in node.decorator_list]


def _parse_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ArgData]:
    """Parse function arguments from AST."""
    args_data = []
    a = node.args

    # Positional-only args (before /)
    num_posonlyargs = len(a.posonlyargs)
    posonly_defaults_offset = num_posonlyargs - len(a.defaults)
    for i, arg in enumerate(a.posonlyargs):
        arg_type = _get_annotation_name(arg.annotation) if arg.annotation else None
        default = None
        di = i - max(0, num_posonlyargs - len(a.defaults))
        if di >= 0 and di < len(a.defaults):
            default = _get_default_value(a.defaults[di])
        args_data.append(ArgData(name=arg.arg, type=arg_type, default=default))

    # Regular args
    num_args = len(a.args)
    num_defaults = len(a.defaults)
    # defaults are right-aligned: last N args get defaults
    # but posonlyargs may have consumed some defaults
    regular_defaults_start = max(0, num_defaults - num_args)
    first_default_arg_index = num_args - (num_defaults - max(0, num_posonlyargs - (num_posonlyargs - min(num_posonlyargs, max(0, num_defaults - num_args)))))
    # Simpler: defaults list covers posonlyargs + args combined
    total_positional = num_posonlyargs + num_args
    for i, arg in enumerate(a.args):
        arg_type = _get_annotation_name(arg.annotation) if arg.annotation else None
        default = None
        abs_index = num_posonlyargs + i
        default_index = abs_index - (total_positional - num_defaults)
        if default_index >= 0 and default_index < num_defaults:
            default = _get_default_value(a.defaults[default_index])
        args_data.append(ArgData(name=arg.arg, type=arg_type, default=default))

    # *args
    if a.vararg:
        arg_type = _get_annotation_name(a.vararg.annotation) if a.vararg.annotation else None
        args_data.append(ArgData(name=f"*{a.vararg.arg}", type=arg_type, default=None))

    # Keyword-only args (after *)
    for i, arg in enumerate(a.kwonlyargs):
        arg_type = _get_annotation_name(arg.annotation) if arg.annotation else None
        default = None
        if i < len(a.kw_defaults) and a.kw_defaults[i] is not None:
            default = _get_default_value(a.kw_defaults[i])
        args_data.append(ArgData(name=arg.arg, type=arg_type, default=default))

    # **kwargs
    if a.kwarg:
        arg_type = _get_annotation_name(a.kwarg.annotation) if a.kwarg.annotation else None
        args_data.append(ArgData(name=f"**{a.kwarg.arg}", type=arg_type, default=None))

    return args_data


def _get_annotation_name(annotation: ast.expr) -> str:
    """Get the name of a type annotation."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return f"{_get_annotation_name(annotation.value)}.{annotation.attr}"
    if isinstance(annotation, ast.Subscript):
        slice_str = _get_annotation_name(annotation.slice)
        return f"{_get_annotation_name(annotation.value)}[{slice_str}]"
    if isinstance(annotation, ast.Constant):
        return repr(annotation.value) if isinstance(annotation.value, str) else str(annotation.value)
    if isinstance(annotation, ast.Tuple):
        return ", ".join(_get_annotation_name(e) for e in annotation.elts)
    if isinstance(annotation, ast.List):
        return "[" + ", ".join(_get_annotation_name(e) for e in annotation.elts) + "]"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return f"{_get_annotation_name(annotation.left)} | {_get_annotation_name(annotation.right)}"
    if isinstance(annotation, ast.Call):
        func_name = _get_annotation_name(annotation.func)
        args = ", ".join(_get_annotation_name(a) for a in annotation.args)
        return f"{func_name}({args})" if args else func_name
    if isinstance(annotation, ast.Starred):
        return f"*{_get_annotation_name(annotation.value)}"
    try:
        return ast.unparse(annotation)
    except Exception:
        return "Unknown"


def _get_default_value(expr: ast.expr) -> str:
    """Get string representation of a default value expression."""
    if isinstance(expr, ast.Constant):
        return repr(expr.value)
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return f"{_get_default_value(expr.value)}.{expr.attr}"
    if isinstance(expr, ast.BinOp):
        return f"{_get_default_value(expr.left)} {_get_binop_symbol(expr.op)} {_get_default_value(expr.right)}"
    if isinstance(expr, ast.UnaryOp):
        return f"{_get_unaryop_symbol(expr.op)}{_get_default_value(expr.operand)}"
    if isinstance(expr, ast.Tuple):
        return "(" + ", ".join(_get_default_value(e) for e in expr.elts) + ")"
    if isinstance(expr, ast.List):
        return "[" + ", ".join(_get_default_value(e) for e in expr.elts) + "]"
    if isinstance(expr, ast.Dict):
        pairs = []
        for k, v in zip(expr.keys, expr.values):
            if k is not None:
                pairs.append(f"{_get_default_value(k)}: {_get_default_value(v)}")
            else:
                pairs.append(f"**{_get_default_value(v)}")
        return "{" + ", ".join(pairs) + "}"
    if isinstance(expr, ast.Set):
        return "{" + ", ".join(_get_default_value(e) for e in expr.elts) + "}"
    if isinstance(expr, ast.Call):
        func = _get_default_value(expr.func)
        args = ", ".join(_get_default_value(a) for a in expr.args)
        return f"{func}({args})"
    try:
        return ast.unparse(expr)
    except Exception:
        return "..."


def _infer_const_type(value: ast.expr) -> str:
    """Infer the type of a constant from its AST value node."""
    if isinstance(value, ast.Constant):
        return type(value.value).__name__
    if isinstance(value, ast.List):
        return "list"
    if isinstance(value, ast.Tuple):
        return "tuple"
    if isinstance(value, ast.Dict):
        return "dict"
    if isinstance(value, ast.Set):
        return "set"
    if isinstance(value, ast.Call):
        return _get_annotation_name(value.func)
    if isinstance(value, ast.Name):
        return value.id
    return "Unknown"


def _get_binop_symbol(op: ast.operator) -> str:
    ops = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}
    return ops.get(type(op), "?")


def _get_unaryop_symbol(op: ast.unaryop) -> str:
    ops = {ast.UAdd: "+", ast.USub: "-", ast.Not: "not "}
    return ops.get(type(op), "")


def _parse_function(node: ast.FunctionDef | ast.AsyncFunctionDef, source_file: str) -> FunctionData:
    """Parse a function definition into FunctionData."""
    short_desc, full_desc, params, returns, raises, examples = parse_google_docstring(ast.get_docstring(node))

    # If no docstring parsed, try type hints for return type
    return_type = None
    if node.returns:
        return_type = _get_annotation_name(node.returns)

    return FunctionData(
        name=node.name,
        args=_parse_args(node),
        return_type=return_type,
        decorators=_get_function_decorators(node),
        short_description=short_desc,
        full_description=full_desc,
        parameters=params,
        returns=returns,
        raises=raises,
        examples=examples,
        source_file=source_file,
        source_line=node.lineno
    )


def _parse_class(node: ast.ClassDef, source_file: str) -> ClassData:
    """Parse a class definition into ClassData."""
    short_desc, full_desc, _, _, _, _ = parse_google_docstring(ast.get_docstring(node))

    # Get base classes
    base_classes = []
    for base in node.bases:
        base_classes.append(_get_annotation_name(base))

    # Separate methods by type
    methods: list[FunctionData] = []
    properties: list[PropertyData] = []

    for item in node.body:
        if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
            func_data = _parse_function(item, source_file)
            # Check if it's a property
            if "property" in func_data.decorators:
                # Get return type from type hint
                prop_type = None
                if item.returns:
                    prop_type = _get_annotation_name(item.returns)
                properties.append(PropertyData(
                    name=item.name,
                    type=prop_type,
                    description=func_data.short_description
                ))
            else:
                methods.append(func_data)

    decorators = _get_class_decorators(node)
    bases_lower = {b.lower() for b in base_classes}

    ENUM_BASES = {'enum', 'intenum', 'strenum', 'flag', 'intflag'}
    ABC_BASES = {'abc', 'abcmeta'}
    EXCEPTION_BASES = {'exception', 'baseexception', 'oserror', 'ioerror',
                       'valueerror', 'typeerror', 'keyerror', 'runtimeerror'}
    PROTOCOL_BASES = {'protocol'}

    has_abstractmethod = any(
        isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(_get_decorator_name(d) == 'abstractmethod' for d in item.decorator_list)
        for item in node.body
    )

    return ClassData(
        name=node.name,
        base_classes=base_classes,
        decorators=decorators,
        short_description=short_desc,
        full_description=full_desc,
        properties=properties,
        methods=methods,
        source_file=source_file,
        source_line=node.lineno,
        is_enum=bool(bases_lower & ENUM_BASES),
        is_dataclass='dataclass' in decorators,
        is_interface=bool(bases_lower & ABC_BASES) or has_abstractmethod,
        is_protocol=bool(bases_lower & PROTOCOL_BASES),
        is_exception=bool(bases_lower & EXCEPTION_BASES) or node.name.endswith(('Error', 'Exception')),
    )


def parse_file(filepath: str) -> SourceData:
    """Parse a Python file and return SourceData.

    Args:
        filepath: Path to the Python file to parse.

    Returns:
        SourceData containing all classes, functions, and constants.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=filepath)

    classes: list[ClassData] = []
    functions: list[FunctionData] = []
    constants: list[ConstantData] = []

    # Get module-level constants (ALL_CAPS variables)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    value_str = _get_default_value(node.value)
                    const_type = _infer_const_type(node.value)
                    constants.append(ConstantData(
                        name=target.id,
                        value=value_str,
                        type=const_type
                    ))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id.isupper() and node.value:
                value_str = _get_default_value(node.value)
                const_type = _get_annotation_name(node.annotation)
                constants.append(ConstantData(
                    name=node.target.id,
                    value=value_str,
                    type=const_type
                ))

    # Get classes and top-level functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            # Skip private classes (single underscore), keep dunder and public
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue
            classes.append(_parse_class(node, filepath))

    # Filter to only top-level functions
    top_level_functions = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__")):
                top_level_functions.append(_parse_function(node, filepath))

    return SourceData(
        classes=classes,
        functions=top_level_functions,
        constants=constants,
        classes_flat=classes,
        functions_flat=top_level_functions,
        constants_flat=constants,
    )


def parse_folder(folder_path: str) -> SourceData:
    """Parse all Python files in a folder and merge SourceData.

    Two sets of results are produced:

    * **flat** (``classes_flat`` etc.) — only ``.py`` files directly inside
      *folder_path* (no subfolders).  ``{{classes}}`` expands from this.
    * **recursive** (``classes`` etc.) — all ``.py`` files in *folder_path*
      and every subfolder.  ``{{classes_rec}}`` and presentation functions
      use this.

    Args:
        folder_path: Path to the folder containing Python files.

    Returns:
        Merged SourceData with both flat and recursive lists.
    """
    all_classes: list[ClassData] = []
    all_functions: list[FunctionData] = []
    all_constants: list[ConstantData] = []
    flat_classes: list[ClassData] = []
    flat_functions: list[FunctionData] = []
    flat_constants: list[ConstantData] = []

    norm_root = os.path.normpath(folder_path)

    for root, _, files in os.walk(folder_path):
        is_direct = os.path.normpath(root) == norm_root
        for filename in sorted(files):
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                try:
                    data = parse_file(filepath)
                    all_classes.extend(data.classes)
                    all_functions.extend(data.functions)
                    all_constants.extend(data.constants)
                    if is_direct:
                        flat_classes.extend(data.classes)
                        flat_functions.extend(data.functions)
                        flat_constants.extend(data.constants)
                except Exception as e:
                    import warnings
                    warnings.warn(f"Could not parse {filepath}: {e}")

    return SourceData(
        classes=all_classes,
        functions=all_functions,
        constants=all_constants,
        classes_flat=flat_classes,
        functions_flat=flat_functions,
        constants_flat=flat_constants,
    )
