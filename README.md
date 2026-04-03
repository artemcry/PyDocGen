# slop-doc

Static documentation generator for Python projects. Walks your source tree, parses `.md` files with JSON front-matter, and produces a searchable 3-column HTML documentation site.

## Quick Start

```bash
# Create a new docs folder
slop-doc init my-docs

# Add .md files and source paths (see below)

# Build
slop-doc build -d my-docs

# Open in browser
slop-doc open -d my-docs
```

## Project Structure

A documentation folder looks like this:

```
docs/
├── root.md          # Project config + landing page
├── intro.md         # Regular page
└── api/
    ├── root.md      # Folder config + landing page (inherits source)
    ├── overview.md  # Regular page
    └── guide.md
```

Folder structure **is** the navigation tree. No config files needed beyond `root.md`.

## root.md — Project Root

`root.md` sets project-level options and serves as the landing page:

```json
{
    "title": "My Library",
    "project_name": "My Library",
    "version": "2.0",
    "output_dir": "build"
}
```

Everything after the front-matter block is the landing page Markdown content.

## root.md — Folder Node

Each folder can have its own `root.md` that acts as both a folder config and a page:

```json
{
    "title": "API Reference",
    "default_source_folder": "../../src"
}
```

# API Reference

Content of the folder's landing page...

## Data Tags — `{{classes}}`, `{{functions}}`, `{{constants}}`

Data tags always expand to a **list of names** — a data primitive. They are not HTML.

In Markdown body, `{{classes}}` becomes a comma-separated linked list of `[[folder/ClassName]]` cross-links. Functions and constants become `` `name` `` inline code.

In presentation function arguments, they expand to comma-separated names that the function then parses.

```markdown
## Classes

{{classes}}

## Functions

{{functions}}
```

## Presentation Functions — `%func(args)%`

Presentation functions render structured HTML from source data. They go **explicitly** in your Markdown where you want the output.

All functions use `%name(args)%` syntax (single `%` on each side).

### Tables

```markdown
%classes_table({{classes}})%
%functions_table({{functions}})%
%constants_table({{constants}})%
```

With specific items:

```markdown
%classes_table(ClassA, ClassB)%
```

### Class Detail

```markdown
%class_info(MyClass)%          — module, file, line, base classes
%class_description(MyClass)%   — short + full description text
%properties(MyClass)%           — property table
```

### Methods

```markdown
%methods_table(MyClass)%        — public methods summary
%methods_table(MyClass, private)% — private methods
%methods_details(MyClass)%      — full method documentation blocks
```

### Other

```markdown
%base_classes(MyClass)%        — comma-separated base class names
%decorators(MyClass)%          — class decorators
%source_link(MyClass)%          — source file:line
```

## children — Auto-Generated Child Nodes

In a `root.md` or `.md` file, use `children:` in front-matter to auto-generate child pages from source data:

```json
{
    "title": "Classes",
    "default_source_folder": "../../src",
    "children": {
        "classes": "{{classes}}"
    }
}
```

This creates one page per class in the source folder, at URLs like `/classes/DataFlowConfig.html`.

Mix manual and auto entries:

```json
{
    "children": {
        "classes": ["ManualClass", "{{classes}}", "AnotherClass"]
    }
}
```

## Cross-Links — `[[folder/Name]]`

Link to other documentation pages using double-bracket syntax:

```markdown
See [[api/DataFlowConfig]] for details.

[[DataFlow/BaseProcessor]] is the parent class.
```

Classes in `{{classes}}` are automatically cross-linked when used inline.

## Source Folder Inheritance

`default_source_folder` set in a `root.md` is inherited by:
- All `.md` files in the same folder
- All child folders (unless they override it)

```json
{
    // relative to the folder containing this root.md
    "default_source_folder": "../../src"
}
```

## Relaxed JSON Front-Matter

Front-matter supports relaxed JSON — no strict quoting rules:

```json
{
    title: "My Title",
    default_source_folder: "../../src",  // trailing comma OK
    // comments also work
}
```

Supported relaxations:
- Unquoted keys: `title: "value"` instead of `"title": "value"`
- `//` and `#` line comments
- Trailing commas

## CLI Commands

```bash
slop-doc init --name docs       # Create new docs folder
slop-doc build -d docs          # Build documentation
slop-doc open -d docs           # Open in browser
```

## Empty Folder Warning

Folders without `root.md` and without any `.md` files are **skipped** with a warning to stderr. This prevents build artifacts (like `build/`) from appearing in the navigation tree.

## Generated Output

Builds to `docs/build/` (configurable via `output_dir` in `root.md`):

```
build/
├── index.html
├── intro.html
├── api/
│   ├── index.html
│   ├── overview.html
│   └── DataFlowConfig.html   (auto-generated)
└── assets/
    ├── style.css
    └── search.js
```
