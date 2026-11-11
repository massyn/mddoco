# Data-driven Chart

Render this folder with:

```bash
mddoco examples/05_security_findings --title "Security Findings" --output ./out
```

This example joins two mddoco features that the other folders show separately:

- `04_jinja_data` — `.md.j2` templates driven by a `.csv` data file
- `02_rich_content` — native `graph` charts rendered to static SVG at build time

`findings.csv` is injected as the `findings` variable (one dict per row, keyed by
the CSV header). `02_findings.md.j2` renders the raw findings table, groups the
rows by severity in the template, and feeds that same grouping into a `graph`
block — no pre-aggregated data file required.
