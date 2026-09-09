# Rich Content

Render this folder with:

```bash
mddoco examples/02_rich_content --title "Rich Content" --output ./out
```

It demonstrates the three content features that go beyond plain Markdown:
Mermaid diagrams, syntax-highlighted code, and native charts.

## Mermaid Diagrams

Fenced ` ```mermaid ` blocks are detected automatically. The Mermaid.js library
is only pulled from the CDN when a diagram is present on the page.

```mermaid
graph TD
    A[Markdown files] --> B[Scan & sort]
    B --> C[Convert each file]
    C --> D{Format?}
    D -->|html| E[Single HTML document]
    D -->|pdf| F[Print via Playwright]
```

```mermaid
sequenceDiagram
    participant U as User
    participant M as mddoco
    U->>M: mddoco ./docs --toc
    M-->>U: docs.html
```
