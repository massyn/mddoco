# Syntax Highlighting

Fenced code blocks are highlighted by language. The language tag after the
opening fence selects the grammar.

```python
from pathlib import Path


def find_markdown_files(folder: str) -> list[Path]:
    """Return every .md file in *folder*, sorted by name."""
    return sorted(Path(folder).glob("*.md"))
```

```bash
mddoco ./docs --theme professional --title "Docs" --toc --format pdf
```

```json
{
  "project": "mddoco",
  "themes": ["default", "professional", "dark", "academic"]
}
```

Inline code such as `--toc-depth 2` is left unstyled.
