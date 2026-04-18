# Niamoto core concepts

Niamoto runs one pipeline through three config files:

```text
import.yml    -> load raw data
transform.yml -> compute grouped outputs
export.yml    -> render pages or APIs
```

The desktop app edits the same project files as the CLI. The interface changes.
The project model does not.

## 1. Project layout

When you run `niamoto init`, Niamoto creates this tree:

```text
config/
imports/
exports/
plugins/
templates/
db/
logs/
```

`config.yml` points to the database, output directories, templates, and plugins.

## 2. Import

`import.yml` defines the raw entities that enter the project database.

You usually split them into:

- `datasets` for observations, measurements, and other raw rows
- `references` for taxonomy, plots, shapes, or classification tables

For each entity, you tell Niamoto:

- where the source lives
- which fields to load
- how datasets link to references

That import step gives the rest of the pipeline a stable project database.

## 3. Transform

`transform.yml` is a list of groups. Each group picks one `group_by` entity and
computes outputs for that entity in `widgets_data`.

- `group_by` says which entity owns the output rows
- `sources` define the extra data each group can read
- `widgets_data` runs transformer plugins and stores their results

Those results become the inputs for HTML widgets, JSON exports, previews, and
other tooling.

## 4. Export

`export.yml` defines an `exports:` list. Each target picks one exporter.

The two common cases are:

- `html_page_exporter` for a static website
- `json_api_exporter` for API files

An HTML target usually contains:

- `params` for site settings, template paths, navigation, and assets
- optional `static_pages`
- `groups` for detail pages and index pages

Each `groups[*].widgets` entry points at a `data_source` that came from
`transform.yml`.

## 5. Plugins

Plugins extend each stage of the pipeline.

Niamoto registers five families:

- loaders
- transformers
- widgets
- exporters
- deployers

Use built-in plugins first. Write your own plugin when the stock ones stop
short.

## 6. Templates and widgets

Templates control page layout. Put overrides in `templates/`.

Widgets do a different job. A widget plugin reads transformed data and returns
HTML for one block inside a page. You configure the widget in `export.yml` with:

- `plugin`
- `data_source`
- `title`
- `description`
- `params`
- `layout`

If you want to change page structure, edit templates. If you want a new data
block, edit widgets.

## 7. Desktop app and CLI

The desktop app and the CLI touch the same project.

Use the desktop app when you want:

- import assistance
- previews
- page composition
- guided deploy setup

Use the CLI when you want:

- repeatable runs
- CI or cron jobs
- scripted deploys
- versioned config changes

You can switch between them at any point.

## 8. A normal project loop

Most projects follow this loop:

1. Copy raw files into `imports/`.
2. Fill `import.yml`.
3. Run `niamoto import`.
4. Fill `transform.yml`.
5. Run `niamoto transform`.
6. Fill `export.yml`.
7. Run `niamoto export`.
8. Publish with `niamoto deploy` when the site looks right.

For repeated runs, many teams use `niamoto run --no-reset`.

## Next reads

- [quickstart.md](quickstart.md) for the shell workflow
- [../03-cli-automation/README.md](../03-cli-automation/README.md) for command
  patterns and deployment
- [../06-reference/configuration-guide.md](../06-reference/configuration-guide.md)
  for schema details
- [../04-plugin-development/README.md](../04-plugin-development/README.md) for
  custom plugins
