# Basic Example

This folder is the simplest possible mddoco input: a handful of plain Markdown
files and nothing else. Render it with a title and a table of contents:

```bash
mddoco examples/01_basic --title "Basic Example" --toc --output ./out
```

`--title` adds the heading at the top of the page; `--toc` builds a contents
list from every heading. Every `.md` file in the folder is combined into a
single document — the rest of this example shows *how* they are combined.
