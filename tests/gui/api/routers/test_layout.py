"""
Tests for layout API endpoints.

These tests ensure that the layout endpoints work correctly
and prevent regressions when calling internal functions.
"""

import inspect


class TestPreviewTemplateCompatibility:
    """
    Tests to verify preview_template function signature compatibility.

    These tests help catch breaking changes in the function signature
    and ensure layout.preview_widget correctly calls preview_template.
    """

    def test_preview_template_accepts_source_parameter(self):
        """Verify preview_template accepts source as keyword argument."""
        from niamoto.gui.api.routers.templates import preview_template

        sig = inspect.signature(preview_template)
        params = list(sig.parameters.keys())

        # Verify expected parameters exist
        assert "template_id" in params, "Missing template_id parameter"
        assert "group_by" in params, "Missing group_by parameter"
        assert "entity_id" in params, "Missing entity_id parameter"
        assert "source" in params, "Missing source parameter"

    def test_preview_template_source_has_default(self):
        """Verify source parameter has a default value."""
        from niamoto.gui.api.routers.templates import preview_template

        sig = inspect.signature(preview_template)
        source_param = sig.parameters.get("source")

        assert source_param is not None, "source parameter not found"
        assert source_param.default != inspect.Parameter.empty, (
            "source parameter must have a default value"
        )

    def test_layout_calls_preview_with_source_parameter(self):
        """
        Verify that layout.preview_widget calls preview_template with source parameter.

        Regression test: When preview_template added a new 'source' parameter
        with Query(default=None), the layout router was not updated. This caused
        Pydantic validation errors like:
        'params.source Input should be a valid string [type=string_type,
        input_value=Query(None)]'

        The fix requires passing source=None explicitly because Query() defaults
        don't work when calling FastAPI endpoint functions directly from Python.

        This test inspects the source code to verify source is passed.
        """
        from niamoto.gui.api.routers import layout

        source_code = inspect.getsource(layout.preview_widget)

        # The call should include source=None
        assert "source=None" in source_code, (
            "preview_widget must pass source=None explicitly to preview_template"
        )

    def test_layout_preview_widget_signature(self):
        """Verify preview_widget has expected signature."""
        from niamoto.gui.api.routers.layout import preview_widget

        sig = inspect.signature(preview_widget)
        params = list(sig.parameters.keys())

        assert "group_by" in params, "Missing group_by parameter"
        assert "widget_index" in params, "Missing widget_index parameter"
        assert "entity_id" in params, "Missing entity_id parameter"


class TestPreviewTemplateSignatureSync:
    """
    Tests to ensure layout and templates routers stay in sync.

    When preview_template signature changes, these tests help catch
    missing updates in layout.preview_widget.
    """

    def test_all_preview_template_params_are_handled(self):
        """
        Verify that all preview_template parameters are either:
        1. Passed explicitly by layout.preview_widget
        2. Have default values (Query with default)

        This prevents regressions when new parameters are added.
        """
        from niamoto.gui.api.routers.templates import preview_template
        from niamoto.gui.api.routers import layout

        preview_sig = inspect.signature(preview_template)
        layout_source = inspect.getsource(layout.preview_widget)

        # Get all preview_template parameters
        for param_name, param in preview_sig.parameters.items():
            if param_name in ("template_id", "request"):
                # template_id: first positional arg, always passed
                # request: injecté automatiquement par FastAPI
                continue

            # Parameter must either be passed explicitly or have a default
            has_default = param.default != inspect.Parameter.empty
            is_passed = f"{param_name}=" in layout_source

            assert has_default or is_passed, (
                f"Parameter '{param_name}' of preview_template is not passed by "
                f"layout.preview_widget and has no default. This will cause "
                f"validation errors when calling preview_template directly."
            )
