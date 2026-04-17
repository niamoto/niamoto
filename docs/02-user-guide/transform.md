# Transform and Collection Configuration

Collections is where you edit transform-backed outputs:

- choose or inspect a collection
- configure widgets and transform-backed outputs
- preview results
- save configuration

## Entry points

- `src/niamoto/gui/ui/src/features/collections`
- `src/niamoto/gui/ui/src/components/widgets`
- `src/niamoto/gui/ui/src/lib/preview`

## Collections model

The GUI organizes transform work around collections such as:

- taxons
- plots
- shapes

For each collection, you work with:

- widget lists
- widget suggestions
- plugin-backed parameter forms
- preview panels

## Typical workflow

1. Open a collection
2. Add or edit a widget
3. Pick the transformer and widget pairing
4. Configure plugin parameters through generated forms
5. Preview the result
6. Save the configuration

## Related documents

- [Transform plugins reference](../06-reference/transform-plugins.md)
- [Widgets and transform workflow](../06-reference/widgets-and-transform-workflow.md)
- [GUI preview system](../07-architecture/gui-preview-system.md)
