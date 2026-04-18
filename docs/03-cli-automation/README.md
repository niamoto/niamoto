# CLI & Automation

Run this path when you want the Niamoto pipeline from a shell, CI job, or
server.

## Start here

- `niamoto --help` shows the top-level command map.
- The CLI covers `init`, `import`, `transform`, `export`, `deploy`, `run`,
  `stats`, `plugins`, `optimize`, and `gui`.
- Repeated deployments can read defaults from `config/deploy.yml`.

## Main commands

- `niamoto init`: create or reset a project.
- `niamoto import`: import the entities defined in `import.yml`.
- `niamoto transform`: compute grouped outputs from `transform.yml`.
- `niamoto export`: run the targets defined in `export.yml`.
- `niamoto deploy`: publish an exported site to a configured platform.
- `niamoto run`: chain import, transform, and export in one command.
- `niamoto stats`: inspect the current project database.
- `niamoto plugins`: list installed plugins.
- `niamoto optimize`: compact and optimize the database.
- `niamoto gui`: launch the visual interface for the active project.

## Common workflows

### Initialize a project

```bash
niamoto init my-project --gui
```

This creates the project tree, writes the default config files, and opens the
GUI if you asked for it.

### Refresh a project from the shell

```bash
export NIAMOTO_HOME=/path/to/my-project
niamoto import
niamoto transform
niamoto export
```

Use this for an explicit step-by-step run in CI or on a server.

### Run the bundled pipeline safely

```bash
export NIAMOTO_HOME=/path/to/my-project
niamoto run --no-reset
```

`niamoto run` resets the environment by default. In automation, prefer
`--no-reset` unless you want a clean rebuild.

### Inspect configuration drift before importing

```bash
export NIAMOTO_HOME=/path/to/my-project
niamoto import check
niamoto import check --entity occurrences
```

This compares source files and current configuration before a full import.

### Deploy a generated site

```bash
niamoto deploy platforms
niamoto deploy -p github --project my-site -e repo org/my-site
```

Supported platforms today are:

- `cloudflare`
- `github`
- `netlify`
- `vercel`
- `render`
- `ssh`

## `config/deploy.yml`

Store repeated deployment defaults in `config/deploy.yml`.

Minimal example:

```yaml
platform: github
project_name: my-site
branch: gh-pages
extra:
  repo: org/my-site
```

Then deployment becomes:

```bash
export NIAMOTO_HOME=/path/to/my-project
niamoto deploy
```

The deploy command reads `platform`, `project_name`, `branch`, and `extra` from
that file. CLI flags override them.

## CI and cron

- Set `NIAMOTO_HOME` to the project root before calling the CLI.
- Prefer explicit phases or `niamoto run --no-reset` for unattended jobs.
- Keep deploy credentials on the runner or host with
  `niamoto deploy credentials ...`.
- Use `niamoto stats` and `niamoto import check` when you need a quick health
  gate before a full run.

## Also useful

- Use the desktop app instead: [../02-user-guide/README.md](../02-user-guide/README.md)
- Find the current CLI surface quickly: [../06-reference/cli-commands.md](../06-reference/cli-commands.md)
- Understand the underlying schemas: [../06-reference/README.md](../06-reference/README.md)

## Related

- [../06-reference/README.md](../06-reference/README.md): canonical references.
- [../06-reference/cli-commands.md](../06-reference/cli-commands.md): compact command reference.
- [../09-troubleshooting/README.md](../09-troubleshooting/README.md): common issues.
