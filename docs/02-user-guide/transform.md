# Transform and Group Configuration

In the current GUI, the transform workflow is primarily expressed through group configuration rather than through a visual pipeline canvas.

The practical unit of work is the group:

- choose or inspect a group
- configure widgets and transform-backed outputs
- preview results
- save configuration

## Main entry points

- [`src/niamoto/gui/ui/src/features/groups`](../../src/niamoto/gui/ui/src/features/groups)
- [`src/niamoto/gui/ui/src/components/widgets`](../../src/niamoto/gui/ui/src/components/widgets)
- [`src/niamoto/gui/ui/src/lib/preview`](../../src/niamoto/gui/ui/src/lib/preview)

## Current model

The GUI is centered on configuring transform-backed widgets for aggregation groups such as:

- taxons
- plots
- shapes

Instead of building a freeform node graph, the user works with:

- widget lists
- widget suggestions
- plugin-backed parameter forms
- preview panels

## Typical workflow

1. Open a group
2. Add or edit a widget
3. Select a transformer and widget pairing
4. Configure plugin parameters through generated forms
5. Preview the result
6. Save the configuration

## What this documentation does not describe

Some older documents described a future “visual transform pipeline builder” with:

- drag-and-drop nodes
- connection graphs
- canvas-based orchestration

That is not the current GUI model and should be treated as historical design exploration rather than current implementation.

## Related documents

- [Transform plugins reference](../06-reference/transform-plugins.md)
- [Widgets and transform workflow](../06-reference/widgets-and-transform-workflow.md)
- [GUI preview system](../09-architecture/gui-preview-system.md)
