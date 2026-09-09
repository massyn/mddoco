# Overview

This folder is written to look good as a *report*: a title banner, a table of
contents, nested headings, tables, and callouts. Render it with a theme and a
TOC:

```bash
mddoco examples/03_themed_report \
  --theme professional \
  --title "Q3 Platform Review" \
  --toc \
  --output ./out
```

Try swapping `--theme professional` for `dark`, `academic`, or
`paged-professional` to see the same content restyled.

## Purpose

The overview section sits at the top of the document and gives the reader the
one-paragraph version before the detail begins.

## Scope

| Area          | Included | Notes                          |
|---------------|----------|--------------------------------|
| Web frontend  | Yes      | Excludes the legacy admin app  |
| API services  | Yes      | v2 endpoints only              |
| Data pipeline | Partial  | Ingestion only; not reporting  |
