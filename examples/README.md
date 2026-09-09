# Examples

Each subfolder is a self-contained mddoco input. Render one by pointing the
`mddoco` command at its folder — they are meant to be run **individually**, not
as one combined `mddoco examples` run (the Jinja examples expect their own data
files at the top level).

| Folder | Demonstrates |
|--------|--------------|
| [`01_basic`](01_basic) | Plain Markdown: file ordering by numeric prefix, underscore-prefixed files excluded from the scan |
| [`02_rich_content`](02_rich_content) | Mermaid diagrams, syntax-highlighted code blocks, native `graph` charts |
| [`03_themed_report`](03_themed_report) | Themes and a table of contents — the same content styled as a report |
| [`04_jinja_data`](04_jinja_data) | `.md.j2` templates, importing `.json` and `.csv` data files, shared macros |

## Quick start

```bash
# 1. Basic, with a title and table of contents
mddoco examples/01_basic --title "Basic Example" --toc --output ./out

# 2. Rich content
mddoco examples/02_rich_content --title "Rich Content" --output ./out

# 3. Themed report with a table of contents
mddoco examples/03_themed_report \
  --theme professional \
  --title "Q3 Platform Review" \
  --toc \
  --output ./out

# 4. Jinja2 templates with JSON and CSV data
mddoco examples/04_jinja_data --title "Jinja Data Demo" --output ./out
```

Each command writes a single HTML file into `./out/`. Add `--format pdf` to any
of them to produce a PDF instead (requires Playwright's Chromium — see the main
[README](../README.md)).
