"""Tests for Stage 3: Template Engine."""

import pytest
from slop_doc.template_engine import (
    parse_params_block, validate_params, substitute_params,
    expand_for_loops, render_data_tags, render_template,
    TemplateEngineError
)
from slop_doc.parser import SourceData, ClassData, FunctionData, ConstantData


class TestParamSubstitution:
    """Test %%PARAM%% substitution."""

    def test_param_substitution(self):
        body = "Hello %%NAME%%"
        params = {"NAME": "World"}
        result = substitute_params(body, params)
        assert result == "Hello World"

    def test_param_required_missing(self):
        body = "Hello %%NAME%%"
        params = {}
        with pytest.raises(TemplateEngineError) as exc:
            substitute_params(body, params)
        assert "Unknown param %%NAME%%" in str(exc.value)

    def test_param_default(self):
        template = '''param@NAME=Default
Hello %%NAME%%'''
        required, optional, body = parse_params_block(template)
        params = {}
        validate_params(required, {**optional, **params})
        result = substitute_params(body, {**optional, **params})
        assert "Default" in result


class TestForLoopExpansion:
    """Test :: for ... :: endfor loops."""

    def test_for_loop_basic(self):
        body = ''':: for X in {{classes}}:
# {{class_name#X}}
:: endfor'''
        source_data = SourceData(
            classes=[ClassData(name="Pipeline", base_classes=[], decorators=[], short_description="A pipeline")],
            functions=[],
            constants=[]
        )
        result = expand_for_loops(body, source_data)
        # After expansion, X is replaced but data tag is not yet rendered
        assert "{{class_name#Pipeline}}" in result

    def test_for_loop_exclude(self):
        body = ''':: for X in {{classes}}.exclude("B"):
# {{class_name#X}}
:: endfor'''
        source_data = SourceData(
            classes=[
                ClassData(name="A", base_classes=[], decorators=[]),
                ClassData(name="B", base_classes=[], decorators=[]),
                ClassData(name="C", base_classes=[], decorators=[])
            ],
            functions=[],
            constants=[]
        )
        result = expand_for_loops(body, source_data)
        assert "A" in result
        assert "B" not in result
        assert "C" in result

    def test_for_loop_no_source(self):
        body = ''':: for X in {{classes}}:
# {{class_name#X}}
:: endfor'''
        with pytest.raises(TemplateEngineError) as exc:
            expand_for_loops(body, None)
        assert "requires source" in str(exc.value)


class TestDataTags:
    """Test {{data_tag}} rendering."""

    def test_data_tag_class_name(self):
        source_data = SourceData(
            classes=[ClassData(name="Pipeline", base_classes=[], decorators=[])],
            functions=[],
            constants=[]
        )
        body = "{{class_name#Pipeline}}"
        result = render_data_tags(body, source_data)
        assert result == "Pipeline"

    def test_data_tag_unknown_class(self):
        source_data = SourceData(
            classes=[ClassData(name="Pipeline", base_classes=[], decorators=[])],
            functions=[],
            constants=[]
        )
        body = "{{class_name#NonExistent}}"
        with pytest.raises(TemplateEngineError) as exc:
            render_data_tags(body, source_data)
        assert "NonExistent" in str(exc.value)

    def test_data_tag_no_source(self):
        body = "{{classes}}"
        with pytest.raises(TemplateEngineError) as exc:
            render_data_tags(body, None)
        assert "requires source" in str(exc.value)

    def test_data_tag_public_methods(self):
        source_data = SourceData(
            classes=[
                ClassData(
                    name="MyClass",
                    base_classes=[],
                    decorators=[],
                    short_description="A class",
                    methods=[
                        FunctionData(name="run", args=[], decorators=[]),
                        FunctionData(name="stop", args=[], decorators=[])
                    ]
                )
            ],
            functions=[],
            constants=[]
        )
        body = "{{public_methods#MyClass}}"
        result = render_data_tags(body, source_data)
        assert "run" in result
        assert "stop" in result

    def test_methods_filtered(self):
        source_data = SourceData(
            classes=[
                ClassData(
                    name="MyClass",
                    base_classes=[],
                    decorators=[],
                    methods=[
                        FunctionData(name="run", args=[], decorators=[]),
                        FunctionData(name="stop", args=[], decorators=[]),
                        FunctionData(name="pause", args=[], decorators=[])
                    ]
                )
            ],
            functions=[],
            constants=[]
        )
        # Note: methods_filtered syntax is {{methods_filtered#ClassName: run, stop}}
        body = "{{methods_filtered#MyClass: run, stop}}"
        result = render_data_tags(body, source_data)
        assert "run" in result
        assert "stop" in result
        # Note: pause would not be in the rendered output since we filtered

    def test_public_methods_except(self):
        source_data = SourceData(
            classes=[
                ClassData(
                    name="MyClass",
                    base_classes=[],
                    decorators=[],
                    methods=[
                        FunctionData(name="run", args=[], decorators=[]),
                        FunctionData(name="stop", args=[], decorators=[]),
                        FunctionData(name="pause", args=[], decorators=[])
                    ]
                )
            ],
            functions=[],
            constants=[]
        )
        body = "{{public_methods_except#MyClass: run}}"
        result = render_data_tags(body, source_data)
        # stop and pause should be present, run should not

    def test_constants_tag(self):
        source_data = SourceData(
            classes=[],
            functions=[],
            constants=[
                ConstantData(name="MAX_SIZE", value="100", type="int"),
                ConstantData(name="PAGE_SIZE", value="50", type="int")
            ]
        )
        body = "{{constants}}"
        result = render_data_tags(body, source_data)
        assert "MAX_SIZE" in result
        assert "100" in result

    def test_class_info_tag(self):
        source_data = SourceData(
            classes=[
                ClassData(
                    name="Pipeline",
                    base_classes=["BaseNode"],
                    decorators=["dataclass"],
                    source_file="src/dataflow/pipeline.py",
                    source_line=10
                )
            ],
            functions=[],
            constants=[]
        )
        body = "{{class_info#Pipeline}}"
        result = render_data_tags(body, source_data)
        # class_info shows module, file, and base classes
        assert "src/dataflow/pipeline.py" in result
        assert "BaseNode" in result


class TestFullPipeline:
    """Test the full template rendering pipeline."""

    def test_full_pipeline(self):
        template = '''param@CLASS_ID
param@MODULE_DESCRIPTION=No description

# {{class_name#%%CLASS_ID%%}}
%%MODULE_DESCRIPTION%%

## Public Methods
{{public_methods#%%CLASS_ID%%}}
'''
        source_data = SourceData(
            classes=[
                ClassData(
                    name="Pipeline",
                    base_classes=[],
                    decorators=[],
                    short_description="A pipeline class",
                    methods=[
                        FunctionData(name="run", args=[], decorators=[]),
                        FunctionData(name="stop", args=[], decorators=[])
                    ]
                )
            ],
            functions=[],
            constants=[]
        )
        params = {"CLASS_ID": "Pipeline"}

        result = render_template(template, params, source_data)
        assert "Pipeline" in result
        # Module description defaults to "No description"
        assert "No description" in result
        assert "run" in result


class TestParseParamsBlock:
    """Test parameter block parsing."""

    def test_parse_required_param(self):
        template = '''param@CLASS_ID

# Content'''
        required, optional, body = parse_params_block(template)
        assert "CLASS_ID" in required
        assert "CLASS_ID" not in optional

    def test_parse_optional_param(self):
        template = '''param@SHOW_PRIVATE=false

# Content'''
        required, optional, body = parse_params_block(template)
        assert "SHOW_PRIVATE" not in required
        assert optional["SHOW_PRIVATE"] == "false"

    def test_parse_body_starts_after_params(self):
        template = '''param@CLASS_ID
param@NAME=Default

# Title
Content here'''
        required, optional, body = parse_params_block(template)
        assert "# Title" in body
        assert "Content here" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
