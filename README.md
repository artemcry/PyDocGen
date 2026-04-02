# slop-doc

Static documentation generator for Python projects. Write pages in Markdown templates, auto-extract API docs from Python source via AST, and get a searchable HTML site with a dark theme and left-nav tree.

## Install

```bash
pip install slop-doc
```

Requires Python 3.10+.

---

## Quickstart

### 1. Scaffold a docs folder

```bash
slop-doc init
# creates docs/ with a default .sdoc.tree config
```

Or use a custom name:

```bash
slop-doc init --name my-docs
```

### 2. Edit `.sdoc.tree`

`docs/.sdoc.tree` is the main config file:

```yaml
project_name: "MyProject"
version: "1.0.0"
output_dir: "build/"          # HTML output goes here
templates_dir: "templates/"   # your .dtmpl template files
assets_dir: "assets/"         # CSS, images (optional)
docstring_style: "google"     # google | numpy | sphinx
mainpage: "main_page"         # template for index.html (root landing page)

tree:
  - title: "Project Tree"
    template: "<your template>"
    auto_source: "../<path to project root>/"
```

### 3. Create templates

Templates live in `templates/` and use the `.dtmpl` extension.

**templates/my_page.dtmpl:**

```markdown
# %%TITLE%%

Welcome to **%%PROJECT_NAME%%** v%%VERSION%%!

See [[mymodule/MyClass]] for the core API.
```

### 4. Build

Run from inside your docs folder (where `.sdoc.tree` lives):

```bash
cd docs/
slop-doc build
```

Or point to the folder explicitly:

```bash
slop-doc build -d docs/
```

### 5. Open in browser

```bash
slop-doc open
# or
slop-doc open -d docs/
```

Output: `build/index.html` (root landing) + `build/` subdirectories with all pages.

---

## Auto-documenting Python source

For any Python package you want to auto-document, place a `.sdoc` file inside that package folder:

**src/mymodule/.sdoc:**

```yaml
branch: "API Reference"         # where to attach in the nav tree
title: "MyModule"
template: "default_module"      # built-in template
source: "."                     # always "." — current folder
params:
  MODULE_DESCRIPTION: "High-level description of this module."

children:
  %%__CLASSES__%%
  - title: "%%__CLASS__%% Class"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%
```

`%%__CLASSES__%%` is a macro that expands into one child entry per class found in the folder.
Same pattern works for functions: use `%%__FUNCTIONS__%%` / `%%__FUNCTION__%%`.

To exclude specific items:

```yaml
  %%__CLASSES__%%
  - title: "%%__CLASS__%% Class"
    template: "default_class"
    params:
      CLASS_ID: "%%__CLASS__%%"
  %%__CLASSES__%%.exclude(InternalClass)
```

Point `auto_source` in `.sdoc.tree` at the parent of these folders to pick them up automatically.

---

## Built-in templates

These ship with slop-doc and can be used without creating your own:

| Template | Use for |
|---|---|
| `default_module` | Module-level page (class list, function list, constants) |
| `default_class` | Class detail page (methods, properties, docstrings) |
| `main_page` / `default_main_page` | Root landing page (`index.html`) |

If a template isn't found in your `templates_dir`, slop-doc falls back to the built-in version.

---

## Template syntax

### Parameters (`%%PARAM%%`)

Pass values from the tree config into a template:

```yaml
# in .sdoc.tree or .sdoc
params:
  GREETING: "Hello, world!"
```

```markdown
<!-- in your .dtmpl file -->
%%GREETING%%
```

### Auto-generated data tags (`{{tag}}`)

Used inside built-in templates (or yours, if you call them):

| Tag | Description |
|---|---|
| `{{title}}` | Page title |
| `{{project_name}}` | From config |
| `{{version}}` | From config |
| `{{classes}}` | Rendered class list for the module |
| `{{functions}}` | Rendered function list |
| `{{constants}}` | Module-level constants |
| `{{class_name}}` | Class name (class page) |
| `{{class_short_description}}` | First line of docstring |
| `{{class_full_description}}` | Full docstring |
| `{{class_info}}` | Base classes, decorators |
| `{{properties}}` | Class properties |
| `{{public_methods_summary}}` | Public methods table |
| `{{private_methods_summary}}` | Private methods table |
| `{{methods_details}}` | Full method documentation |

### Loops (`:: for ... :: endfor`)

Iterate over collected items inside a template:

```markdown
:: for cls in classes ::
## %%CLASS_NAME%%
{{class_short_description}}
:: endfor ::
```

---

## Cross-links

Link to any class or method anywhere in your docs using `[[folder/ClassName]]`:

```markdown
See [[dataflow/Pipeline]] for the main class.

Call [[dataflow/Pipeline.run]] to start execution.

[[dataflow/Pipeline|the pipeline]] is the entry point.
```

**Rules:**
- Always use `folder/ClassName` — the folder is the Python package directory name, not the nav title.
- For methods: `folder/ClassName.method_name`
- Custom link text: `[[folder/ClassName|your text]]`

Cross-links are resolved at build time. Broken links print a warning but don't fail the build.

---

## Assets

Place CSS, images, and JS in your `assets_dir`:

```
docs/assets/
├── style.css     # custom styles (overrides built-in dark theme)
└── logo.png
```

If `style.css` is absent, the built-in dark Qt-inspired theme is used.
`search.js` (client-side search) is always provided by slop-doc — you don't need to supply it.

---

## Project layout reference

```
myproject/
├── docs/                      # your docs folder (created by slop-doc init)
│   ├── .sdoc.tree             # main config
│   ├── templates/             # .dtmpl files
│   ├── assets/                # CSS, images (optional)
│   └── build/                 # generated output (gitignore this)
│       ├── index.html         # root landing page
│       └── assets/
└── src/
    └── mymodule/
        ├── __init__.py
        └── .sdoc              # auto-doc config for this package
```

---

## CLI reference

```
slop-doc init [--name NAME]    scaffold a new docs folder (default: docs/)
slop-doc build [-d DIR]        build docs (DIR = folder with .sdoc.tree)
slop-doc open  [-d DIR]        open built docs in browser
```

`-d` defaults to the current directory if omitted.
You can also run as a module: `python -m slop_doc build`.

---

## Configuration reference

### `.sdoc.tree` fields

| Field | Default | Description |
|---|---|---|
| `project_name` | `"Documentation"` | Displayed in header |
| `version` | `""` | Version string |
| `output_dir` | `"build/"` | Output directory (relative to `.sdoc.tree`) |
| `templates_dir` | `"docs/templates/"` | Your `.dtmpl` files |
| `assets_dir` | `"docs/assets/"` | Your CSS/images |
| `docstring_style` | `"google"` | `google`, `numpy`, or `sphinx` |
| `mainpage` | `"main_page"` | Template for `index.html` |
| `tree` | — | Navigation tree (list of nodes) |

### Tree node fields

```yaml
tree:
  - title: "Page Title"           # required
    template: "template_name"     # .dtmpl file name without extension
    output_path: "custom.html"    # optional override
    auto_source: "src/"           # scan for .sdoc files
    params:
      KEY: "value"
    children:
      - ...
```

---

## License

MIT
