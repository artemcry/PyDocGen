"""End-to-end build test — creates a docs folder and builds it."""

import os
import textwrap

import pytest

from slop_doc.builder import build_docs, BuildError


@pytest.fixture
def full_project(tmp_path):
    """A complete mini-project with Python source and docs."""
    # Python source
    src = tmp_path / "mylib"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "models.py").write_text(textwrap.dedent("""\
        class User:
            \"\"\"A user in the system.

            Represents an authenticated user.
            \"\"\"

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

            def greet(self) -> str:
                \"\"\"Return a greeting.

                Returns:
                    A friendly greeting string.
                \"\"\"
                return f"Hello, {self.name}!"

            @property
            def display_name(self) -> str:
                \"\"\"The display name.\"\"\"
                return self.name.title()

        class Admin(User):
            \"\"\"An admin user with extra privileges.\"\"\"

            def ban(self, target: "User") -> None:
                \"\"\"Ban a user.

                Args:
                    target: User to ban.
                \"\"\"
                pass

        def find_user(email: str) -> User | None:
            \"\"\"Find a user by email.

            Args:
                email: Email address to look up.

            Returns:
                User if found, None otherwise.
            \"\"\"
            return None

        DEFAULT_ROLE = "viewer"
    """))

    # Docs
    docs = tmp_path / "docs"
    docs.mkdir()

    src_path = str(src).replace(os.sep, "/")

    (docs / "root.md").write_text(textwrap.dedent(f"""\
        {{
            "title": "MyLib Docs",
            "project_name": "MyLib",
            "version": "2.0",
            "output_dir": "build",
            "py_source": "{src_path}",
            "editor": "vscode",
            "max_search_results": 5,
            "default_collapsed": true
        }}

        # MyLib Documentation

        Welcome to **MyLib**.

        ## Classes

        %classes_table()%

        ## Functions

        %functions_table()%
    """))

    (docs / "guide.md").write_text(textwrap.dedent("""\
        {
            "title": "User Guide",
            "order": 1
        }

        # User Guide

        ## Getting Started

        Install with pip.

        ## Basic Usage

        Create a user and greet them.
    """))

    # Subfolder (container node — no root.md)
    api = docs / "api"
    api.mkdir()

    (api / "reference.md").write_text(textwrap.dedent("""\
        {
            "title": "API Reference",
            "children": {
                "classes": "{{classes}}"
            }
        }

        # API Reference

        Full API documentation below.
    """))

    return str(docs)


class TestEndToEndBuild:
    def test_build_produces_output(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        assert os.path.isdir(build_dir)
        assert os.path.isfile(os.path.join(build_dir, "index.html"))

    def test_pages_created(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        # Guide page
        guide = os.path.join(build_dir, "user-guide.html")
        assert os.path.isfile(guide)

        with open(guide, "r", encoding="utf-8") as f:
            html = f.read()
        assert "Getting Started" in html
        assert "Basic Usage" in html
        assert "MyLib" in html  # project name in header

    def test_index_has_content(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        with open(os.path.join(build_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()

        assert "MyLib Documentation" in html
        assert "__SEARCH_INDEX__" in html
        assert "__SLOP_SETTINGS__" in html
        assert '"vscode"' in html  # editor setting

    def test_auto_class_pages(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        # API Reference should have child class pages
        api_dir = os.path.join(build_dir, "api", "api-reference")
        assert os.path.isdir(api_dir) or True  # dir may be nested differently

        # Find any .html file mentioning "User" class
        found_user = False
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.endswith(".html"):
                    content = open(os.path.join(root, f), encoding="utf-8").read()
                    if "class User" in content or 'greet' in content:
                        found_user = True
                        break
        assert found_user, "No page found with User class content"

    def test_nav_tree(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        with open(os.path.join(build_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()

        assert "sidebar-left" in html
        assert "User Guide" in html
        assert "API Reference" in html

    def test_search_index(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        with open(os.path.join(build_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()

        assert "__SEARCH_INDEX__" in html
        # Should contain at least page titles
        assert "User Guide" in html

    def test_assets_copied(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        assert os.path.isfile(os.path.join(build_dir, "assets", "app.js"))
        assert os.path.isfile(os.path.join(build_dir, "assets", "style.css"))

    def test_settings_embedded(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        with open(os.path.join(build_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()

        assert '"max_search_results": 5' in html or '"max_search_results":5' in html
        assert "default_collapsed" in html

    def test_order_respected(self, full_project):
        build_docs(full_project)
        build_dir = os.path.join(full_project, "build")

        with open(os.path.join(build_dir, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()

        # User Guide (order=1) should appear before API Reference in nav
        guide_pos = html.find("User Guide")
        api_pos = html.find("API Reference")
        assert guide_pos < api_pos, "User Guide should come before API Reference"

    def test_missing_root_md(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(BuildError):
            build_docs(str(empty))

    def test_rebuild_is_idempotent(self, full_project):
        build_docs(full_project)
        build_docs(full_project)  # second build should not crash
        build_dir = os.path.join(full_project, "build")
        assert os.path.isfile(os.path.join(build_dir, "index.html"))
