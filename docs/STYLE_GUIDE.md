# Niamoto Documentation Style Guide

The public docs and the README share one voice. This guide keeps them
consistent, readable, and free from AI-slop boilerplate.

## Voice

- **Concrete over abstract.** Describe what the software does, not what
  it "enables" or "empowers".
- **Short sentences.** If a sentence runs over three clauses, split it.
- **Active verbs, subject first.** "The import screen detects column
  types" beats "Column types are detected by the import screen".
- **Claim-then-evidence.** Lead with the outcome; follow with the
  mechanism or example.
- **No marketing pathos.** No "game-changing", "revolutionary",
  "cutting-edge".

## Banned vocabulary

These words are either hollow, hype-y, or typical AI-slop. Do not use
them in the docs or the README.

| Banned | Why | Replace with |
|--------|-----|--------------|
| seamlessly | Hollow adverb, almost always removable. | (delete) |
| leveraging | Corporate filler. | using / with |
| delve into | Classic AI tell. | see / read / look at |
| comprehensive | Hollow superlative. | complete / full |
| robust | Hollow. | stable / tested / reliable (with evidence) |
| powerful | Marketing filler. | (delete or describe what it does) |
| elegantly | Hollow. | (delete) |
| unlock | Marketing. | enable / let you / provide |
| empower | Corporate filler. | let / help |
| in today's fast-paced world | Filler intro. | (delete) |
| it's worth noting that | Throat-clearing. | (delete — just make the point) |
| moreover | Essay filler. | also / and |
| furthermore | Essay filler. | also / and |
| in conclusion | Weak ending. | (delete — end with the point) |
| navigate the complexities of | Filler. | handle / work with |
| game-changing | Hype. | (delete) |
| revolutionary | Hype. | (delete) |
| cutting-edge | Hype. | (delete — describe what is new) |
| best-in-class | Hype. | (delete) |
| world-class | Hype. | (delete) |
| ecosystem of | Cliché. | set / suite / collection (if needed) |
| journey | Cliché. | workflow / process / path |
| seamlessly integrates | Worst offender. | connects to / reads / writes |
| at your fingertips | Cliché. | available / in the app |

## Preferred product vocabulary

- **ingest / import** — reading data files into Niamoto.
- **detect** — auto-detection of column types and roles.
- **transform / compute** — deriving statistics, widgets, aggregates.
- **preview** — rendering a widget or page before publishing.
- **generate / render** — producing the static portal.
- **publish / deploy** — pushing the site to GitHub Pages, S3, etc.
- **script** — using the CLI for automation or CI.
- **map (noun)** — spatial visual; **map (verb)** — associating a
  column to a role.
- **portal** — the generated static website.
- **widget** — a chart, map, table, or card rendered in the portal.
- **plugin** — extension point (transformer, loader, exporter, widget).

## Style rules

### Sentence and paragraph

- Prefer sentences of 8–20 words.
- Paragraphs: 1–4 sentences. Break up walls of text.
- Never start a paragraph with "In this section, we will…".

### Headings

- Use sentence case, not title case. "Install the desktop app", not
  "Install The Desktop App".
- Headings are nouns or short imperatives, not full sentences.

### Lists

- Each bullet starts with a capital letter and ends with a period only
  if it is a full sentence.
- Never use one-item lists.
- Do not mix terse bullets and multi-paragraph bullets in the same list.

### Code and commands

- Use fenced blocks with an explicit language: `` ```bash ``,
  `` ```python ``, `` ```yaml ``.
- Put shell commands one per line. No backslash-continued `\` unless
  needed.
- Output is shown with a `$` prompt only when it matters.

### Links

- Always use relative links between docs pages, never absolute file
  paths like `/Users/...` or `https://github.com/.../blob/...`.
- Link text should read naturally. Prefer "see
  [Import guide](02-user-guide/import.md)" over "see the import page".

### Emoji

- No decorative emoji in body text. Exception: top-of-file badges in
  the README and optional emoji headings in CONTRIBUTING.md are allowed
  as-is for now.

## French accents and diacritics

The public docs are in English, so this rule applies to the devlog,
internal comms, commit bodies in French, and any French-language
fragment inside otherwise-English docs:

- Write all diacritics correctly: é, è, ê, à, ù, ç, î, ô, œ.
- Never substitute ASCII fallbacks (never "ecole" for "école").
- This rule is enforced by habit, not tooling.

## Before / after

### Marketing-speak vs. plain

**Before.** Niamoto seamlessly empowers researchers to unlock the full
potential of their ecological data through a comprehensive, robust
pipeline.

**After.** Niamoto imports ecological data, computes statistics, and
publishes a static portal.

### Filler intros vs. direct

**Before.** In today's fast-paced world of biodiversity research, it's
worth noting that data pipelines can be overwhelming. Niamoto makes it
easy.

**After.** Niamoto turns CSVs and shapefiles into a biodiversity portal
in three steps: import, transform, publish.

### Passive constructions vs. active

**Before.** Column types are automatically detected by our ML
auto-detection system.

**After.** The desktop app detects column types when you import a file.

### Explanation vs. showing

**Before.** This section will provide a comprehensive overview of the
import workflow.

**After.** The import workflow has three screens:

1. Pick a file.
2. Review the detected columns.
3. Confirm and load.

## Applying this guide

After drafting any README or doc page:

1. Re-read once out loud. Strike every adverb that does not carry
   information.
2. Run `/anti-slop` against the draft.
3. Run `/stop-slop` for a second pass.
4. Grep for the banned words in this guide — zero hits is the target.
5. Relink with relative paths. Never commit absolute file URLs.

## References

- `CONTRIBUTING.md`
- `docs/plans/2026-04-17-refactor-documentation-desktop-first-plan.md`
