# Niamoto Transform Chain System

## Table of Contents

1. [Introduction](#introduction)
2. [Transform Chain Concept](#transform-chain-concept)
3. [Configuration Syntax](#configuration-syntax)
4. [Reference Resolution System](#reference-resolution-system)
5. [Available Functions](#available-functions)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Introduction

The Transform Chain system in Niamoto provides a powerful way to create complex data transformations by connecting multiple plugins in a sequence. This allows you to build sophisticated data processing pipelines without writing custom code.

## Transform Chain Concept

In Niamoto, a transform chain is a series of transformation steps where:

- Each step uses a transformation plugin
- The output of one step can be used as input to subsequent steps
- References between steps are resolved automatically
- The final output combines results from all steps

This approach offers several advantages:

- Reusability of transformation components
- Clarity in data flow
- Complex transformations without custom coding
- Clear visualization of the data processing pipeline

## Configuration Syntax

Transform chains are defined in the `transform.yml` file using the `transform_chain` plugin:

```yaml
widget_name:
  plugin: "transform_chain"
  params:
    steps:
      - plugin: "plugin_name"
        params:
          # Plugin-specific parameters
          param1: value1
          param2: value2
        output_key: "step_result_name"

      - plugin: "another_plugin"
        params:
          # Can reference previous step results with @ syntax
          input_param: "@step_result_name.field"
        output_key: "another_result"

      # Additional steps...
```

### Key Components

- **plugin**: The `transform_chain` plugin name
- **params.steps**: Array of transformation steps
- For each step:
  - **plugin**: The transformation plugin to use
  - **params**: Plugin-specific parameters
  - **output_key**: Name under which to store the step's output

## Reference Resolution System

One of the most powerful features of the transform chain is the ability to reference results from previous steps using the `@` syntax.

### Basic References

```yaml
input_param: "@step_name.field"
```

This references the `field` property of the result stored in `step_name`.

### Nested References

```yaml
nested_param: "@step_name.field.subfield"
```

References can navigate through nested structures.

### Array Indexing

```yaml
array_item: "@step_name.array[0]"
```

You can access specific array elements using square bracket notation.

### Function Application

```yaml
transformed_value: "@step_name.field|function(args)"
```

This applies a function to the referenced value.

## Available Functions

The reference system includes several built-in functions that can be applied to referenced values:

### Math Functions

- **sum**: Sum all values in a list
- **mean**: Calculate the average of values
- **max**: Find the maximum value
- **min**: Find the minimum value
- **abs**: Absolute value
- **round**: Round a number

### List Functions

- **length**: Get the length of a list
- **first**: Get the first element
- **last**: Get the last element
- **filter_null**: Remove null values

### Type Conversions

- **int**: Convert to integer
- **float**: Convert to float
- **str**: Convert to string
- **bool**: Convert to boolean

### Data Processing

- **unique**: Get unique values from a list
- **sort**: Sort a list
- **reverse**: Reverse a list

## Examples

### Phenology Analysis Example

This example shows a complete transform chain for analyzing phenology data:

```yaml
phenology:
  plugin: "transform_chain"
  params:
    steps:
      # Step 1: Extract time series data
      - plugin: "time_series_analysis"
        params:
          source: occurrences
          fields:
            fleur: flower
            fruit: fruit
          time_field: month_obs
          labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        output_key: "phenology_raw"

      # Step 2: Detect flowering/fruiting peaks
      - plugin: "custom_calculator"
        params:
          operation: "peak_detection"
          time_series: "@phenology_raw.month_data"
          threshold: 30
        output_key: "phenology_peaks"

      # Step 3: Calculate active periods
      - plugin: "custom_calculator"
        params:
          operation: "active_periods"
          time_series: "@phenology_raw.month_data"
          labels: "@phenology_raw.labels"
        output_key: "phenology_periods"

      # Step 4: Combine all results
      - plugin: "custom_calculator"
        params:
          operation: "custom_formula"
          formula: "{'raw': phenology_raw, 'peaks': phenology_peaks, 'periods': phenology_periods}"
          variables:
            phenology_raw: "@phenology_raw"
            phenology_peaks: "@phenology_peaks"
            phenology_periods: "@phenology_periods"
        output_key: "phenology_data"
```

In this example:

1. First, we extract time series data for flowering and fruiting by month
2. Next, we detect significant peaks in the data
3. Then, we identify active periods of flowering/fruiting
4. Finally, we combine all results into a single structured output

### Geospatial Analysis Example

```yaml
habitat_analysis:
  plugin: "transform_chain"
  params:
    steps:
      - plugin: "geospatial_extractor"
        params:
          source: occurrences
          field: geo_pt
          format: geojson
        output_key: "occurrence_points"

      - plugin: "vector_overlay"
        params:
          source: "@occurrence_points"
          overlay_layer: "forest_cover"
        output_key: "forest_intersection"

      - plugin: "statistical_summary"
        params:
          source: "@forest_intersection.intersection_data"
          field: "area"
          stats: ["sum", "mean"]
        output_key: "forest_stats"
```

This example analyzes habitat preferences:

1. First, it extracts occurrence points
2. Then it overlays these points with a forest cover layer
3. Finally, it calculates statistics about the intersection

## Best Practices

1. **Logical step organization**:
   - Organize steps in a logical sequence
   - Use descriptive output_key names

2. **Reference clarity**:
   - Keep references as simple as possible
   - Use direct field access rather than nested paths when possible

3. **Error handling**:
   - Validate inputs before processing
   - Check for edge cases (empty data, missing fields)

4. **Performance**:
   - Consider data volume when chaining transformations
   - Process/filter data early in the chain to reduce overhead

5. **Maintainability**:
   - Use comments to describe complex transformations
   - Split very complex chains into multiple smaller chains

## Troubleshooting

Common issues with transform chains include:

### Reference Errors

If you see errors like `Field 'X' not found in step 'Y'`:

- Check that the step name in the reference is correct
- Verify that the previous step produced the expected output structure
- Make sure the field paths are correct

### Type Errors

If function application fails:

- Check that the referenced value is of the correct type for the function
- Use transformation functions to convert types if needed

### Plugin Errors

If step execution fails:

- Check plugin-specific parameter requirements
- Ensure required input data is available
- Look at detailed error messages for specific plugin requirements

### Debugging Tips

- Use temporary output steps to inspect intermediate data
- Add simple processing steps to verify data structure
- Check for null values or empty collections that might cause issues in later steps
