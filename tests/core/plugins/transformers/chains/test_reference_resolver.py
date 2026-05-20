import pytest
import numpy as np

from niamoto.core.plugins.transformers.chains.reference_resolver import (
    ReferenceConfig,
    ReferenceResolver,
)


@pytest.fixture
def sample_context():
    """Provides a sample context dictionary for testing."""
    return {
        "step1": {
            "simple_string": "hello world",
            "simple_number": 123.45,
            "simple_list": [10, 20, 30],
            "mixed_list": [3, None, 1, 3, 2, None],
            "is_true": True,
            "is_null": None,
        },
        "precision": {"digits": 1},
        "step2": {
            "nested": {
                "key": "nested_value",
                "numbers": [100, 200],
            },
            "another_list": ["a", "b", "c"],
        },
        "step3": {"matrix": [[1, 2], [3, 4]]},
    }


class TestReferenceResolver:
    """Tests for the ReferenceResolver class."""

    @pytest.fixture(autouse=True)
    def setup_resolver(self, sample_context):
        """Initialize the resolver for each test."""
        self.resolver = ReferenceResolver(sample_context)
        self.context = sample_context  # Keep context for assertions

    # --- Basic Resolution Tests --- #

    def test_resolve_simple_string(self):
        assert (
            self.resolver.resolve("@step1.simple_string")
            == self.context["step1"]["simple_string"]
        )

    def test_resolve_simple_number(self):
        assert (
            self.resolver.resolve("@step1.simple_number")
            == self.context["step1"]["simple_number"]
        )

    def test_resolve_boolean(self):
        assert self.resolver.resolve("@step1.is_true") is True

    def test_resolve_none(self):
        assert self.resolver.resolve("@step1.is_null") is None

    def test_resolve_non_reference_string(self):
        assert self.resolver.resolve("not_a_reference") == "not_a_reference"

    def test_resolve_non_reference_other_types(self):
        assert self.resolver.resolve(123) == 123
        assert self.resolver.resolve([1, 2]) == [1, 2]
        assert self.resolver.resolve({"a": 1}) == {"a": 1}

    def test_resolve_dict_with_references(self):
        input_dict = {
            "key1": "@step1.simple_string",
            "key2": 500,
            "nested": {"sub_key": "@step2.nested.key"},
        }
        expected_dict = {
            "key1": self.context["step1"]["simple_string"],
            "key2": 500,
            "nested": {"sub_key": self.context["step2"]["nested"]["key"]},
        }
        assert self.resolver.resolve(input_dict) == expected_dict

    def test_resolve_list_with_references(self):
        input_list = ["@step1.simple_number", "literal", "@step2.another_list"]
        expected_list = [
            self.context["step1"]["simple_number"],
            "literal",
            self.context["step2"]["another_list"],
        ]
        assert self.resolver.resolve(input_list) == expected_list

    # --- Path Resolution Tests --- #

    def test_resolve_nested_dict_key(self):
        assert (
            self.resolver.resolve("@step2.nested.key")
            == self.context["step2"]["nested"]["key"]
        )

    def test_resolve_simple_list_index(self):
        assert (
            self.resolver.resolve("@step1.simple_list[1]")
            == self.context["step1"]["simple_list"][1]
        )  # Expect 20

    def test_resolve_nested_list_index(self):
        assert (
            self.resolver.resolve("@step3.matrix[0][1]")
            == self.context["step3"]["matrix"][0][1]
        )  # Expect 2

    def test_resolve_nested_dict_list_index(self):
        assert (
            self.resolver.resolve("@step2.nested.numbers[0]")
            == self.context["step2"]["nested"]["numbers"][0]
        )  # Expect 100

    # --- Function Application Tests (Basic) --- #

    def test_resolve_function_len(self):
        assert self.resolver.resolve("@step1.simple_list|length") == len(
            self.context["step1"]["simple_list"]
        )

    def test_resolve_function_sum(self):
        assert self.resolver.resolve("@step1.simple_list|sum") == sum(
            self.context["step1"]["simple_list"]
        )

    def test_resolve_function_mean(self):
        assert self.resolver.resolve("@step1.simple_list|mean") == np.mean(
            self.context["step1"]["simple_list"]
        )

    def test_resolve_function_first(self):
        assert (
            self.resolver.resolve("@step2.another_list|first")
            == self.context["step2"]["another_list"][0]
        )

    def test_resolve_function_last(self):
        assert (
            self.resolver.resolve("@step2.another_list|last")
            == self.context["step2"]["another_list"][-1]
        )

    def test_resolve_function_int(self):
        assert self.resolver.resolve("@step1.simple_number|int") == int(
            self.context["step1"]["simple_number"]
        )

    def test_resolve_function_str(self):
        assert self.resolver.resolve("@step1.simple_number|str") == str(
            self.context["step1"]["simple_number"]
        )

    def test_resolve_function_with_literal_argument(self):
        assert self.resolver.resolve("@step1.simple_number|round(1)") == 123.5

    def test_resolve_function_with_reference_argument(self):
        assert (
            self.resolver.resolve("@step1.simple_number|round(@precision.digits)")
            == 123.5
        )

    def test_resolve_function_unique(self):
        assert set(self.resolver.resolve("@step1.mixed_list|unique")) == {
            1,
            2,
            3,
            None,
        }

    def test_resolve_function_sort(self):
        assert self.resolver.resolve("@step1.simple_list|sort") == [10, 20, 30]

    def test_resolve_function_reverse(self):
        assert self.resolver.resolve("@step1.simple_list|reverse") == [30, 20, 10]

    def test_resolve_function_filter_null(self):
        assert self.resolver.resolve("@step1.mixed_list|filter_null") == [3, 1, 3, 2]

    def test_allowed_functions_restricts_function_application(self):
        resolver = ReferenceResolver(
            self.context,
            ReferenceConfig(allowed_functions=["length"]),
        )

        assert resolver.resolve("@step1.simple_list|length") == 3
        with pytest.raises(ValueError, match="Function 'sum' is not allowed"):
            resolver.resolve("@step1.simple_list|sum")

    def test_empty_allowed_functions_denies_all_functions(self):
        resolver = ReferenceResolver(
            self.context,
            ReferenceConfig(allowed_functions=[]),
        )

        with pytest.raises(ValueError, match="Function 'length' is not allowed"):
            resolver.resolve("@step1.simple_list|length")

    def test_allowed_functions_does_not_block_plain_references(self):
        resolver = ReferenceResolver(
            self.context,
            ReferenceConfig(allowed_functions=[]),
        )

        assert resolver.resolve("@step1.simple_number") == 123.45

    # --- Error Handling Tests (Basic) --- #

    def test_error_invalid_format_missing_dot(self):
        with pytest.raises(ValueError, match="Invalid reference format"):
            self.resolver.resolve("@step1")

    def test_error_step_not_found(self):
        with pytest.raises(ValueError, match="Step 'invalid_step' not found"):
            self.resolver.resolve("@invalid_step.field")

    def test_error_field_not_found(self):
        with pytest.raises(ValueError, match="Field 'invalid_field' not found"):
            self.resolver.resolve("@step1.invalid_field")

    def test_error_index_out_of_bounds(self):
        # Match the beginning of the error message, ignoring potential suffixes like 'on list'
        with pytest.raises(
            ValueError, match=r"Invalid index access '\[5\]': Index 5 out of bounds"
        ):
            self.resolver.resolve("@step1.simple_list[5]")

    def test_error_invalid_index_type(self):
        # Correct the regex escaping for literal brackets and include single quotes
        with pytest.raises(ValueError, match=r"Invalid index format: '\[abc\]'"):
            self.resolver.resolve("@step1.simple_list[abc]")

    def test_error_function_not_found(self):
        with pytest.raises(ValueError, match="Function 'invalid_func' not found"):
            self.resolver.resolve("@step1.simple_string|invalid_func")

    def test_error_indexing_non_list_value(self):
        with pytest.raises(ValueError, match="Invalid index access '\\[0\\]'.*str"):
            self.resolver.resolve("@step1.simple_string[0]")

    def test_error_function_argument_count(self):
        with pytest.raises(TypeError):
            self.resolver.resolve("@step1.simple_number|int(10)")

    def test_error_function_argument_type(self):
        with pytest.raises(TypeError):
            self.resolver.resolve("@step1.simple_string|round(1)")
