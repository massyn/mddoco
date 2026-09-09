# Jinja2 + Data Files

Render this folder with:

```bash
mddoco examples/04_jinja_data --title "Jinja Data Demo" --output ./out
```

Files ending in `.md.j2` are treated as Jinja2 templates that produce Markdown.
Any `*.json` or `*.csv` file in the same folder becomes a template variable,
named after the file: `project.json` is `project`, `team.csv` is `team`.

- `02_summary.md.j2` reads `project.json`
- `03_team.md.j2` reads `team.csv` and imports macros from `_macros.j2`

Plain `.md` files like this one are passed straight through, untouched.
