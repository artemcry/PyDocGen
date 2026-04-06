# slop-doc

Static documentation generator for Python projects. Parses Python source code via AST, renders Markdown pages with embedded data tags and presentation functions into a styled 3-column HTML site with navigation tree, cross-linking, and search.

## Installation

```bash
pip install slop-doc
```

Requires Python >= 3.10.

## Quick Start

```bash
# 1. Create a docs folder with starter root.md
slop-doc init --name docs

# 2. Edit docs/root.md, add .md pages

# 3. Build
slop-doc build -d docs

# 4. Open in browser
slop-doc open -d docs
```

## CLI Commands

| Command | Description |
|---|---|
| `slop-doc init [--name <folder>]` | Create a new docs folder with a starter `root.md`. Default name: `docs` |
| `slop-doc build [-d <dir>]` | Build documentation. Looks for `root.md` in `-d` dir or current directory |
| `slop-doc open [-d <dir>]` | Open built `index.html` in the browser |

---

## How It Works

The folder structure **is** the documentation tree. Every `.md` file becomes a page; every subfolder with a `root.md` becomes a folder node in the navigation.

```
my-docs/                    ← docs root (contains root.md)
├── root.md                 ← project config + landing page
├── getting-started.md      ← top-level page
├── 1-installation.md       ← sorted by numeric prefix (prefix stripped from title)
├── 2-usage.md
└── api/                    ← subfolder = folder node in nav
    ├── root.md             ← folder config + folder landing page
    ├── overview.md         ← page inside the folder
    └── advanced/
        └── root.md
```

**Build output**: a self-contained HTML site with `assets/style.css`, `assets/search.js`, and one `.html` per page. Works with `file://` protocol (no server needed).

---

## Front-matter

Each `.md` file can start with a JSON config block. The block is relaxed JSON — supports `//` comments, `#` comments, trailing commas, and unquoted keys.

```markdown
{
    "title": "My Page",
    "default_source_folder": "../src/mypackage"
}

# My Page

Page content here...
```

### Page-level keys

| Key | Type | Description |
|---|---|---|
| `title` | `string` | Display name in the nav tree. Falls back to the first `#` heading, then filename |
| `default_source_folder` | `string` | Path to Python source folder for this page (and its children). Resolved relative to the **parent directory** of the docs root |
| `children` | `object` | Auto-generated child pages from source code. See [Children](#children) |

### Project-level keys (only in the root `root.md`)

| Key | Type | Default | Description |
|---|---|---|---|
| `project_name` | `string` | `"Documentation"` | Displayed in the site header |
| `version` | `string` | `""` | Shown in page titles |
| `output_dir` | `string` | `"build"` | Output folder (relative to docs root) |
| `assets_dir` | `string` | — | Custom assets folder (relative to docs root). Files here override defaults |

### Example root.md

```json
{
    "title": "MyProject Docs",
    "project_name": "MyProject",
    "version": "2.1.0",
    "output_dir": "build",
    "default_source_folder": "../src/myproject"
}

# Welcome to MyProject

This is the landing page.
```

---

## Source Folder

The `default_source_folder` key tells slop-doc where to find your Python source code. It is **inherited** by child pages — set it once on a folder's `root.md` and all pages inside that folder use it automatically.

A deeper `root.md` or individual page can override it with its own `default_source_folder`.

**Path resolution**: always relative to the **parent of the docs root**, not relative to the `.md` file. For example, if your docs are in `project/docs/` and your source is in `project/src/mypackage/`, use:

```json
{
    "default_source_folder": "../src/mypackage"
}
```

This works regardless of how deeply nested the `.md` file is.

---

## Data Tags

Data tags are placeholders in Markdown that expand to lists of items from your Python source code. Write them as `{{tag_name}}` in the page body.

### Available tags

| Tag | What it lists |
|---|---|
| `{{classes}}` | All classes (from files directly in the source folder) |
| `{{functions}}` | All module-level functions |
| `{{constants}}` | All constants (ALL_CAPS names) |
| `{{enums}}` | Enum classes |
| `{{dataclasses}}` | Dataclass classes |
| `{{interfaces}}` | Abstract base classes (ABC / have abstract methods) |
| `{{protocols}}` | Protocol classes |
| `{{exceptions}}` | Exception classes |
| `{{plain_classes}}` | Regular classes that don't fit any category above |

Each tag has a **recursive variant** with `_rec` suffix that includes files from all subfolders:

| Flat (direct files only) | Recursive (all subfolders) |
|---|---|
| `{{classes}}` | `{{classes_rec}}` |
| `{{functions}}` | `{{functions_rec}}` |
| `{{enums}}` | `{{enums_rec}}` |
| ... | ... |

### Inline rendering

In the page body, class-type tags render as cross-linked lists:

```markdown
## Available Classes

{{classes}}
```

Becomes something like: `DataSource, FetchSpec, ColumnMap` — each name is a clickable cross-link to its class page.

If no items are found, renders as: *None found.*

---

## Children (Auto-Generated Pages)

The `children` key in front-matter generates child pages from source code. Each child gets a full dedicated page with class/function documentation.

```json
{
    "title": "API Reference",
    "default_source_folder": "../src/mypackage",
    "children": {
        "classes": "{{classes}}"
    }
}
```

This creates a child page for **every class** found in the source folder. Each child page appears in the nav tree under this folder.

### Syntax

The `children` value is an object mapping a **type** to a **list of names**:

```json
{
    "children": {
        "classes": "{{classes}}",
        "functions": "{{functions}}"
    }
}
```

You can also mix tag expansion with explicit names:

```json
{
    "children": {
        "classes": ["{{interfaces}}", "MySpecialClass"]
    }
}
```

### Supported child types

| Type | Generates |
|---|---|
| `classes` | Class pages with full docs (description, info, properties, methods) |
| `enums` | Same as classes, filtered to enums |
| `dataclasses` | Same, filtered to dataclasses |
| `interfaces` | Same, filtered to interfaces/ABCs |
| `protocols` | Same, filtered to protocols |
| `exceptions` | Same, filtered to exceptions |
| `plain_classes` | Same, filtered to plain classes |
| `functions` | Function pages (name + stub) |

### Auto-generated class page content

Each auto-generated class page contains:

```
# ClassName

(class description)

## Info
(module, file:line, base classes)

## Properties
(table of @property methods)

## Public Methods
(summary table with links)

## Private Methods
(summary table)

## Method Details
(full signature, parameters, returns, raises for each method)
```

---

## Presentation Functions

Presentation functions render structured data tables and detail blocks from your source code. Write them as `%function_name(args)%` in the page body.

### Table functions

| Function | Output |
|---|---|
| `%classes_table({{classes}})%` | Table of classes with descriptions. Class names are cross-links |
| `%functions_table({{functions}})%` | Table of functions with signatures and descriptions |
| `%constants_table({{constants}})%` | Table of constants with values and types |

The argument can be a `{{tag}}` (expands to all matching items), a comma-separated list of names, or empty (uses all).

### Class detail functions

| Function | Output |
|---|---|
| `%class_description(ClassName)%` | Short + full description |
| `%class_info(ClassName)%` | Table: module, file:line, base classes |
| `%properties(ClassName)%` | Table of `@property` methods: name, type, description |
| `%base_classes(ClassName)%` | Comma-separated list of base classes |
| `%decorators(ClassName)%` | Comma-separated list of decorators |
| `%source_link(ClassName)%` | Source file path and line number |

### Methods functions

| Function | Output |
|---|---|
| `%methods_table(ClassName)%` | Public methods summary table |
| `%methods_table(ClassName, private)%` | Private methods (`_name`) table |
| `%methods_table(ClassName, static)%` | Static methods table |
| `%methods_table(ClassName, classmethod)%` | Class methods table |
| `%methods_table(ClassName, dunder)%` | Dunder methods (`__name__`) table |
| `%methods_table(ClassName, all)%` | All methods (public + private, including dunder) |
| `%methods_details(ClassName)%` | Full detail blocks for all methods: signature, params, returns, raises |

### Example page

```markdown
{
    "title": "API Reference",
    "default_source_folder": "../src/mypackage"
}

# API Reference

## Classes

%classes_table({{classes}})%

## Functions

%functions_table({{functions}})%

## Constants

%constants_table({{constants}})%
```

---

## Cross-Links

Link to any class or method page from anywhere in your documentation using `[[double bracket]]` syntax.

| Syntax | Links to |
|---|---|
| `[[folder/ClassName]]` | Class page |
| `[[folder/ClassName.method_name]]` | Method anchor on the class page |
| `[[folder/ClassName\|Display Text]]` | Class page with custom display text |

The `folder` is the **basename** of the source folder. For example, if `default_source_folder` is `../src/mypackage`, the folder slug is `mypackage`.

```markdown
See the [[mypackage/DataSource]] class for details.

The [[mypackage/DataSource.fetch]] method handles data retrieval.

Check [[mypackage/DataSource|the data source]] documentation.
```

### Hidden class pages

Every class in an indexed source folder automatically gets a dedicated page, even if not explicitly listed in `children`. These "hidden" pages:

- Are rendered with full class documentation
- Are indexed for cross-link resolution
- Appear in search results
- Do **not** appear in the navigation tree

This means `[[folder/AnyClass]]` always resolves, as long as the class exists in a parsed source folder.

---

## Docstring Format

slop-doc parses **Google-style** docstrings:

```python
class MyClass(BaseClass):
    """Short description of the class.

    Longer description that provides more detail
    about the class and its purpose.
    """

    def my_method(self, name: str, count: int = 5) -> list[str]:
        """Short description of the method.

        More detailed description here.

        Args:
            name: The name to process.
            count: How many times to repeat. Defaults to 5.

        Returns:
            A list of processed strings.

        Raises:
            ValueError: If name is empty.
            TypeError: If count is not an integer.
        """
```

### What gets parsed

- **Classes**: all public classes (private `_ClassName` are skipped)
- **Methods**: all methods including private and dunder, with full signatures
- **Functions**: top-level functions only (private and dunder are skipped)
- **Constants**: `ALL_CAPS` names assigned at module level
- **Properties**: methods decorated with `@property`
- **Type annotations**: preserved from source, displayed in method signatures and tables

### Class classification

Classes are automatically classified based on their base classes and decorators:

| Category | Detection rule |
|---|---|
| Enum | Inherits from `Enum`, `IntEnum`, `StrEnum`, `Flag`, `IntFlag` |
| Dataclass | Has `@dataclass` decorator |
| Interface/ABC | Inherits from `ABC`/`ABCMeta` or has any `@abstractmethod` |
| Protocol | Inherits from `Protocol` |
| Exception | Inherits from `Exception`/`BaseException` or name ends with `Error`/`Exception` |
| Plain class | None of the above |

---

## File Sorting

Files are sorted in the nav tree by:

1. **Numeric prefix first**: `1-intro.md`, `2-setup.md`, `3-api.md` — sorted by number
2. **Alphabetical second**: files without numeric prefix sort alphabetically

The numeric prefix is stripped from the display title: `1-introduction.md` shows as "Introduction".

---

## Assets and Styling

slop-doc ships with a default dark theme (`style.css`) and client-side search (`search.js`).

To customize:

1. Set `assets_dir` in your root `root.md`:
   ```json
   {
       "assets_dir": "assets"
   }
   ```

2. Place your custom `style.css` in that folder. It will replace the default.

The `search.js` is always copied from defaults (the search index is embedded inline in each page).

---

## Complete Example

### Project structure

```
my-project/
├── src/
│   └── mylib/
│       ├── __init__.py
│       ├── client.py        # Client, Config classes
│       ├── models.py         # User, Product dataclasses
│       └── exceptions.py     # ApiError, NotFoundError
└── docs/
    ├── root.md
    ├── 1-getting-started.md
    └── api/
        ├── root.md
        └── overview.md
```

### docs/root.md

```markdown
{
    "title": "MyLib",
    "project_name": "MyLib",
    "version": "1.0.0",
    "output_dir": "build"
}

# MyLib Documentation

Welcome to the MyLib documentation.
```

### docs/1-getting-started.md

```markdown
# Getting Started

## Installation

​```bash
pip install mylib
​```

## Quick Start

​```python
from mylib import Client

client = Client(api_key="...")
result = client.fetch("data")
​```
```

### docs/api/root.md

```markdown
{
    "title": "API Reference",
    "default_source_folder": "../../src/mylib",
    "children": {
        "classes": "{{classes}}"
    }
}

# API Reference

## All Classes

%classes_table({{classes}})%

## Functions

%functions_table({{functions}})%

## Constants

%constants_table({{constants}})%
```

This generates:
- A nav tree: Getting Started, API Reference > Client, Config, User, Product, ApiError, NotFoundError
- Each class gets a full page with methods, properties, signatures
- Cross-links like `[[mylib/Client]]` work from any page

### Build and view

```bash
cd docs
slop-doc build
slop-doc open
```

---

## Output Structure

```
docs/build/
├── index.html              ← root.md landing page
├── getting-started.html
├── api/
│   ├── index.html          ← api/root.md
│   ├── client.html         ← auto-generated from children
│   ├── config.html
│   ├── user.html
│   └── ...
└── assets/
    ├── style.css
    └── search.js
```

---

## Summary of Syntax

| Syntax | Where | Purpose |
|---|---|---|
| `{ "key": "value" }` | Top of `.md` file | Front-matter config |
| `{{tag}}` | Page body or `children` value | Expand to list of items from source |
| `{{tag_rec}}` | Page body or `children` value | Same but recursive (includes subfolders) |
| `%function(args)%` | Page body | Render tables/details from source data |
| `[[folder/Class]]` | Page body | Cross-link to class page |
| `[[folder/Class.method]]` | Page body | Cross-link to method anchor |
| `[[folder/Class\|text]]` | Page body | Cross-link with custom display text |

## License

MIT
