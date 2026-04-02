# PyDocGen — Technical Specification

## 1. Overview

PyDocGen is a static documentation generator for Python projects. It produces a set of HTML pages with a 3-column layout (navigation tree, content, page contents/anchors). Documentation structure is defined explicitly via a tree config, with localized auto-generation from Python source code via templates.

### Core Principles

- **Everything is a template.** Every page (module overview, class page, manual page, introduction) is a `.dtmpl` template file. There are no special page types.
- **Nodes are the only abstraction.** A node = title + template + source folder (optional) + params. The navigation tree is a tree of nodes.
- **Templates are universal.** Any template can access any data from its source folder. A "class template" and "module template" differ only in content, not in mechanism.
- **Hard errors.** Any invalid reference (unknown class, missing param, broken cross-link) stops the build immediately with a clear error message.

### File Extensions

| Extension | Purpose |
|-----------|---------|
| `.dtmpl`  | Template file (Markdown + HTML + tags) |
| `.dcfg`   | Config file (YAML with macro preprocessing) |

---

## 2. Project Structure

```
project/
  .sdoc.tree                 # main config
  docs/
    templates/
      default_module.dtmpl
      default_class.dtmpl
      default_function.dtmpl
      pipeline_custom.dtmpl
      introduction.dtmpl
      installation.dtmpl
      migration.dtmpl
    assets/                        # copied as-is to build
      pipeline_flow.svg
      style_overrides.css
  src/
    dataflow/
      .sdoc                   # folder doc config
      __init__.py
      pipeline.py
      nodes.py
      transforms/
        .sdoc
        base.py
  build/docs/                      # output directory
```

---

## 3. Main Config — `.sdoc.tree`

```yaml
project_name: "MyProject"
version: "1.0.0"
output_dir: "build/docs/"
templates_dir: "docs/templates/"
assets_dir: "docs/assets/"
docstring_style: "google"

tree:
  - title: "Introduction"
    template: "introduction"

  - title: "Getting Started"
    children:
      - title: "Installation"
        template: "installation"
      - title: "First Pipeline"
        template: "first_pipeline"

  - title: "Overviews"
    children:
      - title: "Architecture"
        template: "architecture"

  - title: "API Reference"
    auto_source: "src/"
```

### Fields

- `project_name` — displayed in header and title tags.
- `version` — displayed in header.
- `output_dir` — where the build output goes.
- `templates_dir` — where `.dtmpl` files are searched.
- `assets_dir` — copied as-is into `output_dir/assets/`.
- `docstring_style` — only `"google"` supported initially.
- `tree` — the navigation tree. Each item is a node.

### Tree Node (in main config)

```yaml
- title: "Page Title"          # displayed in nav tree
  template: "template_name"    # references templates_dir/template_name.dtmpl
  params:                      # optional, passed to template
    SOME_KEY: "some_value"
  children:                    # optional, sub-nodes
    - title: "Child"
      template: "child_tmpl"
```

- `auto_source: "src/"` — special directive. The builder scans this directory recursively for `.sdoc` files and attaches found sub-trees to this node.

### Nodes Without `source`

Manual pages (Introduction, Installation, etc.) have no `source` folder. Their templates can contain plain Markdown/HTML and `[[cross-links]]`, but NOT data tags like `{{classes}}` or `{{class_name#X}}`. Using a data tag in a sourceless template is a **hard error**.

---

## 4. Folder Config — `.sdoc`

Each Python source folder that should appear in documentation must contain a `.sdoc` file. Folders without it are ignored (not inherited, not defaulted).

```yaml
branch: "API Reference"
title: "DataFlow"
template: "default_module"
source: "."
params:
  MODULE_DESCRIPTION: "High-level data processing framework"
  CUSTOM_WARNING: "This module is experimental."

children:
  %%__CLASSES__.exclude(InternalHelper)%%
  - title: "%%__CLASS__%% Class"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%

  - title: "Migration Guide"
    template: "migration"
    params:
      MODULE_DESCRIPTION: "How to migrate from v1 to v2"

  - dir: "transforms/"
```

### Fields

- `branch` — path in the main tree where this folder attaches. Uses `">"` separator for nested paths: `"API Reference > Core"`.
- `title` — display name of this node in the nav tree.
- `template` — which `.dtmpl` to use for this node's page.
- `source` — path to Python source folder, relative to this `.sdoc` location. `"."` means same folder.
- `params` — key-value pairs passed to the template. All values are strings.
- `children` — ordered list of child nodes. Can contain:
  - Regular child nodes (`title` + `template` + optional `params`)
  - `%%__CLASSES__%%` macro blocks (see Section 5)
  - `- dir: "subfolder/"` — recursion into subfolder's `.sdoc`

### `source` Inheritance

All children of a node inherit the parent's `source` unless they specify their own. A `- dir:` child gets its source from its own `.sdoc`.

---

## 5. DCFG Macro Preprocessing

Before YAML parsing, `.dcfg` files go through a text preprocessor that expands macro blocks.

### `%%__CLASSES__%%` Block

```yaml
%%__CLASSES__%%
- title: "%%__CLASS__%% Class"
  template: "default_class"
  params:
    CLASS_ID: "%%__CLASS__%%"
%%__CLASSES__%%
```

The preprocessor:

1. Scans the `source` folder's Python files via AST.
2. Collects all class names: `[Pipeline, SourceNode, SinkNode, InternalHelper]`.
3. Applies `.exclude(...)` if present: `%%__CLASSES__.exclude(InternalHelper)%%` → `[Pipeline, SourceNode, SinkNode]`.
4. For each class, clones the inner YAML block, replacing `%%__CLASS__%%` with the class name.

Result after preprocessing:

```yaml
- title: "Pipeline Class"
  template: "default_class"
  params:
    CLASS_ID: "Pipeline"
- title: "SourceNode Class"
  template: "default_class"
  params:
    CLASS_ID: "SourceNode"
- title: "SinkNode Class"
  template: "default_class"
  params:
    CLASS_ID: "SinkNode"
```

### `%%__FUNCTIONS__%%` Block

Same mechanics, but iterates over top-level functions (not inside classes).

```yaml
%%__FUNCTIONS__%%
- title: "%%__FUNCTION__%%()"
  template: "default_function"
  params:
    FUNC_ID: "%%__FUNCTION__%%"
%%__FUNCTIONS__%%
```

### `.exclude()` Syntax

```
%%__CLASSES__.exclude(Name1, Name2)%%
%%__FUNCTIONS__.exclude(helper_func)%%
```

Comma-separated list of names to exclude. No quotes, no spaces after commas.

### Rules

- Macro blocks must be at the top level of `children:` list.
- `%%__CLASS__%%` / `%%__FUNCTION__%%` can appear anywhere inside the block — in `title`, `template`, `params` values.
- Macros are expanded before YAML parsing, so the result must be valid YAML.
- If `source` folder has 0 classes/functions, the block produces 0 items (no error).
- Unknown macro names (not `__CLASSES__` or `__FUNCTIONS__`) → hard error.

---

## 6. Template Format — `.dtmpl`

A `.dtmpl` file consists of two parts: parameter declarations (optional) and body.

### Parameter Block

```
param@CLASS_ID
param@SHOW_PRIVATE=false
param@MODULE_DESCRIPTION=No description provided

# {{class_name#%%CLASS_ID%%}}
...body...
```

Lines at the top of the file matching `param@NAME` or `param@NAME=default` are parameter declarations. The parameter block ends at the first line that is NOT a `param@` declaration (including blank lines).

- `param@NAME` — required parameter. If not provided in `params` of the node's config, **hard error**.
- `param@NAME=default` — optional parameter with default value.

### Body

Everything after the parameter block is the template body. It is a mix of:

- **Plain text / Markdown** — rendered via Markdown→HTML conversion.
- **Raw HTML** — passed through unchanged.
- **`%%PARAM%%` substitutions** — replaced with parameter values.
- **`{{data_tags}}`** — replaced with rendered data from Python source.
- **`:: for` loops** — iterate over collections.
- **`[[cross-links]]`** — replaced with `<a href>` links.

---

## 7. Template Processing Pipeline

For each node, the template is processed in this exact order:

### Step 1: Parameter Resolution

Parse `param@` declarations. Merge with `params` from config. Validate all required params are present (hard error if not).

### Step 2: `%%PARAM%%` Substitution

Pure text replacement. Every `%%NAME%%` in the body is replaced with the parameter value. If `%%NAME%%` is found but NAME is not declared — **hard error**.

After this step, all `%%...%%` are gone. What remains is Markdown/HTML with `{{tags}}`, `:: for` blocks, and `[[links]]`.

### Step 3: `:: for` Loop Expansion

Find and expand all `:: for` blocks:

```
:: for X in {{classes}}.exclude("Custom"):
## {{class_name#X}}
{{class_short_description#X}}
:: endfor
```

Processing:
1. Evaluate the collection expression (`{{classes}}` returns list of class names from source).
2. Apply `.exclude("Name1","Name2")` if present.
3. For each item in collection, clone the body and replace `#X` with `#ActualName`.
4. Concatenate all cloned bodies.

Nested `:: for` loops are NOT supported in v1.

After this step, all `:: for` blocks are gone. What remains is Markdown/HTML with concrete `{{tag#ClassName}}` tags and `[[links]]`.

### Step 4: `{{data_tag}}` Rendering

Replace each `{{tag}}` or `{{tag#target}}` with rendered HTML content. See Section 8 for all available tags.

- If `target` refers to a non-existent class/function — **hard error**.
- If a data tag is used in a template whose node has no `source` — **hard error**.

### Step 5: Markdown → HTML

Convert the result from Markdown to HTML. Existing HTML tags are preserved. Use Python `markdown` library with `extra` extension (supports fenced code blocks, tables, etc.).

### Step 6: Cross-Link Resolution

Replace `[[Target]]` patterns with `<a href="...">` links:

- `[[ClassName]]` → link to the class page node.
- `[[ClassName.method_name]]` → link to the class page node with `#method_name` anchor.
- `[[function_name]]` → link to the function page node.
- `[[module_name.ClassName]]` → fully qualified, for disambiguation.
- `[[Target|custom text]]` → `<a href="...">custom text</a>`.

Resolution uses a global index built from all nodes. If target not found — **hard error**.

Cross-links work in: template bodies, docstrings (rendered within `{{data_tags}}`), and parameter values.

### Step 7: Layout Wrapping

Insert the rendered HTML into the base 3-column layout:

- **Left panel**: navigation tree (generated from the full node tree, current node highlighted).
- **Center**: the rendered page content.
- **Right panel**: "Contents" sidebar — list of `<h2>` and `<h3>` anchors from the page.
- **Top**: breadcrumb path (e.g., `MyProject > API Reference > DataFlow > Pipeline`) and search input.

---

## 8. Data Tags Reference

All data tags read from the `SourceData` of the node's `source` folder.

### Module-Level Tags (no `#target`)

| Tag | Output |
|-----|--------|
| `{{classes}}` | HTML table: class name (as link) + short description, for each class in source folder (not recursive) |
| `{{classes_all}}` | Same but recursive into subfolders |
| `{{functions}}` | HTML table: function signature + short description, for top-level functions |
| `{{functions_all}}` | Same but recursive |
| `{{constants}}` | HTML table: constant name + value + type, for `ALL_CAPS` module-level variables |
| `{{submodules}}` | HTML table: subfolder name + description (from their `.sdoc`) |

### Class-Level Tags (`#ClassName` required)

| Tag | Output |
|-----|--------|
| `{{class_name#X}}` | Class name as string |
| `{{class_short_description#X}}` | First line of class docstring |
| `{{class_full_description#X}}` | Full class docstring (rendered as Markdown) |
| `{{class_info#X}}` | Info table: module, file, base classes, known subclasses |
| `{{properties#X}}` | Table of `@property` methods: name, type, description |
| `{{public_methods#X}}` | Table of public methods (no `_` prefix): signature + short description. Then detailed block for each method with full description, parameters, returns. |
| `{{private_methods#X}}` | Same for `_`-prefixed methods (not `__dunder__`) |
| `{{static_methods#X}}` | Same for `@staticmethod` methods |
| `{{class_methods#X}}` | Same for `@classmethod` methods |
| `{{all_methods#X}}` | All methods combined |
| `{{dunder_methods#X}}` | `__init__`, `__repr__`, `__str__`, etc. |
| `{{methods_filtered#X: name1, name2, name3}}` | Only specified methods, in specified order |
| `{{public_methods_except#X: name1, name2}}` | Public methods excluding specified |
| `{{decorators#X}}` | List of class decorators |
| `{{base_classes#X}}` | Comma-separated base classes (as cross-links if available) |
| `{{source_link#X}}` | Relative path to source file with line number: `src/dataflow/pipeline.py:15` |

### Function-Level Tags (`#function_name` required)

| Tag | Output |
|-----|--------|
| `{{function_name#X}}` | Function name |
| `{{signature#X}}` | Full signature with types |
| `{{description#X}}` | Full docstring (rendered as Markdown) |
| `{{short_description#X}}` | First line of docstring |
| `{{parameters#X}}` | Table: param name, type, default, description |
| `{{returns#X}}` | Return type and description |
| `{{decorators#X}}` | List of decorators |
| `{{source_link#X}}` | Relative path to source file with line number |

### Method Tags (inside `{{public_methods#X}}` etc.)

Methods are rendered inline on the class page. Each method entry includes:

- Signature line with anchor `id="method_name"`
- Parameters table (parsed from Google-style docstring)
- Returns description
- Full description

The exact HTML structure of method rendering is hardcoded in the engine (not a separate template).

---

## 9. Python Source Parsing

### What is Parsed

The engine uses Python's `ast` module to parse `.py` files. It extracts:

**Classes:**
- Name, base classes, decorators
- Docstring (class-level)
- Methods (name, args with type hints, decorators, docstring)
- Properties (`@property` decorated methods)
- Class variables with type annotations

**Functions (top-level):**
- Name, arguments with type hints, return type hint
- Decorators
- Docstring

**Constants:**
- Module-level variables matching `ALL_CAPS` pattern (e.g., `MAX_RETRIES = 5`)
- Type is inferred from the value

### Docstring Parsing (Google Style)

```python
def run(self, timeout: int = 30, verbose: bool = False) -> bool:
    """Runs the pipeline with the given configuration.

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
        True
    """
```

Parsed into:
- `short_description`: "Runs the pipeline with the given configuration."
- `full_description`: Everything before `Args:` section.
- `parameters`: List of (name, type, default, description). Types come from type hints first, then docstring.
- `returns`: (type, description)
- `raises`: List of (exception_type, description)
- `examples`: Raw code block

### Public/Private Distinction

- `method_name` — public
- `_method_name` — private (shown with `{{private_methods}}`)
- `__method_name` — private (shown with `{{private_methods}}`)
- `__dunder__` — dunder (shown with `{{dunder_methods}}`)
- `_ClassName` — class is completely skipped (not in `{{classes}}`, not processable)

### `__init__.py` Handling

- `__init__.py` is parsed like any other file.
- If it contains classes/functions, they belong to the module's `SourceData`.
- Re-exports (`from .pipeline import Pipeline`) are **not** followed. Classes belong to the file where they are physically defined.

---

## 10. Cross-Link Resolution

### Global Index

During the tree-building step, a global index is built:

```
{
  "Pipeline": "/api-reference/dataflow/pipeline-class.html",
  "Pipeline.run": "/api-reference/dataflow/pipeline-class.html#run",
  "SourceNode": "/api-reference/dataflow/sourcenode-class.html",
  "dataflow.Pipeline": "/api-reference/dataflow/pipeline-class.html",
  "run_all": "/api-reference/dataflow/functions.html#run_all",
  ...
}
```

Index is built from all nodes that have a `source` and render classes/functions.

### Resolution Rules

1. `[[Pipeline]]` → look up "Pipeline" in index.
2. `[[Pipeline.run]]` → look up "Pipeline.run" in index.
3. `[[dataflow.Pipeline]]` → fully qualified lookup.
4. If ambiguous (two classes named `Config` in different modules) — **hard error** with message suggesting fully qualified name.
5. `[[Target|display text]]` → uses resolved URL but displays custom text.

### Where Cross-Links Work

- Template bodies (after `%%PARAM%%` substitution and `:: for` expansion)
- Inside docstrings (processed when `{{data_tags}}` are rendered)
- NOT in `.sdoc` files
- NOT in `param@` declarations

---

## 11. HTML Output & Layout

### Base Layout

Every page shares the same HTML shell:

```html
<!DOCTYPE html>
<html>
<head>
  <title>{page_title} — {project_name}</title>
  <link rel="stylesheet" href="assets/style.css">
  <script src="assets/search.js"></script>
</head>
<body>
  <header>
    <div class="breadcrumb">MyProject > API Reference > DataFlow > Pipeline</div>
    <div class="search"><input type="text" placeholder="Search..." id="search-input"></div>
  </header>
  <div class="layout">
    <nav class="sidebar-left">
      <!-- Navigation tree -->
    </nav>
    <main class="content">
      <!-- Rendered page content -->
    </main>
    <aside class="sidebar-right">
      <!-- Contents: h2/h3 anchors -->
    </aside>
  </div>
</body>
</html>
```

### Navigation Tree (Left Panel)

- Rendered from the full node tree.
- Text-only, collapsible branches.
- Current page node is highlighted.
- Parent nodes of current page are expanded.
- Clicking a node navigates to its page.
- Clicking an expandable node also toggles its children.

### Contents Panel (Right)

- Auto-generated from `<h2>` and `<h3>` in the rendered page.
- Each entry is a clickable anchor link.
- Highlights current section on scroll.

### Breadcrumb

- Built from the path in the node tree: root → ... → parent → current.
- Each segment is a clickable link to that node's page.

### Search

- Client-side search using a generated JSON index.
- Index contains: node titles, class names, function names, method names, short descriptions.
- Simple substring matching. Results shown in a dropdown.

### Styling

- Single `style.css` file, plain CSS, no framework.
- Qt-docs-inspired 3-column layout.
- User can override by placing `style_overrides.css` in assets.
- No theme system. No dark mode (can be added later).

---

## 12. CLI Interface

```bash
python -m pydocgen build [--config .sdoc.tree]
```

- `--config` — path to main config. Default: `.sdoc.tree` in current directory.
- Exit code 0 on success, 1 on any error.
- Errors printed to stderr with file path and line number where possible.
- Warnings (e.g., empty sections) printed to stderr but don't stop the build.
- On success, prints: `Built {N} pages to {output_dir}`.
- Always does full rebuild (no incremental).

---

## 13. Complete Example

### Source Code

`src/dataflow/pipeline.py`:
```python
MAX_NODES = 100

class Pipeline:
    """A data processing pipeline that chains nodes together.

    Pipeline manages the lifecycle of data processing nodes,
    executing them in sequence and handling errors.
    """

    def __init__(self, name: str = "default"):
        """Initialize the pipeline.

        Args:
            name: Pipeline identifier.
        """
        self.name = name
        self._nodes = []

    @property
    def node_count(self) -> int:
        """Number of registered nodes."""
        return len(self._nodes)

    def add_node(self, node: "BaseNode") -> None:
        """Add a processing node to the pipeline.

        Args:
            node: The node to add.

        Raises:
            ValueError: If max nodes exceeded.
        """
        if len(self._nodes) >= MAX_NODES:
            raise ValueError("Max nodes exceeded")
        self._nodes.append(node)

    def run(self, timeout: int = 30) -> bool:
        """Execute the pipeline.

        Args:
            timeout: Max seconds to wait.

        Returns:
            True if all nodes completed.
        """
        ...

    def _validate(self) -> None:
        """Internal validation."""
        ...


class BaseNode:
    """Abstract base class for pipeline nodes."""

    def process(self, data: dict) -> dict:
        """Process incoming data.

        Args:
            data: Input data dictionary.

        Returns:
            Processed data dictionary.
        """
        ...
```

### Config

`src/dataflow/.sdoc`:
```yaml
branch: "API Reference"
title: "DataFlow"
template: "default_module"
source: "."
params:
  MODULE_DESCRIPTION: "High-level data processing framework for building node-based pipelines."

children:
  %%__CLASSES__%%
  - title: "%%__CLASS__%%"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%
```

### Templates

`docs/templates/default_module.dtmpl`:
```
param@MODULE_DESCRIPTION=No description

# Module Overview
%%MODULE_DESCRIPTION%%

## Classes

:: for X in {{classes}}:
### [[{{class_name#X}}]]
{{class_short_description#X}}
:: endfor

## Functions
{{functions}}

## Constants
{{constants}}
```

`docs/templates/default_class.dtmpl`:
```
param@CLASS_ID

# {{class_name#%%CLASS_ID%%}}
{{class_short_description#%%CLASS_ID%%}}

## Info
{{class_info#%%CLASS_ID%%}}

## Properties
{{properties#%%CLASS_ID%%}}

## Public Methods
{{public_methods#%%CLASS_ID%%}}

## Private Methods
{{private_methods#%%CLASS_ID%%}}

## Detailed Description
{{class_full_description#%%CLASS_ID%%}}
```

### Expected Output

Clicking "DataFlow" in nav tree shows:

```
Module Overview
High-level data processing framework for building node-based pipelines.

Classes
  Pipeline    A data processing pipeline that chains nodes together.
  BaseNode    Abstract base class for pipeline nodes.

Functions
  (none)

Constants
  MAX_NODES   100   int
```

Clicking "Pipeline" in nav tree shows:

```
Pipeline
A data processing pipeline that chains nodes together.

Info
  Module:      DataFlow
  File:        src/dataflow/pipeline.py:5
  Inherits:    (none)

Properties
  node_count   int   Number of registered nodes.

Public Methods
  __init__(name: str = "default")
    Initialize the pipeline.
    Parameters:
      name (str) — Pipeline identifier. Default: "default"

  add_node(node: BaseNode) -> None
    Add a processing node to the pipeline.
    Parameters:
      node (BaseNode) — The node to add.
    Raises:
      ValueError — If max nodes exceeded.

  run(timeout: int = 30) -> bool
    Execute the pipeline.
    Parameters:
      timeout (int) — Max seconds to wait. Default: 30
    Returns:
      bool — True if all nodes completed.

Private Methods
  _validate() -> None
    Internal validation.

Detailed Description
  Pipeline manages the lifecycle of data processing nodes,
  executing them in sequence and handling errors.
```

---

## 14. Implementation Stages

The system is built in stages. Each stage is a standalone module that can be tested independently. Each stage has a defined input, output, and set of tests.

---

### Stage 1: Python Source Parser

**Module:** `pydocgen/parser.py`

**Input:** Path to a `.py` file.

**Output:** `SourceData` object containing:
```python
@dataclass
class FunctionData:
    name: str
    args: list[ArgData]         # name, type, default
    return_type: str | None
    decorators: list[str]
    short_description: str
    full_description: str
    parameters: list[ParamDoc]  # from docstring
    returns: ReturnDoc | None
    raises: list[RaiseDoc]
    examples: str
    source_file: str
    source_line: int

@dataclass
class PropertyData:
    name: str
    type: str | None
    description: str

@dataclass
class ClassData:
    name: str
    base_classes: list[str]
    decorators: list[str]
    short_description: str
    full_description: str
    properties: list[PropertyData]
    methods: list[FunctionData]   # includes all methods
    source_file: str
    source_line: int

@dataclass
class ConstantData:
    name: str
    value: str
    type: str

@dataclass
class SourceData:
    classes: list[ClassData]
    functions: list[FunctionData]
    constants: list[ConstantData]
```

**Functionality:**
- Parse Python file using `ast` module.
- Extract classes with all methods, properties, decorators, base classes.
- Extract top-level functions.
- Extract `ALL_CAPS` module-level constants.
- Parse Google-style docstrings into structured data.
- Type hints from code take priority; docstring types used as fallback.
- Skip classes starting with `_`.

**Tests:**
```
test_parse_simple_class
    Input: .py file with one class, two methods, one property
    Assert: ClassData has correct name, 2 methods, 1 property

test_parse_google_docstring
    Input: function with full Google-style docstring (Args, Returns, Raises, Examples)
    Assert: all sections parsed correctly

test_parse_type_hints_priority
    Input: function with type hint `int` and docstring type `number`
    Assert: type is `int` (code wins)

test_parse_constants
    Input: file with MAX_SIZE = 100 and regular_var = "hello"
    Assert: only MAX_SIZE in constants list

test_skip_private_classes
    Input: file with class _Internal and class Public
    Assert: only Public in classes list

test_parse_decorators
    Input: class with @dataclass, method with @staticmethod
    Assert: decorators lists correct

test_parse_base_classes
    Input: class Foo(Bar, Baz)
    Assert: base_classes = ["Bar", "Baz"]

test_parse_empty_file
    Input: empty .py file
    Assert: SourceData with empty lists

test_parse_property
    Input: class with @property def name(self) -> str
    Assert: property with type "str"

test_parse_method_categories
    Input: class with public, _private, __private, __dunder__, @staticmethod, @classmethod
    Assert: each method has correct decorators/naming for categorization

test_parse_folder
    Input: folder with two .py files
    Assert: SourceData merges classes/functions from all files
```

---

### Stage 2: DCFG Preprocessor

**Module:** `pydocgen/dcfg_preprocessor.py`

**Input:** Raw text of a `.dcfg` file + list of class names + list of function names.

**Output:** Valid YAML string with all `%%...%%` macros expanded.

**Functionality:**
- Find `%%__CLASSES__%%...%%__CLASSES__%%` blocks.
- Find `%%__FUNCTIONS__%%...%%__FUNCTIONS__%%` blocks.
- Apply `.exclude(Name1,Name2)` filters.
- Clone inner block for each class/function, replacing `%%__CLASS__%%` / `%%__FUNCTION__%%`.
- Result is valid YAML.

**Tests:**
```
test_expand_classes_basic
    Input: DCFG with %%__CLASSES__%% block, classes=["A","B"]
    Assert: two children with titles "A Class", "B Class"

test_expand_classes_exclude
    Input: %%__CLASSES__.exclude(B)%%, classes=["A","B","C"]
    Assert: only A and C expanded

test_expand_functions
    Input: %%__FUNCTIONS__%% block, functions=["foo","bar"]
    Assert: two children for foo and bar

test_expand_no_classes
    Input: %%__CLASSES__%% block, classes=[]
    Assert: empty result (no error)

test_mixed_content
    Input: DCFG with manual child, then %%__CLASSES__%% block, then another manual child
    Assert: order preserved — manual, expanded, manual

test_no_macros
    Input: DCFG with no %% blocks
    Assert: output identical to input

test_invalid_macro_name
    Input: %%__INVALID__%% block
    Assert: hard error raised

test_valid_yaml_output
    Input: any DCFG with macros
    Assert: output parses as valid YAML
```

---

### Stage 3: Template Engine

**Module:** `pydocgen/template_engine.py`

**Input:** `.dtmpl` file content + `params` dict + `SourceData` (can be None).

**Output:** Rendered string (Markdown + HTML mix, with `[[links]]` still unresolved).

**Functionality:**
- Parse `param@` block.
- Validate required params present.
- `%%PARAM%%` text substitution.
- `:: for X in {{collection}}.exclude("..."):` loop expansion.
- `{{data_tag}}` and `{{data_tag#target}}` rendering.

**Tests:**
```
test_param_substitution
    Input: template with param@NAME, params={"NAME": "World"}, body "Hello %%NAME%%"
    Assert: "Hello World"

test_param_required_missing
    Input: template with param@NAME, params={}
    Assert: hard error

test_param_default
    Input: template with param@NAME=Default, params={}
    Assert: "Default" used

test_for_loop_basic
    Input: :: for X in {{classes}}: / # {{class_name#X}} / :: endfor
    SourceData with classes [A, B]
    Assert: "# A\n# B"

test_for_loop_exclude
    Input: :: for X in {{classes}}.exclude("B"): ...
    SourceData with classes [A, B, C]
    Assert: only A and C rendered

test_data_tag_class_name
    Input: {{class_name#Pipeline}}
    SourceData with class Pipeline
    Assert: "Pipeline"

test_data_tag_unknown_class
    Input: {{class_name#NonExistent}}
    Assert: hard error

test_data_tag_no_source
    Input: {{classes}} with source=None
    Assert: hard error

test_data_tag_public_methods
    Input: {{public_methods#MyClass}}
    SourceData with MyClass having 2 public methods
    Assert: rendered HTML table with both methods

test_methods_filtered
    Input: {{methods_filtered#MyClass: run, stop}}
    MyClass has methods [run, stop, pause]
    Assert: only run and stop rendered, in that order

test_public_methods_except
    Input: {{public_methods_except#MyClass: run}}
    MyClass has public methods [run, stop, pause]
    Assert: stop and pause rendered, not run

test_full_pipeline
    Input: template with params, for-loop, data tags, mixed Markdown+HTML
    Assert: correct combined output

test_constants_tag
    Input: {{constants}}
    SourceData with 2 constants
    Assert: rendered table with names, values, types

test_class_info_tag
    Input: {{class_info#Pipeline}}
    Assert: table with module name, file path, base classes
```

---

### Stage 4: Tree Builder

**Module:** `pydocgen/tree_builder.py`

**Input:** Main `.sdoc.tree` + all `.sdoc` files from `auto_source` directories.

**Output:** Tree of `Node` objects:
```python
@dataclass
class Node:
    title: str
    template: str
    params: dict[str, str]
    source: str | None         # absolute path to source folder
    children: list[Node]
    output_path: str           # relative path for output HTML file
```

**Functionality:**
- Parse main config.
- Build manual tree nodes from `tree:` section.
- Walk `auto_source` directories, find `.sdoc` files.
- For each `.sdoc`: run preprocessor (Stage 2), parse YAML, build sub-tree.
- Attach sub-trees to correct branches via `branch:` field.
- Assign `output_path` to each node (slugified title, nested by tree path).

**Tests:**
```
test_manual_tree
    Input: config with 3 manual nodes, no auto_source
    Assert: tree has 3 nodes with correct titles and templates

test_auto_source_single_folder
    Input: auto_source pointing to folder with .sdoc
    Assert: folder attached as child of auto_source node

test_auto_source_nested
    Input: auto_source with folder containing subfolder (both have .sdoc)
    Assert: nested tree structure

test_branch_attachment
    Input: .sdoc with branch: "API Reference", main tree has "API Reference" node
    Assert: folder node is child of "API Reference"

test_branch_not_found
    Input: .sdoc with branch: "NonExistent"
    Assert: hard error

test_folder_without_dcfg_ignored
    Input: auto_source with two folders, only one has .sdoc
    Assert: only one folder in tree

test_output_paths
    Input: tree with nested nodes
    Assert: output_path like "api-reference/dataflow/pipeline-class.html"

test_source_inheritance
    Input: parent node with source, child without explicit source
    Assert: child inherits parent's source

test_dir_reference
    Input: .sdoc with children containing - dir: "subfolder/"
    Assert: subfolder's .sdoc parsed and attached
```

---

### Stage 5: Cross-Link Index & Resolver

**Module:** `pydocgen/cross_links.py`

**Input:** Full node tree + all `SourceData` objects.

**Output:** Global index (dict: target_name → URL), and a function `resolve(text) → text_with_links`.

**Functionality:**
- Build index from all nodes: class names, function names, method names → node URLs + anchors.
- Detect ambiguities (same short name in different modules).
- `resolve()` replaces `[[Target]]` patterns with `<a href>` tags.

**Tests:**
```
test_resolve_class_link
    Input: "See [[Pipeline]]", index has Pipeline
    Assert: <a href="...">Pipeline</a>

test_resolve_method_link
    Input: "Call [[Pipeline.run]]"
    Assert: <a href="...#run">Pipeline.run</a>

test_resolve_custom_text
    Input: "[[Pipeline|the main class]]"
    Assert: <a href="...">the main class</a>

test_resolve_not_found
    Input: "[[NonExistent]]"
    Assert: hard error

test_ambiguous_name
    Input: two classes named "Config" in different modules
    Assert: [[Config]] → hard error suggesting [[module.Config]]

test_fully_qualified
    Input: "[[dataflow.Pipeline]]"
    Assert: resolves correctly even with ambiguity

test_no_links
    Input: "No links here"
    Assert: text unchanged
```

---

### Stage 6: Markdown Renderer

**Module:** `pydocgen/markdown_renderer.py`

**Input:** String with Markdown + HTML mix.

**Output:** Pure HTML string.

**Functionality:**
- Convert Markdown to HTML using `markdown` library.
- Preserve existing HTML tags.
- Add `id` attributes to `<h2>` and `<h3>` for anchor links.
- Wrap code blocks in proper `<pre><code>` with language class.

**Tests:**
```
test_basic_markdown
    Input: "# Title\nParagraph text"
    Assert: <h1>Title</h1><p>Paragraph text</p>

test_preserve_html
    Input: "<div class='custom'>text</div>"
    Assert: output contains the div unchanged

test_mixed_content
    Input: "## Header\n<div>html</div>\nMore **markdown**"
    Assert: both HTML and markdown rendered correctly

test_heading_anchors
    Input: "## Public Methods"
    Assert: <h2 id="public-methods">Public Methods</h2>

test_code_blocks
    Input: fenced code block with python
    Assert: <pre><code class="language-python">...</code></pre>
```

---

### Stage 7: Layout Generator & HTML Output

**Module:** `pydocgen/layout.py`

**Input:** Rendered page HTML + node tree + current node.

**Output:** Complete HTML page.

**Functionality:**
- Generate navigation tree HTML (collapsible, current highlighted).
- Extract `<h2>` / `<h3>` from page content for right sidebar.
- Generate breadcrumb from node path.
- Assemble into base layout template.
- Generate `search_index.json` from all nodes.

**Tests:**
```
test_nav_tree_html
    Input: tree with 3 levels
    Assert: nested <ul> structure, all titles present

test_nav_current_highlighted
    Input: tree + current node
    Assert: current node has "active" class, parents expanded

test_breadcrumb
    Input: node at path Root > API > DataFlow > Pipeline
    Assert: breadcrumb HTML with 4 linked segments

test_contents_sidebar
    Input: page with 3 h2 and 2 h3
    Assert: 5 anchor links in sidebar

test_full_page_assembly
    Input: rendered content + tree + node
    Assert: valid HTML with all 3 columns populated

test_search_index
    Input: tree with multiple nodes
    Assert: JSON with all node titles, class/function names, descriptions
```

---

### Stage 8: Build Orchestrator & CLI

**Module:** `pydocgen/builder.py` + `pydocgen/__main__.py`

**Input:** Config path (CLI argument).

**Output:** Full HTML site in `output_dir`.

**Functionality:**
- Orchestrate all stages in order:
  1. Parse config
  2. Scan source folders → `SourceData` per folder
  3. Preprocess all `.dcfg` files
  4. Build node tree
  5. Build cross-link index
  6. For each node: render template → markdown → resolve links → wrap in layout
  7. Generate search index
  8. Copy assets
  9. Write all HTML files
- CLI with `--config` option.
- Clear error messages with file/line context.

**Tests:**
```
test_full_build_minimal
    Input: project with 1 manual page, no auto_source
    Assert: output_dir has 1 HTML file + assets

test_full_build_with_source
    Input: project with auto_source, 2 classes
    Assert: output has module page + 2 class pages

test_full_build_cross_links
    Input: template with [[ClassName]] references
    Assert: rendered HTML has working <a href> links

test_build_error_missing_template
    Input: node references non-existent template
    Assert: build fails with clear error message

test_build_error_missing_param
    Input: template requires param not in config
    Assert: build fails with clear error message

test_assets_copied
    Input: assets_dir with files
    Assert: files present in output_dir/assets/

test_cli_default_config
    Run: python -m pydocgen build (with .sdoc.tree in cwd)
    Assert: builds successfully

test_cli_custom_config
    Run: python -m pydocgen build --config path/to/config.dcfg
    Assert: uses specified config
```

---

## 15. Error Handling Summary

| Condition | Type | Message Example |
|-----------|------|-----------------|
| `%%PARAM%%` not declared in template | Hard error | `template.dtmpl: Unknown param %%FOO%%. Declared params: [CLASS_ID, NAME]` |
| Required `param@X` not in config | Hard error | `template.dtmpl: Required param 'X' not provided. Node: "Pipeline Class"` |
| `{{class_name#NonExistent}}` | Hard error | `template.dtmpl: Class 'NonExistent' not found in source src/dataflow/` |
| Data tag with no source | Hard error | `template.dtmpl: Tag {{classes}} requires source, but node "Introduction" has no source` |
| `[[Unknown]]` cross-link | Hard error | `template.dtmpl: Cross-link target 'Unknown' not found in index` |
| Ambiguous cross-link | Hard error | `template.dtmpl: Ambiguous target 'Config'. Use [[dataflow.Config]] or [[utils.Config]]` |
| `branch: "X"` not in tree | Hard error | `.sdoc: Branch "X" not found in main tree` |
| Unknown macro `%%__INVALID__%%` | Hard error | `.sdoc: Unknown macro '__INVALID__'. Valid: __CLASSES__, __FUNCTIONS__` |
| Template file not found | Hard error | `Node "Pipeline": template 'nonexistent' not found in docs/templates/` |
| `.sdoc` missing in subfolder | Ignored | (folder skipped silently) |
| Empty `{{public_methods#X}}` | Warning | `Warning: Pipeline has no public methods` |
| Empty `:: for` loop | Warning | `Warning: {{classes}} returned 0 items in template.dtmpl` |

---

## 16. Dependencies

- **Python 3.10+**
- **`ast`** — standard library, Python parsing
- **`markdown`** — Markdown to HTML conversion (`pip install markdown`)
- **`pyyaml`** — YAML parsing (`pip install pyyaml`)
- **No other external dependencies**

---

## 17. Stage Execution Order

```
Stage 1: Parser         → can be built and tested in isolation
Stage 2: DCFG Preprocessor → needs class/function name lists (from Stage 1)
Stage 3: Template Engine    → needs SourceData (from Stage 1)
Stage 4: Tree Builder       → needs Stage 1 + Stage 2
Stage 5: Cross-Link Index   → needs Stage 4
Stage 6: Markdown Renderer  → standalone
Stage 7: Layout Generator   → needs Stage 4 output
Stage 8: Build Orchestrator → integrates all stages
```

Stages 1, 2, 3, 6 can be developed in parallel. Stage 4 integrates 1+2. Stage 5 needs 4. Stage 7 needs 4. Stage 8 is final integration.
