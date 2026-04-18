# CLI quickstart

Drive Niamoto from a shell. For the desktop path, read
[first-project.md](first-project.md).

## Prerequisites

- Install the CLI with [installation.md](installation.md).
- Open a terminal.
- Put your source files somewhere you can copy into the project.

## 1. Create a project

```bash
niamoto init my-project
cd my-project
export NIAMOTO_HOME="$PWD"
```

`niamoto init` writes the standard project tree:

```text
my-project/
├── config/
│   ├── config.yml
│   ├── import.yml
│   ├── transform.yml
│   └── export.yml
├── imports/
├── exports/
├── plugins/
├── templates/
├── db/
└── logs/
```

`niamoto init` also tries to open the GUI. Close it if you only want the CLI
scaffold.

## 2. Copy your source data

Put your raw files in `imports/`. A first project often starts with:

- one CSV or spreadsheet for observations
- one reference file for taxonomy, plots, or stations
- optional GeoPackage, shapefile, or raster layers

If you want sample data, use the repository linked from
[first-project.md](first-project.md).

## 3. Fill the config files

Open these files:

- `config/import.yml`
- `config/transform.yml`
- `config/export.yml`

`niamoto init` writes commented examples into each file. Start from those blocks
or copy a known-good config from an existing project.

Run `niamoto gui` once if you want the desktop interface to write the config
files, then come back to the CLI.

Keep these roles in mind:

- `import.yml` defines datasets and references
- `transform.yml` defines grouped outputs in `widgets_data`
- `export.yml` defines export targets, pages, and widgets

For the canonical shapes, use:

- [concepts.md](concepts.md)
- [../06-reference/configuration-guide.md](../06-reference/configuration-guide.md)
- [../03-cli-automation/README.md](../03-cli-automation/README.md)

## 4. Check the import config

```bash
niamoto import check
```

Use `niamoto import check --entity <name>` when you want to isolate one entity.

## 5. Run the pipeline

For a first pass, run each phase yourself:

```bash
niamoto import
niamoto transform
niamoto export
```

When the project looks stable, use the bundled command:

```bash
niamoto run --no-reset
```

`niamoto run` resets the environment by default. Use `--no-reset` unless you
want a clean rebuild.

## 6. Inspect the result

Check the database:

```bash
niamoto stats
```

Serve the generated site:

```bash
python -m http.server --directory exports/web 8000
```

Then open [http://localhost:8000](http://localhost:8000).

## 7. Deploy

When the exported site looks right, publish it with:

```bash
niamoto deploy
```

If you deploy often, store defaults in `config/deploy.yml`. See
[../03-cli-automation/README.md](../03-cli-automation/README.md).

## Next reads

- [../03-cli-automation/README.md](../03-cli-automation/README.md) for command
  patterns, `deploy.yml`, CI, and cron.
- [../06-reference/cli-commands.md](../06-reference/cli-commands.md) for the
  command reference.
- [../04-plugin-development/README.md](../04-plugin-development/README.md) if
  the built-in plugins stop short.
