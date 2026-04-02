# slop-doc

Static documentation generator for Python projects. Write your documentation in Markdown templates, extract API docs automatically from Python source code, and get a searchable HTML documentation site.

## Installation

```bash
pip install slop-doc
```


## Quick Start

### 1. Create Project Structure

```
myproject/
├── .sdoc.tree          # Main configuration
├── docs/
│   ├── templates/      # Your .dtmpl template files
│   └── assets/         # CSS, images, JS (optional)
└── src/
    └── your_module/    # Python source to document
```

### 2. Create `.sdoc.tree` Configuration

```yaml
project_name: "MyProject"
version: "1.0.0"
output_dir: "build/docs/"
templates_dir: "docs/templates/"
assets_dir: "docs/assets/"

tree:
  - title: "Introduction"
    template: "introduction"

  - title: "Getting Started"
    children:
      - title: "Installation"
        template: "installation"

  - title: "API Reference"
    auto_source: "src/"
```

### 3. Create Templates

**docs/templates/introduction.dtmpl:**

```markdown
# Introduction

Welcome to **MyProject**!

## Quick Example

[[dataflow/Pipeline]]

See the [Getting Started](getting-started/installation.html) section.
```

**docs/templates/installation.dtmpl:**

```markdown
# Installation

## Requirements

- Python 3.10+
- pip

## Install

```bash
pip install myproject
```
```

### 4. Add Auto-Documentation (Optional)

For each Python package you want to auto-document, create a `.sdoc` file:

**src/mypackage/.sdoc:**

```yaml
branch: "API Reference"
title: "MyPackage"
template: "default_module"
source: "."
params:
  MODULE_DESCRIPTION: "Description of your module."

children:
  %%__CLASSES__%%
  - title: "%%__CLASS__%% Class"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%
```

### 5. Build

```bash
python -m slop_doc build
```

Or with custom config path:

```bash
python -m slop_doc build --config path/to/.sdoc.tree
```

## Configuration Reference

### `.sdoc.tree` (Main Config)

| Field | Type | Description |
|-------|------|-------------|
| `project_name` | string | Name displayed in header |
| `version` | string | Version string |
| `output_dir` | string | Output directory (relative to config) |
| `templates_dir` | string | Templates directory |
| `assets_dir` | string | Assets directory |
| `docstring_style` | string | Docstring format: `google` (default), `numpy`, `sphinx` |
| `tree` | list | Navigation tree structure |

### Tree Node Fields

```yaml
tree:
  - title: "Page Title"              # Required: display name
    template: "template_name"         # Template file (without .dtmpl)
    output_path: "custom/page.html"   # Optional: override output path
    children: [...]                  # Optional: nested pages
    auto_source: "src/"              # Optional: auto-scan folder for .sdoc files
    params:                           # Optional: template parameters
      KEY: "value"
```

### `.sdoc` (Folder Config)

Place `.sdoc` in each Python package folder:

```yaml
branch: "Parent > Child"              # Where to attach in navigation
title: "Module Name"                  # Page title
template: "default_module"            # Or your custom template
source: "."                          # Always "." for current folder
params:
  MODULE_DESCRIPTION: "..."
children:
  %%__CLASSES__%%                    # Auto-expand all classes
  - title: "%%__CLASS__%% Class"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%
```

### Template Macros

| Macro | Description |
|-------|-------------|
| `%%__CLASSES__%%` | Placeholder replaced with all classes in folder |
| `%%__CLASS__%%` | Current class name (inside CLASSES block) |
| `%%__FUNCTIONS__%%` | All functions in folder |
| `%%__FUNCTION__%%` | Current function name |

## Template Variables

Templates receive data via `{{variable}}` syntax:

### Common Variables

| Variable | Description |
|----------|-------------|
| `{{title}}` | Page title from tree config |
| `{{project_name}}` | From config |
| `{{version}}` | From config |

### Module Template Variables (`default_module`)

| Variable | Description |
|----------|-------------|
| `{{classes}}` | Rendered class list |
| `{{functions}}` | Rendered function list |
| `{{constants}}` | Constants list |
| `{{MODULE_DESCRIPTION}}` | From params |

### Class Template Variables (`default_class`)

| Variable | Description |
|----------|-------------|
| `{{class_name}}` | Class name |
| `{{class_short_description}}` | First line of docstring |
| `{{class_full_description}}` | Full docstring |
| `{{class_info}}` | Base classes, decorators |
| `{{properties}}` | Class properties |
| `{{public_methods_summary}}` | Public methods list |
| `{{private_methods_summary}}` | Private methods list |
| `{{methods_details}}` | Detailed method docs |

## Cross-Links

Link to classes and methods using `[[folder/ClassName]]` syntax:

```markdown
See [[dataflow/Pipeline]] for details.

Call [[dataflow/Pipeline.run]] to execute.
```

**Rules:**
- Always use `folder/ClassName` format (not just `ClassName`)
- For methods: `folder/ClassName.method_name`
- For custom text: `[[dataflow/Pipeline|the main pipeline class]]`

## Default Templates

slop-doc includes built-in templates you can use:

- `default_module` — For Python module pages (auto-generates from source)
- `default_class` — For Python class pages (auto-generates from source)
- Your custom templates in `docs/templates/`

If a template isn't found in your templates dir, defaults are used.

## Assets

### User Assets

Place CSS, images, JS in `docs/assets/`:

```
docs/assets/
├── style.css          # Your custom styles
├── logo.png           # Images
└── custom.js         # Custom scripts
```

### Default Assets

If you don't provide `style.css` or `search.js`, defaults are used automatically:
- **style.css** — Dark theme inspired by Qt documentation
- **search.js** — Client-side search

## Project Structure

```
myproject/
├── .sdoc.tree              # Main config
├── docs/
│   ├── templates/         # .dtmpl files
│   └── assets/            # CSS, images (optional)
└── src/
    └── mypackage/         # Python source
        └── .sdoc           # Folder config for auto-docs
```

## Full `.sdoc.tree` Example

```yaml
project_name: "DataFlow"
version: "2.0.0"
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
      - title: "Quick Start"
        template: "quickstart"

  - title: "API Reference"
    auto_source: "src/"

  - title: "Contributing"
    template: "contributing"
```

---

## How It Works

slop-doc builds your documentation in **8 stages**:

```
Config File (.sdoc.tree)
         │
         ▼
┌─────────────────────┐
│  SDOC Preprocessor  │  Expand macros in .sdoc configs
│ (sdoc_preprocessor) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────┐
│  Tree Builder   │  Parse .sdoc.tree + .sdoc configs → navigation tree
│  (tree_builder) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Parser      │  Extract classes/functions from Python source via AST
│    (parser)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Cross-Links    │  Build index for [[folder/ClassName]] references
│  (cross_links)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Template Engine │  Process .dtmpl templates with params + data tags
│ (template_engine│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Markdown     │  Convert Markdown → HTML
│   (markdown)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Layout      │  Assemble full page (header, nav, sidebar, content)
│    (layout)     │
└────────┬────────┘
         │
         ▼
   Output (HTML files + assets)
```

### Stage 1 — Parser (`parser.py`)

Extracts structured data from Python source files using the AST (Abstract Syntax Tree):

- **Classes** — name, base classes, decorators, docstring, methods, properties
- **Functions** — signature, parameters, return type, decorators, docstring
- **Constants** — module-level ALL_CAPS variables

Uses Google-style docstrings (Args:, Returns:, Raises:, Examples:).

### Stage 2 — SDOC Preprocessor (`sdoc_preprocessor.py`)

Expands macros in `.sdoc` YAML configs before parsing:

- `%%__CLASSES%%` — replaced with one entry per class
- `%%__CLASS%%` — current class name (inside block)
- `%%__FUNCTIONS%%` / `%%__FUNCTION%%` — same for functions
- `.exclude(ClassName)` — filter out specific items

### Stage 3 — Tree Builder (`tree_builder.py`)

Parses `.sdoc.tree` and `.sdoc` YAML configs into a **navigation tree**:

```
Node {
    title: "Introduction"
    template: "introduction"
    output_path: "introduction.html"
    children: [Node, Node, ...]
    source: "."          # Python source folder (for auto-docs)
    params: {}            # Template parameters
}
```

Handles `auto_source` scanning (finds `.sdoc` files recursively) and macro expansion (`%%__CLASSES__%%`, `%%__FUNCTIONS__%%`).

### Stage 4 — Cross-Link Index (`cross_links.py`)

Builds a global index for `[[folder/ClassName]]` cross-references:

- **folder_class_index**: `"dataflow/Pipeline"` → `"api-reference/dataflow/pipeline-class.html"`
- **qualified_index**: `"Pipeline.run"` → URL with anchor
- **short_index**: `"Pipeline"` → list of possible matches (for disambiguation)

### Stage 5 — Template Engine (`template_engine.py`)

Processes `.dtmpl` templates in 4 steps:

1. **Parse params** — Extract `param@NAME` declarations from top of template
2. **Substitute `%%PARAM%%`** — Replace with values from node config
3. **Expand `:: for X in ... :: endfor`** — Loop over classes/functions
4. **Render `{{data_tag}}`** — Insert auto-generated content (`{{classes}}`, `{{methods_details}}`, etc.)

### Stage 6 — Markdown Renderer (`markdown_renderer.py`)

Converts Markdown to HTML using the Markdown library.

### Stage 7 — Layout (`layout.py`)

Assembles the final HTML page:

- **Header** — project name, breadcrumb, search bar
- **Left nav** — collapsible tree navigation with active page highlight
- **Right sidebar** — table of contents (h2/h3 headings)
- **Content** — the rendered page content
- **Assets** — copies CSS/JS, falls back to defaults if not provided

### Stage 8 — Output

Writes the HTML file to `output_dir`. Assets are copied (user dir first, then defaults for missing files like `style.css`).

---

## Troubleshooting

**Template not found error:**
- Check `templates_dir` path in `.sdoc.tree`
- Ensure template file has `.dtmpl` extension in filename
- Template names in tree config should not include extension

**Cross-link errors:**
- Use `folder/ClassName` format (e.g., `[[dataflow/Pipeline]]`)
- Check that the target class exists in the indexed source

**Build succeeds but no output:**
- Verify `output_dir` exists or can be created
- Check that nodes have valid `template` values

## License

MIT
